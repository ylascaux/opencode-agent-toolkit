import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-v2-plugin-entries"


class V2PluginEntryTests(unittest.TestCase):
    def _validate(self, root: Path, entries: list[str]) -> subprocess.CompletedProcess[str]:
        config = root / "opencode.v2.jsonc"
        config.write_text(json.dumps({"plugins": entries}))
        return subprocess.run(
            ["python3", str(VALIDATOR), str(config)],
            capture_output=True,
            text=True,
        )

    def test_accepts_directory_with_supported_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugin"
            plugin.mkdir()
            (plugin / "index.ts").write_text("export default {}\n")
            result = self._validate(root, ["./plugin"])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_empty_plugin_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "empty-plugin").mkdir()
            result = self._validate(root, ["./empty-plugin"])
            self.assertEqual(result.returncode, 1)
            self.assertIn("./empty-plugin", result.stderr)

    def test_rejects_direct_plugin_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "plugin.ts").write_text("export default {}\n")
            result = self._validate(root, ["./plugin.ts"])
            self.assertEqual(result.returncode, 1)
            self.assertIn("./plugin.ts", result.stderr)


if __name__ == "__main__":
    unittest.main()
