import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeAcceptanceSurfaceTests(unittest.TestCase):
    def test_acceptance_runs_from_disposable_toolkit_copy(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("copy_toolkit", text)
        self.assertIn("TemporaryDirectory", text)
        self.assertIn('".env", ".env.local"', text)
        self.assertIn("isolated_environment", text)
        self.assertNotIn("os.environ.copy()", text)

    def test_acceptance_has_single_stable_opencode_launcher(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn('root / "opencode.jsonc"', text)
        self.assertNotIn("opencode.v2.jsonc", text)
        self.assertNotIn("opencode2", text)
        self.assertNotIn("OPENCODE_MAJOR", text)

    def test_codex_regression_keeps_conflict_protection(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn('"security-review" / "references" / "user.txt"', text)
        self.assertIn("partial writes", text)

    def test_docker_acceptance_uses_stable_skill_http_api(self):
        text = (ROOT / "scripts" / "opencode-skill-smoke").read_text()
        self.assertIn("/api/skill", text)
        self.assertIn("opencode serve", text)
        self.assertIn("project-skill", text)
        self.assertIn("terraform-review", text)
        self.assertNotIn("opencode2", text)

    def test_acceptance_workflow_has_no_private_memory_or_beta_lane(self):
        workflow = (ROOT / ".github" / "workflows" / "acceptance.yml").read_text()
        self.assertNotIn("OAT_MEMORY_PLUGIN_TOKEN", workflow)
        self.assertNotIn("ylascaux/opencode-memory-plugin", workflow)
        self.assertNotIn("opencode-v2-skill-smoke", workflow)
        self.assertIn("scripts/opencode-skill-smoke", workflow)
        self.assertIn("opencode-agent-toolkit:acceptance", workflow)


if __name__ == "__main__":
    unittest.main()
