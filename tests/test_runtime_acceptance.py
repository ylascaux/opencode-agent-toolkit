import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeAcceptanceSurfaceTests(unittest.TestCase):
    def test_acceptance_runs_from_disposable_toolkit_copy(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("copy_toolkit", text)
        self.assertIn("TemporaryDirectory", text)
        self.assertIn("isolated_environment", text)
        self.assertNotIn("fake-v2", text)
        self.assertNotIn("OPENCODE_MAJOR", text)

    def test_acceptance_checks_single_open_code_launcher(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn("OpenCode 2 launcher routing", text)
        self.assertIn('root / "opencode.jsonc"', text)
        self.assertNotIn("opencode.v2.jsonc", text)

    def test_codex_regression_uses_preexisting_nonempty_skill_directory(self):
        text = (ROOT / "scripts" / "runtime-acceptance").read_text()
        self.assertIn('"security-review" / "references" / "user.txt"', text)
        self.assertIn("partial writes", text)

    def test_acceptance_workflow_uses_released_runtime_only(self):
        workflow = (ROOT / ".github" / "workflows" / "acceptance.yml").read_text()
        self.assertIn("opencode-agent-toolkit:acceptance", workflow)
        self.assertNotIn("opencode-v2-skill-smoke", workflow)
        self.assertNotIn("opencode-memory-plugin", workflow)


if __name__ == "__main__":
    unittest.main()
