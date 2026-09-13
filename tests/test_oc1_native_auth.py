import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Oc1NativeAuthTests(unittest.TestCase):
    def test_bootstrap_uses_native_auth_without_installing_a_docker_client(self):
        bootstrap = (ROOT / "scripts" / "bootstrap").read_text()
        self.assertNotIn('install -m 0755 "$ROOT/scripts/opencode-v1-native-client"', bootstrap)
        self.assertNotIn('OAT_OC_NATIVE_BIN=%s', bootstrap)
        launcher = (ROOT / "scripts/opencode-agents").read_text()
        self.assertIn('auth|--help|-h|--version|-v|version)', launcher)
        self.assertIn('exec "$bin" "$@"', launcher)

    def test_legacy_native_v1_wrapper_forwards_basic_auth_explicitly(self):
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

    def test_legacy_v1_server_is_loopback_only_and_does_not_inherit_oc2_password(self):
        compose = (ROOT / "compose.yaml").read_text()
        v1 = compose.split("\n  oc-server:\n", 1)[1].split("\n  oc2-server:\n", 1)[0]
        v2 = compose.split("\n  oc2-server:\n", 1)[1]
        self.assertIn('127.0.0.1:${OAT_OC_PORT:-4095}:4096', v1)
        self.assertIn('OPENCODE_SERVER_PASSWORD: ""', v1)
        self.assertNotIn('OPENCODE_SERVER_PASSWORD: ""', v2)
        self.assertIn('127.0.0.1:${OAT_OC2_PORT:-4096}:4096', v2)


if __name__ == "__main__":
    unittest.main()
