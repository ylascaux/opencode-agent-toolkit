import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OneCommandInstallTests(unittest.TestCase):
    def test_just_install_routes_through_bootstrap(self):
        text = (ROOT / "justfile").read_text()
        install_block = text.split("\ninstall:\n", 1)[1].split("\n# Apply a model-provider profile", 1)[0]
        self.assertIn("bash ./scripts/bootstrap", install_block)

    def test_bootstrap_builds_materializes_installs_then_restarts_oc2(self):
        text = (ROOT / "scripts" / "bootstrap").read_text()
        build = text.index("bash ./scripts/docker-build")
        materialize = text.index("  materialize_generated_artifacts", build)
        install_launchers = text.index("  install_launchers", materialize)
        restart = text.index('OAT_WORKSPACE_ROOT="$ROOT" OPENCODE_MAJOR=2 bash "$ROOT/scripts/docker-runtime" server restart')

        self.assertIn('docker run --rm', text)
        self.assertIn('python3 ./scripts/generate-config', text)
        self.assertIn('python3 ./scripts/apply-reliability', text)
        self.assertIn('.generated/prompts-v1/api-contract.md', text)
        self.assertIn('bash "$ROOT/scripts/user-link" install oc', text)
        self.assertIn('bash "$ROOT/scripts/user-link" install oc2', text)
        self.assertLess(build, materialize)
        self.assertLess(materialize, install_launchers)
        self.assertLess(install_launchers, restart)

    def test_bootstrap_remains_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "scripts" / "bootstrap")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
