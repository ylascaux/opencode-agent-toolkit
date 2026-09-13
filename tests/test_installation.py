import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationSurfaceTests(unittest.TestCase):
    def test_justfile_is_primary_small_command_surface(self):
        text = (ROOT / 'justfile').read_text()
        for recipe in ['install:', 'profile name="copilot":', 'doctor:', 'config:',
                       'oc *args:', 'oc2 *args:', 'sync *args:', 'codex *args:',
                       'memory *args:', 'test:', 'check: config test']:
            self.assertIn(recipe, text)
        for recipe in ['sandbox-on:', 'sandbox-clean:', 'docker-build:', 'install-oc2:', 'memory-on repo:']:
            self.assertNotIn(recipe, text)
        self.assertIn('set positional-arguments', text)

    def test_config_recipe_is_native_and_never_discovers_providers(self):
        text = (ROOT / 'justfile').read_text()
        block = text.split('\nconfig:\n', 1)[1].split('\n# Local diagnostics', 1)[0]
        self.assertIn('scripts/opencode-agents config', block)
        launcher = (ROOT / 'scripts/opencode-agents').read_text()
        self.assertIn('scripts/generate-config" --native', launcher)
        self.assertNotIn('scripts/apply-reliability', launcher)
        self.assertNotIn('configure-models', block)
        self.assertNotIn('litellm', block.lower())

    def test_makefile_is_not_required(self):
        self.assertFalse((ROOT / 'Makefile').exists())

    def test_installation_scripts_exist(self):
        for name in ['bootstrap', 'doctor', 'generate-config', 'opencode-agents',
                     'opencode-skill-source', 'user-link', 'apply-profile', 'resolve-models',
                     'apply-memory', 'sync-runtime', 'codex', 'memory-mcp']:
            self.assertTrue((ROOT / 'scripts' / name).exists(), name)
        self.assertTrue((ROOT / 'runtime/opencode/native.py').is_file())

    def test_native_runtime_is_the_only_launcher_install_path(self):
        self.assertIn('OAT_RUNTIME=host', (ROOT / '.env.example').read_text())
        for name in ('bootstrap', 'opencode-agents'):
            text = (ROOT / 'scripts' / name).read_text()
            for removed in ('scripts/docker-build', 'scripts/docker-runtime', 'scripts/sandbox-start', 'scripts/task-run'):
                self.assertNotIn(removed, text)
        self.assertIn('OAT_RUNTIME=host OAT_SANDBOX_ENABLED=0 PLAN_APPROVAL_MODE=off',
                      (ROOT / 'scripts/opencode-agents').read_text())

    def test_opencode_v2_plugin_sdk_dependency_is_pinned_for_legacy_tests(self):
        package = json.loads((ROOT / 'package.json').read_text())
        self.assertTrue(package.get('private'))
        self.assertEqual(package.get('type'), 'module')
        self.assertEqual(package.get('dependencies', {}).get('@opencode/plugin'), '0.0.0-beta-19398')
        self.assertIn('node_modules/', (ROOT / '.gitignore').read_text().splitlines())

    def test_bootstrap_does_not_install_unrelated_dependencies(self):
        text = (ROOT / 'scripts/bootstrap').read_text()
        self.assertNotIn('python3 -m venv', text)
        self.assertNotIn('pip install', text)
        self.assertNotIn('npm ci --', text)
        self.assertNotIn('npm install --', text)
        self.assertIn('scripts/opencode-agents" config', text)

    def test_legacy_preflight_stays_an_explicit_diagnostic(self):
        text = (ROOT / 'scripts/preflight').read_text()
        self.assertIn('source "$ROOT/.env"', text)
        self.assertIn('source "$ROOT/.env.local"', text)
        self.assertNotIn('scripts/preflight', (ROOT / 'scripts/opencode-agents').read_text())

    def test_opencode_skill_source_preserves_user_inline_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / 'skills'
            skills.mkdir()
            env = os.environ.copy()
            env['OPENCODE_CONFIG_CONTENT'] = json.dumps({'experimental': {'user-setting': True}, 'skills': ['/user/skills']})
            result = subprocess.run(['python3', str(ROOT / 'scripts/opencode-skill-source'), str(skills)],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual(config['experimental'], {'user-setting': True})
            self.assertEqual(config['skills'], ['/user/skills', str(skills.resolve())])

    def test_user_link_install_is_idempotent_and_reversible(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / 'bin'
            env = {**os.environ, 'OPENCODE_TOOLKIT_BIN_DIR': str(bin_dir)}
            env['PATH'] = f'{bin_dir}:{env.get("PATH", "")}'
            script = ROOT / 'scripts/user-link'
            for _ in range(2):
                subprocess.run(['bash', str(script), 'install', 'oc-test'], check=True, env=env, capture_output=True, text=True)
            link = bin_dir / 'oc-test'
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), str(ROOT / 'scripts/opencode-agents'))
            subprocess.run(['bash', str(script), 'uninstall', 'oc-test'], check=True, env=env, capture_output=True, text=True)
            self.assertFalse(link.exists())
            self.assertFalse(link.is_symlink())

    def test_user_link_launcher_generates_agents_skills_and_models_from_an_external_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit = tmp_path / 'toolkit'
            scripts = toolkit / 'scripts'
            scripts.mkdir(parents=True)
            for name in ['opencode-agents', 'opencode-skill-source', 'generate-config', 'user-link', 'resolve-models',
                         'apply-memory', 'memory_plugin.py', 'agent_config.py']:
                shutil.copy2(ROOT / 'scripts' / name, scripts / name)
            for name in ('agents', 'skills', 'runtime'):
                shutil.copytree(ROOT / name, toolkit / name)
            shutil.copy2(ROOT / 'reliability.json', toolkit / 'reliability.json')
            (toolkit / '.env').write_text('OPENCODE_MAJOR=1\nOAT_RUNTIME=docker\nOAT_SANDBOX_ENABLED=1\n'
                                        'OAT_MEMORY_ENABLED=0\nMODEL_PROFILE=test\nMODEL_LOW=test/low\n'
                                        'MODEL_MEDIUM=test/medium\nMODEL_HIGH=test/high\n')
            fake = tmp_path / 'fake-opencode'
            fake.write_text('#!/usr/bin/env bash\n'
                            'printf "cwd=%s\\nconfig=%s\\nargs=%s\\nmodel=%s\\ninline=%s\\n" "$PWD" "${OPENCODE_CONFIG:-}" "$*" "${MODEL_BUILDER:-}" "${OPENCODE_CONFIG_CONTENT:-}"\n')
            fake.chmod(0o755)
            bin_dir = tmp_path / 'bin'
            env = {key: value for key, value in os.environ.items() if not key.startswith(('MODEL_', 'OPENCODE_', 'OAT_'))}
            env.update(OPENCODE_CONFIG_CONTENT=json.dumps({'experimental': {'user-setting': True}}),
                       OPENCODE_TOOLKIT_BIN_DIR=str(bin_dir), OPENCODE_BIN=str(fake))
            env['PATH'] = f'{bin_dir}:{env.get("PATH", "")}'
            subprocess.run(['bash', str(scripts / 'user-link'), 'install', 'oc-test'], check=True, env=env, capture_output=True, text=True)
            project = tmp_path / 'project'
            project.mkdir()
            result = subprocess.run([str(bin_dir / 'oc-test'), 'run', 'hello'], cwd=project, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
            self.assertEqual(Path(output['cwd']).resolve(), project.resolve())
            self.assertEqual(Path(output['config']).resolve(), (toolkit / 'opencode.jsonc').resolve())
            self.assertEqual(output['args'], 'run hello')
            self.assertEqual(output['model'], 'test/medium')
            inline = json.loads(output['inline'])
            self.assertEqual(inline['experimental'], {'user-setting': True})
            self.assertIn(str((toolkit / '.opencode/skills').resolve()), inline['skills'])
            self.assertTrue((toolkit / '.opencode/skills/test-review/SKILL.md').is_file())
            config = json.loads((toolkit / 'opencode.jsonc').read_text())
            self.assertEqual(config['plugin'], [])
            self.assertEqual(config['default_agent'], 'meta-router')

    def test_user_link_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / 'bin'
            bin_dir.mkdir()
            existing = bin_dir / 'oc-test'
            existing.write_text('keep-me')
            env = {**os.environ, 'OPENCODE_TOOLKIT_BIN_DIR': str(bin_dir)}
            result = subprocess.run(['bash', str(ROOT / 'scripts/user-link'), 'install', 'oc-test'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(existing.read_text(), 'keep-me')


if __name__ == '__main__':
    unittest.main()
