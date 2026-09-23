import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationSurfaceTests(unittest.TestCase):
    def test_daily_just_surface_is_small_and_stable_only(self):
        text = (ROOT / "justfile").read_text()
        recipes = [line for line in text.splitlines() if line and not line.startswith((" ", "#", "[", "set ")) and ":" in line]
        self.assertLessEqual(len(recipes), 13)
        for command in ("install:", "uninstall:", "config:", "doctor:", "test:", "oc *args:", "plugins:", "sync *args:", "codex *args:"):
            self.assertIn(command, text)
        self.assertNotIn("oc2 *args:", text)
        self.assertNotIn("memory *args:", text)

    def test_native_launcher_has_no_version_switch_or_control_plugin(self):
        text = (ROOT / "scripts/opencode-agents").read_text()
        self.assertNotIn("OPENCODE_MAJOR", text)
        self.assertNotIn("opencode2", text)
        for legacy in ("scripts/docker-runtime", "scripts/apply-reliability", "scripts/apply-memory", "runtime/plugins/usage-pricing"):
            self.assertNotIn(legacy, text)
        self.assertIn('config="$ROOT/opencode.jsonc"', text)
        self.assertIn('exec "$bin" "$@"', text)

    def test_real_catalogue_generates_one_stable_config(self):
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
            self.assertEqual(config["plugins"], [])
            self.assertNotIn("agent", config)
            self.assertNotIn("plugin", config)
            self.assertFalse((checkout / "opencode.v2.jsonc").exists())
            self.assertTrue((checkout / ".opencode/skills/test-review/SKILL.md").is_file())
            self.assertEqual(subprocess.run([*command, "--check"], capture_output=True).returncode, 0)

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
            user_file = directory / "oc-test"
            user_file.write_text("keep me")
            self.assertNotEqual(subprocess.run([*command, "install", "oc-test"], env=env, capture_output=True).returncode, 0)
            self.assertEqual(user_file.read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()
