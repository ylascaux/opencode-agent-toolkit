import importlib.util
import json
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply-reliability"

sys.path.insert(0, str(ROOT / "scripts"))
loader = SourceFileLoader("apply_reliability_for_test", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
if spec is None:
    raise RuntimeError("Unable to load scripts/apply-reliability")
MODULE = importlib.util.module_from_spec(spec)
loader.exec_module(MODULE)


class V2PluginMigrationTests(unittest.TestCase):
    def test_legacy_v2_plugin_files_are_replaced_by_directory_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "opencode.v2.jsonc"
            config.write_text(json.dumps({
                "agents": {},
                "plugins": [
                    "./runtime/plugins/reliability-v2.ts",
                    "./runtime/plugins/plan-approval-v2.ts",
                    "./some-other-plugin",
                ],
            }))

            MODULE.patch_config(config, v2=True)
            plugins = json.loads(config.read_text())["plugins"]

            self.assertIn("./runtime/plugins/reliability-v2", plugins)
            self.assertIn("./runtime/plugins/plan-approval-v2", plugins)
            self.assertIn("./some-other-plugin", plugins)
            self.assertNotIn("./runtime/plugins/reliability-v2.ts", plugins)
            self.assertNotIn("./runtime/plugins/plan-approval-v2.ts", plugins)


if __name__ == "__main__":
    unittest.main()
