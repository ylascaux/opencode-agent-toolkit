import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V2CompactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            ["python3", str(ROOT / "scripts" / "generate-config")],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        cls.v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())

    def test_v2_uses_native_compaction_defaults(self):
        self.assertEqual(
            self.v2["compaction"],
            {
                "auto": True,
                "keep": {"tokens": 15000},
                "buffer": 20000,
            },
        )

    def test_v1_does_not_receive_v2_compaction_shape(self):
        self.assertNotIn("compaction", self.v1)

    def test_v2_does_not_depend_on_context_pruning_plugins(self):
        plugins = self.v2.get("plugins", [])
        plugin_text = " ".join(
            item if isinstance(item, str) else json.dumps(item, sort_keys=True)
            for item in plugins
        ).lower()
        self.assertNotIn("dcp", plugin_text)
        self.assertNotIn("context-compress", plugin_text)


if __name__ == "__main__":
    unittest.main()
