import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Oc1NativeAuthTests(unittest.TestCase):
    def test_bootstrap_installs_managed_native_v1_auth_client(self):
        bootstrap = (ROOT / "scripts" / "bootstrap").read_text()
        self.assertIn('install -m 0755 "$ROOT/scripts/opencode-v1-native-client" "$wrapper"', bootstrap)
        self.assertIn('OAT_OC_NATIVE_BIN=%s', bootstrap)
        self.assertIn('Keeping explicit OAT_OC_NATIVE_BIN override', bootstrap)

    def test_native_v1_wrapper_forwards_basic_auth_explicitly(self):
        wrapper = (ROOT / "scripts" / "opencode-v1-native-client").read_text()
        self.assertIn('auth_args+=(--username "${OPENCODE_SERVER_USERNAME:-opencode}")', wrapper)
        self.assertIn('auth_args+=(--password "$OPENCODE_SERVER_PASSWORD")', wrapper)
        self.assertIn('exec "$HOST_BIN" attach "${auth_args[@]}" "$@"', wrapper)
        self.assertIn('exec "$HOST_BIN" run "${auth_args[@]}" "$@"', wrapper)

    def test_native_v1_wrapper_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "scripts" / "opencode-v1-native-client")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
