import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationSurfaceTests(unittest.TestCase):
    def test_daily_just_surface_is_small_and_uses_positional_arguments(self):
        text = (ROOT / "justfile").read_text()
        recipes = [line for line in text.splitlines() if line and not line.startswith((" ", "#", "[", "set ")) and ":" in line]
        self.assertLessEqual(len(recipes), 13)  # includes default and the hidden CI alias
        for command in ("install:", "uninstall:", "config:", "doctor:", "test:", "sync *args:", "codex *args:", "memory *args:"):
            self.assertIn(command, text)
        self.assertIn("set positional-arguments", text)
        self.assertNotIn("{{args}}", text)
        self.assertNotIn("sandbox-on:", text)
        self.assertNotIn("docker-build:", text)

    def test_native_is_default_and_no_control_plugin_is_loaded_at_startup(self):
        self.assertIn("OAT_RUNTIME=host", (ROOT / ".env.example").read_text())
        text = (ROOT / "scripts/opencode-agents").read_text()
        for legacy in ("scripts/docker-runtime", "scripts/sandbox-start", "scripts/apply-reliability", "scripts/apply-memory", "scripts/preflight"):
            self.assertNotIn(legacy, text)
        self.assertIn('exec "$bin" "$@"', text)

    def test_real_catalogue_generates_self_contained_native_configs(self):
        # A complete checkout validates the actual catalogue, not only renderer fixtures.
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
            for name, key, plugin_key in (("opencode.jsonc", "agent", "plugin"), ("opencode.v2.jsonc", "agents", "plugins")):
                config = json.loads((checkout / name).read_text())
                self.assertEqual(config["default_agent"], "meta-router")
                self.assertIn("orchestrator", config[key])
                self.assertEqual(config[plugin_key], [])
                self.assertNotIn("shell", config)
                self.assertTrue(all("steps" not in agent for agent in config[key].values()))
                self.assertNotIn("{file:", json.dumps(config))
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
