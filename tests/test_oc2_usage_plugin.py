import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "opencode-skill-source"
LAUNCHER = ROOT / "scripts" / "opencode-agents"


class Oc2UsagePluginTests(unittest.TestCase):
    def render(self, major: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "OPENCODE_MAJOR": major,
                    "OAT_NATIVE_USAGE_PLUGIN": "/tmp/usage-pricing-v2.js",
                    "OPENCODE_CONFIG_CONTENT": json.dumps({"plugins": ["user-plugin"]}),
                }
            )
            result = subprocess.run(
                ["python3", "-B", str(SOURCE), str(skills)],
                check=True,
                text=True,
                capture_output=True,
                env=env,
            )
            return json.loads(result.stdout)

    def test_usage_plugin_is_injected_only_for_v2(self):
        v2 = self.render("2")
        self.assertEqual(v2["plugins"], ["user-plugin", "/tmp/usage-pricing-v2.js"])

        v1 = self.render("1")
        self.assertEqual(v1["plugins"], ["user-plugin"])
        self.assertNotIn("plugin", v1)

    def test_native_launcher_wires_the_fail_open_usage_plugin(self):
        launcher = LAUNCHER.read_text()
        self.assertIn('usage_plugin="$ROOT/runtime/plugins/usage-pricing-v2.js"', launcher)
        self.assertIn('export OAT_NATIVE_USAGE_PLUGIN="$usage_plugin"', launcher)
        self.assertIn("continuing without estimated cost", launcher)


if __name__ == "__main__":
    unittest.main()
