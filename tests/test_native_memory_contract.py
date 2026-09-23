import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NativeMemoryContractTests(unittest.TestCase):
    def test_oc2_uses_published_memory_plugin_not_private_bridge(self):
        launcher = (ROOT / "scripts/opencode-agents").read_text()
        inline = (ROOT / "scripts/opencode-skill-source").read_text()

        self.assertIn('OAT_OC2_MEMORY_PLUGIN:-opencode-mem@2.26.0', launcher)
        self.assertIn('OAT_NATIVE_V2_MEMORY_PLUGIN', launcher)
        self.assertIn('scripts/configure-v2-memory', launcher)
        self.assertIn('if [[ "$major" == 1 ]]', launcher)
        self.assertIn('scripts/native_memory.py" --major 1', launcher)
        self.assertNotIn('scripts/native_memory.py" --major "$major"', launcher)

        self.assertIn('v2_memory_plugin = os.environ.get("OAT_NATIVE_V2_MEMORY_PLUGIN"', inline)
        self.assertIn('if v2_memory_plugin and major == "2"', inline)
        self.assertIn('append_unique(config, "plugins", v2_memory_plugin)', inline)

    def test_private_memory_bridge_is_v1_only_at_runtime(self):
        inline = (ROOT / "scripts/opencode-skill-source").read_text()
        self.assertIn('if memory_plugin and major == "1"', inline)
        self.assertIn('append_unique(config, "plugin", memory_plugin)', inline)
        self.assertNotIn('append_unique(config, "plugins" if major == "2" else "plugin", memory_plugin)', inline)

    def test_oc2_memory_is_opt_out_and_version_pinned(self):
        launcher = (ROOT / "scripts/opencode-agents").read_text()
        env = (ROOT / ".env.example").read_text()
        self.assertIn('OAT_OC2_MEMORY_ENABLED:-1', launcher)
        self.assertIn('OAT_OC2_MEMORY_ENABLED=1', env)
        self.assertIn('OAT_OC2_MEMORY_PLUGIN=opencode-mem@2.26.0', env)


if __name__ == "__main__":
    unittest.main()
