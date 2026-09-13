import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NativeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'toolkit with spaces'
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir(parents=True)
        shutil.copy2(ROOT / 'scripts/opencode-agents', self.scripts / 'opencode-agents')
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(('OPENCODE_', 'OAT_', 'MODEL_', 'PLAN_APPROVAL'))}
        self.env['PATH'] = f'{self.bin}:{self.env.get("PATH", "")}'
        self.env['NATIVE_TEST_LOG'] = str(self.base / 'calls')
        for name in ['generate-config', 'apply-memory', 'resolve-models']:
            (self.scripts / name).write_text('import os, pathlib, sys\n'
                'with pathlib.Path(os.environ["NATIVE_TEST_LOG"]).open("a") as f: f.write(pathlib.Path(sys.argv[0]).name + " " + " ".join(sys.argv[1:]) + "\\n")\n')
        for name in ['sync-runtime', 'codex', 'memory-mcp', 'memory']:
            (self.scripts / name).write_text('import json, sys\nprint(json.dumps(sys.argv[1:]))\n')
        for name in ['opencode', 'opencode2']:
            binary = self.bin / name
            binary.write_text(f'#!{sys.executable}\nimport json, os, sys\n'
                'print(json.dumps({"binary": os.path.basename(sys.argv[0]), "args": sys.argv[1:], '
                '"cwd": os.getcwd(), "major": os.getenv("OPENCODE_MAJOR"), "config": os.getenv("OPENCODE_CONFIG"), '
                '"runtime": os.getenv("OAT_RUNTIME"), "sandbox": os.getenv("OAT_SANDBOX_ENABLED"), '
                '"approval": os.getenv("PLAN_APPROVAL_MODE"), "home": os.getenv("HOME")}))\n'
                'sys.exit(int(os.getenv("NATIVE_TEST_EXIT", "0")))\n')
            binary.chmod(0o755)
        for name in ['oc', 'oc2']:
            (self.bin / name).symlink_to(self.scripts / 'opencode-agents')
        (self.root / '.env').write_text('OPENCODE_MAJOR=1\nOAT_RUNTIME=docker\nOAT_SANDBOX_ENABLED=1\nPLAN_APPROVAL_MODE=always\n')
        for name in ['docker-runtime', 'sandbox-start', 'preflight', 'apply-reliability']:
            (self.scripts / name).write_text('#!/bin/sh\nexit 99\n')
        for name in ['docker', 'podman']:
            path = self.bin / name
            path.write_text('#!/bin/sh\necho CONTAINER_CALLED >&2\nexit 99\n')
            path.chmod(0o755)

    def run_oc(self, *args, command='oc2'):
        return subprocess.run([str(self.bin / command), *args], cwd=self.project,
                              env=self.env, capture_output=True, text=True, timeout=10)

    def result(self, *args, command='oc2'):
        result = self.run_oc(*args, command=command)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_old_docker_settings_cannot_start_containers(self):
        data = self.result('run', 'hello world')
        self.assertEqual(data['runtime'], 'host')
        self.assertEqual(data['sandbox'], '0')
        self.assertEqual(data['approval'], 'off')
        self.assertEqual(data['args'], ['--standalone', 'run', 'hello world'])
        self.assertIn('generate-config --native', (self.base / 'calls').read_text())

    def test_oc_stays_v1(self):
        self.assertEqual(self.result('run', 'hello', command='oc')['binary'], 'opencode')

    def test_symlink_preserves_cwd_home_and_v2_config(self):
        data = self.result('run', 'hello')
        self.assertEqual(Path(data['cwd']).resolve(), self.project.resolve())
        self.assertEqual(data['home'], self.env.get('HOME'))
        self.assertEqual(Path(data['config']).resolve(), (self.root / 'opencode.v2.jsonc').resolve())

    def test_explicit_major_wins_over_env_file(self):
        self.env['OPENCODE_MAJOR'] = '2'
        self.assertEqual(self.result('run', 'hello', command='oc')['major'], '2')

    def test_explicit_binary_wins_over_env_file(self):
        with (self.root / '.env').open('a') as stream:
            stream.write('OPENCODE_BIN=missing-in-env\n')
        self.env['OPENCODE_BIN'] = str(self.bin / 'opencode2')
        self.assertEqual(self.result('run', 'hello')['binary'], 'opencode2')

    def test_auth_needs_neither_env_nor_working_generation(self):
        (self.root / '.env').unlink()
        (self.scripts / 'generate-config').write_text('raise SystemExit(99)\n')
        self.assertEqual(self.result('auth', 'login')['args'], ['auth', 'login'])
        self.assertFalse((self.base / 'calls').exists())

    def test_model_resolution_failure_is_not_ignored(self):
        (self.scripts / 'resolve-models').write_text('raise SystemExit(42)\n')
        self.assertEqual(self.run_oc('run', 'hello').returncode, 42)

    def test_inline_config_failure_is_not_ignored(self):
        (self.scripts / 'opencode-skill-source').write_text('raise SystemExit(43)\n')
        self.assertEqual(self.run_oc('run', 'hello').returncode, 43)

    def test_version_does_not_generate(self):
        self.assertEqual(self.result('--version')['args'], ['--version'])
        self.assertFalse((self.base / 'calls').exists())

    def test_portable_commands_do_not_source_env(self):
        (self.root / '.env').write_text('exit 91\n')
        for args in [('sync', 'codex', '--check'), ('codex', 'install'), ('memory', 'mcp', '--help')]:
            with self.subTest(args=args):
                result = self.run_oc(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = list(args[2:] if args[:2] == ('memory', 'mcp') else args[1:])
                self.assertEqual(json.loads(result.stdout), expected)
        self.assertFalse((self.base / 'calls').exists())

    def test_memory_does_not_start_opencode(self):
        self.env['OPENCODE_BIN'] = 'not-installed'
        result = self.run_oc('memory', 'candidates', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ['candidates', '--json'])

    def test_exit_code_is_preserved(self):
        self.env['NATIVE_TEST_EXIT'] = '17'
        self.assertEqual(self.run_oc('run', 'hello').returncode, 17)

    def test_missing_binary_is_actionable(self):
        self.env['OPENCODE_BIN'] = 'not-installed'
        result = self.run_oc('run', 'hello')
        self.assertEqual(result.returncode, 127)
        self.assertIn('Native OpenCode binary not found', result.stderr)

    def test_recursive_binary_is_rejected(self):
        self.env['OPENCODE_BIN'] = str(self.bin / 'oc2')
        self.assertEqual(self.run_oc('run', 'hello').returncode, 2)

    def test_explicit_server_is_preserved(self):
        args = ['--server', 'http://127.0.0.1:4096', 'run', 'hello']
        self.assertEqual(self.result(*args)['args'], args)

    def test_foreground_serve_is_preserved(self):
        args = ['serve', '--hostname', '127.0.0.1']
        self.assertEqual(self.result(*args)['args'], args)

    def test_standalone_is_not_duplicated(self):
        args = ['--standalone', 'run', 'hello']
        self.assertEqual(self.result(*args)['args'], args)

    def test_prompt_word_serve_is_not_a_server_command(self):
        self.assertEqual(self.result('run', 'serve')['args'], ['--standalone', 'run', 'serve'])

    def test_config_does_not_require_opencode(self):
        self.env['OPENCODE_BIN'] = 'not-installed'
        result = self.run_oc('config')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Native V1/V2', result.stdout)

    def test_arguments_are_not_evaluated_by_shell(self):
        prompt = '$(touch should-not-exist); "quoted" and spaces'
        self.assertEqual(self.result('run', prompt)['args'][-1], prompt)
        self.assertFalse((self.project / 'should-not-exist').exists())


if __name__ == '__main__':
    unittest.main()
