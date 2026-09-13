import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Oc1NativeAuthTests(unittest.TestCase):
    def test_native_v1_client_passes_basic_auth_explicitly(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()

        self.assertIn('native_v1_auth_args=()', runtime)
        self.assertIn('native_v1_auth_args+=(--username "${OPENCODE_SERVER_USERNAME:-opencode}")', runtime)
        self.assertIn('native_v1_auth_args+=(--password "$OPENCODE_SERVER_PASSWORD")', runtime)
        self.assertIn('attach "http://127.0.0.1:$host_port" --dir "$cwd" "${native_v1_auth_args[@]}"', runtime)
        self.assertIn('run --attach "http://127.0.0.1:$host_port" --dir "$cwd" "${native_v1_auth_args[@]}"', runtime)


if __name__ == "__main__":
    unittest.main()
