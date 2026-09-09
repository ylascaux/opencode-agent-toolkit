import importlib.util
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_apply_memory():
    loader = SourceFileLoader("apply_memory_test", str(ROOT / "scripts" / "apply-memory"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MemoryCaptureConfigTests(unittest.TestCase):
    def test_capture_plugin_is_v2_only_and_opt_in(self):
        module = load_apply_memory()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "opencode.v2.jsonc").write_text('{"plugins": []}\n')
            module.ROOT = root
            with patch.dict(os.environ, {"OAT_MEMORY_ENABLED": "1", "OAT_MEMORY_CAPTURE_ENABLED": "1"}, clear=False):
                self.assertTrue(module.configure_capture_plugin())
            text = (root / "opencode.v2.jsonc").read_text()
            self.assertIn("memory-capture-v2.ts", text)

            with patch.dict(os.environ, {"OAT_MEMORY_ENABLED": "0", "OAT_MEMORY_CAPTURE_ENABLED": "1"}, clear=False):
                self.assertFalse(module.configure_capture_plugin())
            text = (root / "opencode.v2.jsonc").read_text()
            self.assertNotIn("memory-capture-v2.ts", text)


if __name__ == "__main__":
    unittest.main()
