import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NativeMemoryContractTests(unittest.TestCase):
    def test_native_launcher_loads_memory_after_base_config_and_never_blocks(self):
        launcher = (ROOT / "scripts/opencode-agents").read_text()
        configure = launcher.index('scripts/configure-local')
        memory = launcher.index('scripts/native_memory.py')
        inline = launcher.index('scripts/opencode-skill-source')
        self.assertLess(configure, memory)
        self.assertLess(memory, inline)
        self.assertIn('OAT_MEMORY_AUTO_SYNC=0 OPENCODE_MEMORY_AUTO_SYNC=0', launcher)
        self.assertIn('OAT_MEMORY_STRICT=0 OPENCODE_MEMORY_STRICT=0', launcher)
        self.assertIn('OAT_NATIVE_MEMORY_PLUGIN', launcher)
        self.assertIn('continuing without memory', launcher)

    def test_native_memory_uses_only_existing_local_plugin_and_vault(self):
        loader = (ROOT / "scripts/native_memory.py").read_text()
        self.assertIn('OAT_MEMORY_PLUGIN_DIR', loader)
        self.assertIn('data / "opencode-agent-toolkit" / "plugins" / "opencode-memory-plugin"', loader)
        self.assertIn('not entry.is_file() or not vault.is_dir()', loader)
        self.assertIn('"v2.js" if args.major == "2" else "v1.js"', loader)
        self.assertIn('prepare_v2_wrapper', loader)
        self.assertIn('export { default } from', loader)
        self.assertIn('"exports": "./index.js"', loader)
        self.assertIn('"render", "--agent"', loader)
        for forbidden in ('git clone', 'git pull', 'ensure_plugin(', 'npm install', 'pip install'):
            self.assertNotIn(forbidden, loader)

    def test_memory_plugin_is_added_to_highest_precedence_inline_config(self):
        inline = (ROOT / "scripts/opencode-skill-source").read_text()
        self.assertIn('OAT_NATIVE_MEMORY_PLUGIN', inline)
        self.assertIn('"plugins" if major == "2" else "plugin"', inline)
        self.assertIn('append_unique', inline)

    def test_explicit_memory_cli_still_owns_install_sync_and_capture(self):
        memory = (ROOT / "scripts/memory").read_text()
        self.assertIn('ensure_plugin(force_sync=True)', memory)
        self.assertIn('sub.add_parser("sync"', memory)
        self.assertIn('sub.add_parser("capture-on"', memory)
        self.assertIn('OAT_MEMORY_CAPTURE_ENABLED', memory)


if __name__ == "__main__":
    unittest.main()
