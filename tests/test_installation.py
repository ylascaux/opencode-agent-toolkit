import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationSurfaceTests(unittest.TestCase):
    def test_justfile_is_primary_command_surface(self):
        text = (ROOT / "justfile").read_text()
        for recipe in ["install:", "configure *args:", "doctor:", "check:", "run *args:", "scan *args:", "api:", "models:"]:
            self.assertIn(recipe, text)

    def test_makefile_is_not_required(self):
        self.assertFalse((ROOT / "Makefile").exists())

    def test_bootstrap_doctor_configure_and_generator_exist(self):
        for name in ["bootstrap", "doctor", "configure-models", "generate-config", "opencode-agents"]:
            self.assertTrue((ROOT / "scripts" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
