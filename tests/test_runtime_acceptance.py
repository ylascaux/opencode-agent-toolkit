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

    def test_acceptance_uses_real_memory_plugin_or_explicit_skip_only(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("OAT_ACCEPTANCE_MEMORY_PLUGIN_DIR", text)
        self.assertIn("OAT_ACCEPTANCE_SKIP_MEMORY", text)
        self.assertIn('plugin / "dist" / "cli.js"', text)
        self.assertNotIn("make_mcp_plugin", text)
        self.assertIn("memory_status", text)
        self.assertIn("memory_candidates", text)

    def test_codex_regression_uses_preexisting_nonempty_skill_directory(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn('"security-review" / "references" / "user.txt"', text)
        self.assertIn("partial writes", text)

    def test_legacy_docker_acceptance_uses_real_v2_skill_http_api(self):
        text = (ROOT / "scripts" / "opencode-v2-skill-smoke").read_text()
        self.assertIn("/api/skill", text)
        self.assertIn("opencode2 serve", text)
        self.assertIn("project-skill", text)
        self.assertIn("terraform-review", text)
        self.assertNotIn("ctx.skill.list()", text)

    def test_acceptance_workflow_keeps_native_core_mandatory_and_private_mcp_conditional(self):
        workflow = (ROOT / ".github" / "workflows" / "acceptance.yml").read_text()
        native = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn('OAT_ACCEPTANCE_SKIP_MEMORY: "1"', workflow)
        self.assertIn("OAT_MEMORY_PLUGIN_TOKEN", workflow)
        self.assertIn("ylascaux/opencode-memory-plugin", workflow)
        self.assertIn("b573f3ba0b253abeb26bbb01eaee0c5a8b5ab518", workflow)
        self.assertIn("MEMORY_TOKEN != ''", workflow)
        self.assertIn("native-v2:", native)
        self.assertIn("@opencode/cli@0.0.0-beta-19507", native)
        self.assertIn("/api/health", native)
        self.assertIn("/api/skill", native)
        self.assertIn("x-opencode-directory", native)
        self.assertNotIn("docker run", workflow + native)
        self.assertNotIn("continue-on-error", workflow + native)


if __name__ == "__main__":
    unittest.main()
