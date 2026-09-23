import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OneCommandInstallTests(unittest.TestCase):
    def test_just_install_routes_through_bootstrap(self):
        text = (ROOT / "justfile").read_text()
        install = text.split("\ninstall:\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("bash ./scripts/bootstrap", install)

    def test_bootstrap_installs_released_cli_and_only_oc_launcher(self):
        text = (ROOT / "scripts/bootstrap").read_text()
        self.assertIn("npm uninstall -g opencode-ai", text)
        self.assertIn("npm install -g @opencode/cli@latest", text)
        self.assertIn('bash "$ROOT/scripts/user-link" install oc', text)
        self.assertIn('bash "$ROOT/scripts/user-link" uninstall oc2', text)
        self.assertNotIn('user-link" install oc2', text)

    def test_bootstrap_remains_valid_bash(self):
        result = subprocess.run(["bash", "-n", str(ROOT / "scripts/bootstrap")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
