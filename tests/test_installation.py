import os
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
            'install-user command="oc":',
            'uninstall-user command="oc":',
            'user-status command="oc":',
            "configure *args:",
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

    def test_bootstrap_doctor_configure_generator_and_user_link_exist(self):
        for name in ["bootstrap", "doctor", "configure-models", "generate-config", "opencode-agents", "user-link"]:
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
