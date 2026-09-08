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
            'install-user command="oc":',
            'uninstall-user command="oc":',
            'user-status command="oc":',
            "configure *args:",
            "configure-litellm *args:",
            "doctor:",
            "check:",
            "run *args:",
            "scan *args:",
            "api:",
            "models:",
        ]:
            self.assertIn(recipe, text)

    def test_makefile_is_not_required(self):
        self.assertFalse((ROOT / "Makefile").exists())

    def test_installation_scripts_exist(self):
        for name in [
            "bootstrap", "doctor", "configure-models", "generate-config", "opencode-agents",
            "user-link", "apply-profile", "resolve-models",
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
            agents = toolkit / "agents"
            profiles = toolkit / "profiles"
            scripts.mkdir(parents=True)
            agents.mkdir()
            profiles.mkdir()

            for name in ["opencode-agents", "generate-config", "user-link", "resolve-models"]:
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            shutil.copy2(ROOT / "agents" / "manifest.json", agents / "manifest.json")
            shutil.copy2(ROOT / "profiles" / "agent-tiers.json", profiles / "agent-tiers.json")
            (toolkit / ".env").write_text(
                "OPENCODE_MAJOR=1\n"
                "MODEL_PROFILE=test\n"
                "MODEL_LOW=test/low\n"
                "MODEL_MEDIUM=test/medium\n"
                "MODEL_HIGH=test/high\n"
            )

            fake_opencode = tmp_path / "fake-opencode"
            fake_opencode.write_text(
                "#!/usr/bin/env bash\n"
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
            self.assertIn(f"cwd={project}", result.stdout)
            self.assertIn(f"config={toolkit / 'opencode.jsonc'}", result.stdout)
            self.assertIn("args=run hello", result.stdout)
            self.assertIn("model=test/medium", result.stdout)

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
