import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure-v2-memory"


class ConfigureV2MemoryTests(unittest.TestCase):
    def run_configure(self, home: Path, **extra: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(("MODEL_", "OAT_OC2_MEMORY_")):
                env.pop(key)
        env.update({"HOME": str(home), "MODEL_MEDIUM": "github-copilot/gpt-5.6-terra", **extra})
        return subprocess.run(["python3", str(SCRIPT)], env=env, capture_output=True, text=True)

    def test_creates_minimal_auto_capture_config_from_active_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_configure(home)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = home / ".config/opencode/opencode-mem.jsonc"
            payload = json.loads(config.read_text())
            self.assertEqual(payload["opencodeProvider"], "github-copilot")
            self.assertEqual(payload["opencodeModel"], "inherit")
            self.assertTrue(payload["autoCaptureEnabled"])
            self.assertFalse(payload["webServerEnabled"])
            self.assertEqual(payload["memory"]["defaultScope"], "project")

    def test_existing_user_config_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".config/opencode/opencode-mem.jsonc"
            config.parent.mkdir(parents=True)
            config.write_text('{"custom":"keep-me"}\n')
            before = config.read_bytes()
            result = self.run_configure(home, OAT_OC2_MEMORY_PROVIDER="openai")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(config.read_bytes(), before)

    def test_explicit_provider_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = self.run_configure(home, OAT_OC2_MEMORY_PROVIDER="openai")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((home / ".config/opencode/opencode-mem.jsonc").read_text())
            self.assertEqual(payload["opencodeProvider"], "openai")


if __name__ == "__main__":
    unittest.main()
