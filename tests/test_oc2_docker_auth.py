import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Oc2DockerAuthTests(unittest.TestCase):
    def test_openai_shortcut_uses_headless_oauth(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()

        self.assertIn('"${2:-}" == "openai"', runtime)
        self.assertIn('opencode2 auth login -p openai -m "ChatGPT Pro/Plus (headless)"', runtime)
        self.assertIn("For ChatGPT Pro/Plus use: oc2 auth openai", runtime)

    def test_browser_oauth_port_is_not_published(self):
        compose = (ROOT / "compose.yaml").read_text()
        env_example = (ROOT / ".env.example").read_text()

        self.assertNotIn("OAT_OC2_OAUTH_PORT", compose)
        self.assertNotIn(":1455", compose)
        self.assertNotIn("OAT_OC2_OAUTH_PORT", env_example)
        self.assertIn("oc2 auth openai", env_example)

    def test_server_password_is_documented_as_transport_auth_only(self):
        env_example = (ROOT / ".env.example").read_text()

        self.assertIn("OPENCODE_SERVER_PASSWORD", env_example)
        self.assertIn("does not authenticate providers", env_example)


if __name__ == "__main__":
    unittest.main()
