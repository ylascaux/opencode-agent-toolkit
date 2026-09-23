import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationSurfaceTests(unittest.TestCase):
    def test_daily_just_surface_has_only_oc(self):
        text = (ROOT / "justfile").read_text()
        self.assertIn("\noc *args:\n", text)
        self.assertNotIn("\noc2 *args:\n", text)
        for command in ("install:", "uninstall:", "config:", "doctor:", "test:", "sync *args:", "codex *args:"):
            self.assertIn(command, text)

    def test_real_catalogue_generates_single_open_code_2_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "toolkit"
            checkout.mkdir()
            for folder in ("agents", "skills", "runtime"):
                shutil.copytree(ROOT / folder, checkout / folder)
            (checkout / "scripts").mkdir()
            for name in ("configure-local", "native_config.py"):
                shutil.copy2(ROOT / "scripts" / name, checkout / "scripts" / name)
            command = ["python3", "-B", str(checkout / "scripts/configure-local")]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((checkout / "opencode.jsonc").read_text())
            self.assertEqual(config["default_agent"], "meta-router")
            self.assertIn("orchestrator", config["agents"])
            self.assertEqual(config["plugins"], ["opencode-mem@2.26.0"])
            self.assertFalse((checkout / "opencode.v2.jsonc").exists())
            self.assertTrue((checkout / ".opencode/skills/test-review/SKILL.md").is_file())

    def test_user_links_are_idempotent_and_do_not_replace_user_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "bin"
            env = {**os.environ, "OPENCODE_TOOLKIT_BIN_DIR": str(directory)}
            command = ["bash", str(ROOT / "scripts/user-link")]
            for _ in range(2):
                result = subprocess.run([*command, "install", "oc-test"], env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((directory / "oc-test").resolve(), (ROOT / "scripts/opencode-agents").resolve())
            self.assertEqual(subprocess.run([*command, "uninstall", "oc-test"], env=env, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
