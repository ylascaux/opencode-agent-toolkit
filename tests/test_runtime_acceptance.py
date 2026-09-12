import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RuntimeAcceptanceSurfaceTests(unittest.TestCase):
    def test_acceptance_runs_from_disposable_toolkit_copy(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("copy_toolkit", text)
        self.assertIn("TemporaryDirectory", text)
        self.assertIn('".env", ".env.local"', text)
        self.assertIn("sanitized_environment", text)
        self.assertNotIn("base_env = os.environ.copy()", text)

    def test_acceptance_uses_real_memory_plugin_not_synthetic_cli(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("OAT_ACCEPTANCE_MEMORY_PLUGIN_DIR", text)
        self.assertIn('plugin / "dist" / "cli.js"', text)
        self.assertNotIn("make_mcp_plugin", text)
        self.assertIn("memory_status", text)
        self.assertIn("memory_candidates", text)

    def test_codex_regression_uses_preexisting_nonempty_skill_directory(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn('"security-review" / "references" / "user.txt"', text)
        self.assertIn("partial writes", text)

    def test_docker_acceptance_probes_real_v2_skill_registry(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("ctx.skill.list()", text)
        self.assertIn("project-skill", text)
        self.assertIn("real OpenCode V2", text)

    def test_acceptance_workflow_pins_real_memory_plugin(self):
        workflow = (ROOT / ".github" / "workflows" / "acceptance.yml").read_text()
        self.assertIn("ylascaux/opencode-memory-plugin", workflow)
        self.assertIn("b573f3ba0b253abeb26bbb01eaee0c5a8b5ab518", workflow)
        self.assertIn("OAT_ACCEPTANCE_DOCKER", workflow)
        self.assertIn("opencode-agent-toolkit:acceptance", workflow)


if __name__ == "__main__":
    unittest.main()
