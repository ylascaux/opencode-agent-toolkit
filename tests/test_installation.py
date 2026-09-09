import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationSurfaceTests(unittest.TestCase):
    def test_justfile_is_primary_command_surface(self):
        text = (ROOT / "justfile").read_text()
        for recipe in [
            "install:",
            'profile name="copilot":',
            "profiles:",
            "agents:",
            "new-agent name *args:",
            'install-user command="oc":',
            'uninstall-user command="oc":',
            'user-status command="oc":',
            "configure-litellm *args:",
            "doctor:",
            "preflight:",
            "reliability:",
            "check:",
            "config:",
            "run *args:",
            "scan *args:",
            "api:",
            "models:",
        ]:
            self.assertIn(recipe, text)
        self.assertNotIn("\nconfigure *args:", text)

    def test_config_recipe_never_invokes_litellm_or_interactive_configurator(self):
        text = (ROOT / "justfile").read_text()
        config_block = text.split("\nconfig:\n", 1)[1].split("\ntest:\n", 1)[0]
        self.assertIn("generate-config", config_block)
        self.assertIn("apply-reliability", config_block)
        self.assertNotIn("configure-models", config_block)
        self.assertNotIn("litellm", config_block.lower())

    def test_makefile_is_not_required(self):
        self.assertFalse((ROOT / "Makefile").exists())

    def test_installation_scripts_exist(self):
        for name in [
            "bootstrap", "doctor", "configure-models", "generate-config", "opencode-agents",
            "user-link", "apply-profile", "resolve-models", "apply-reliability", "preflight",
            "show-reliability", "agent_config.py", "new-agent",
        ]:
            self.assertTrue((ROOT / "scripts" / name).exists(), name)

    def test_user_link_install_is_idempotent_and_reversible(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            env = os.environ.copy()
            env["OPENCODE_TOOLKIT_BIN_DIR"] = str(bin_dir)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            script = ROOT / "scripts" / "user-link"

            subprocess.run(["bash", str(script), "install", "oc-test"], check=True, env=env, capture_output=True, text=True)
            link = bin_dir / "oc-test"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), str(ROOT / "scripts" / "opencode-agents"))

            subprocess.run(["bash", str(script), "install", "oc-test"], check=True, env=env, capture_output=True, text=True)
            subprocess.run(["bash", str(script), "uninstall", "oc-test"], check=True, env=env, capture_output=True, text=True)
            self.assertFalse(link.exists())
            self.assertFalse(link.is_symlink())

    def test_user_link_launcher_resolves_toolkit_root_through_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit = tmp_path / "toolkit"
            scripts = toolkit / "scripts"
            plugins = toolkit / ".opencode" / "plugins"
            scripts.mkdir(parents=True)
            plugins.mkdir(parents=True)

            for name in [
                "opencode-agents", "generate-config", "user-link", "resolve-models",
                "apply-reliability", "preflight", "agent_config.py",
            ]:
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            shutil.copytree(ROOT / "agents", toolkit / "agents")
            shutil.copy2(ROOT / "reliability.json", toolkit / "reliability.json")
            shutil.copy2(
                ROOT / ".opencode" / "plugins" / "reliability-v1.js",
                plugins / "reliability-v1.js",
            )
            (toolkit / ".env").write_text(
                "OPENCODE_MAJOR=1\n"
                "OPENCODE_PREFLIGHT=1\n"
                "MODEL_PROFILE=test\n"
                "MODEL_LOW=test/low\n"
                "MODEL_MEDIUM=test/medium\n"
                "MODEL_HIGH=test/high\n"
            )

            fake_opencode = tmp_path / "fake-opencode"
            fake_opencode.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"${1:-}\" == \"auth\" && \"${2:-}\" == \"list\" ]]; then\n"
                "  echo '1 credential'\n"
                "  exit 0\n"
                "fi\n"
                "if [[ \"${1:-}\" == \"models\" ]]; then\n"
                "  printf '%s\\n' \"${MODEL_LOW:-}\" \"${MODEL_MEDIUM:-}\" \"${MODEL_HIGH:-}\"\n"
                "  exit 0\n"
                "fi\n"
                "printf 'cwd=%s\\nconfig=%s\\nargs=%s\\nmodel=%s\\n' \"$PWD\" \"${OPENCODE_CONFIG:-}\" \"$*\" \"${MODEL_BUILDER:-}\"\n"
            )
            fake_opencode.chmod(0o755)

            bin_dir = tmp_path / "bin"
            env = os.environ.copy()
            env["OPENCODE_TOOLKIT_BIN_DIR"] = str(bin_dir)
            env["OPENCODE_BIN"] = str(fake_opencode)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            subprocess.run(
                ["bash", str(scripts / "user-link"), "install", "oc-test"],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )

            project = tmp_path / "project"
            project.mkdir()
            result = subprocess.run(
                [str(bin_dir / "oc-test"), "run", "hello"],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = dict(
                line.split("=", 1)
                for line in result.stdout.splitlines()
                if "=" in line
            )
            # macOS exposes /var as a symlink to /private/var. Bash `cd -P`
            # intentionally canonicalizes paths, so compare filesystem identity
            # instead of the lexical spelling returned by tempfile.
            self.assertEqual(Path(output["cwd"]).resolve(), project.resolve())
            self.assertEqual(Path(output["config"]).resolve(), (toolkit / "opencode.jsonc").resolve())
            self.assertEqual(output["args"], "run hello")
            self.assertEqual(output["model"], "test/medium")

    def test_user_link_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir(parents=True)
            existing = bin_dir / "oc-test"
            existing.write_text("keep-me")

            env = os.environ.copy()
            env["OPENCODE_TOOLKIT_BIN_DIR"] = str(bin_dir)
            script = ROOT / "scripts" / "user-link"
            result = subprocess.run(["bash", str(script), "install", "oc-test"], env=env, capture_output=True, text=True)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(existing.read_text(), "keep-me")


if __name__ == "__main__":
    unittest.main()
