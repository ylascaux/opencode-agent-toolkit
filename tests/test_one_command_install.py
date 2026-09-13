import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OneCommandInstallTests(unittest.TestCase):
    def test_just_install_routes_through_bootstrap(self):
        text = (ROOT / "justfile").read_text()
        install = text.split("\ninstall:\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("bash ./scripts/bootstrap", install)

    def test_bootstrap_generates_then_installs_without_runtime_setup(self):
        text = (ROOT / "scripts/bootstrap").read_text()
        generation = text.index('python3 -B "$ROOT/scripts/configure-local"')
        self.assertLess(generation, text.index('bash "$ROOT/scripts/user-link" install oc'))
        self.assertIn('bash "$ROOT/scripts/user-link" install oc2', text)
        for legacy in ('bash ./scripts/docker-build', 'docker run ', 'docker-runtime',
                       'python3 -m venv', 'pip install -', 'npm ci ', 'npm install -'):
            self.assertNotIn(legacy, text)
        self.assertIn('if [[ ! -f "$ROOT/.env" ]]', text)

    def test_bootstrap_remains_valid_bash(self):
        result = subprocess.run(["bash", "-n", str(ROOT / "scripts/bootstrap")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
