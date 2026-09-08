import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True)
        cls.config = json.loads((ROOT / "opencode.jsonc").read_text())

    def test_every_agent_has_structured_prompt(self):
        required = [
            "# Role",
            "## Operating method",
            "## Non-negotiables",
            "## Evidence discipline",
            "## Runtime contracts",
            "## Stop conditions",
            "## Handoff",
        ]
        for name in self.config["agent"]:
            path = ROOT / "prompts" / f"{name}.md"
            self.assertTrue(path.exists(), name)
            text = path.read_text()
            for heading in required:
                self.assertIn(heading, text, f"{name}: {heading}")

    def test_handoff_schema_is_valid_json(self):
        data = json.loads((ROOT / "contracts" / "agent-handoff.schema.json").read_text())
        self.assertEqual(data["title"], "Agent Handoff")
        self.assertIn("confidence", data["required"])

    def test_routing_schema_is_valid_json(self):
        data = json.loads((ROOT / "contracts" / "routing-decision.schema.json").read_text())
        self.assertEqual(data["title"], "Routing Decision")
        self.assertIn("route", data["required"])

    def test_generated_prompts_embed_contracts_without_runtime_file_reads(self):
        for name in self.config["agent"]:
            text = (ROOT / "prompts" / f"{name}.md").read_text()
            self.assertNotIn("`contracts/agent-handoff.schema.json`", text, name)
            self.assertNotIn("`contracts/routing-decision.schema.json`", text, name)
            self.assertIn("Agent Handoff required fields:", text, name)
            self.assertIn("Routing Decision required fields:", text, name)
            self.assertIn("Do not try to read them from the target repository at runtime.", text, name)

        meta_router = (ROOT / "prompts" / "meta-router.md").read_text()
        self.assertIn("embedded Routing Decision contract below", meta_router)

    def test_architecture_workflow_is_staged_and_independent(self):
        meta_router = (ROOT / "prompts" / "meta-router.md").read_text().lower()
        self.assertIn("## architecture delivery workflow", meta_router)
        self.assertIn("platform-architect", meta_router)
        self.assertIn("review-lead", meta_router)
        self.assertIn("security-lead", meta_router)
        self.assertIn("parallelizable", meta_router)
        self.assertIn("final independent reviewer", meta_router)

    def test_platform_architect_produces_review_ready_handoff(self):
        text = (ROOT / "prompts" / "platform-architect.md").read_text().lower()
        self.assertIn("## review-ready architecture output", text)
        self.assertIn("docs-writer", text)
        self.assertIn("artifact path", text)
        self.assertIn("review-lead", text)
        self.assertIn("security-lead", text)
        self.assertIn("do not self-certify", text)

    def test_review_lead_rechecks_architecture_from_direct_evidence(self):
        text = (ROOT / "prompts" / "review-lead.md").read_text().lower()
        self.assertIn("## architecture review policy", text)
        self.assertIn("direct repository evidence", text)
        self.assertIn("project-scanner", text)
        self.assertIn("aws-platform", text)
        self.assertIn("migration/rollback gaps", text)
        self.assertIn("parallelize independent read-only dimensions", text)

    def test_common_prompt_encourages_native_parallel_read_only_gates(self):
        text = (ROOT / "prompts" / "meta-router.md").read_text().lower()
        self.assertIn("native background subagents", text)
        self.assertIn("same completed artifact", text)

    def test_leads_use_delegation_economy_but_leaves_do_not(self):
        for name in ["meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead"]:
            text = (ROOT / "prompts" / f"{name}.md").read_text().lower()
            self.assertIn("## delegation economy", text, name)
            self.assertIn("smallest sufficient set of children", text, name)
            self.assertIn("do not delegate merely because a technology is detected", text, name)
            self.assertIn("once a child returns complete", text, name)

        for name in ["builder", "terraform-terragrunt", "project-scanner", "reviewer"]:
            text = (ROOT / "prompts" / f"{name}.md").read_text().lower()
            self.assertNotIn("## delegation economy", text, name)

    def test_platform_architect_requires_material_specialist_trigger(self):
        text = (ROOT / "prompts" / "platform-architect.md").read_text().lower()
        self.assertIn("## architecture specialist trigger policy", text)
        self.assertIn("do not fan out to every technology detected", text)
        self.assertIn(".tf", text)
        self.assertIn("terraform-terragrunt", text)
        self.assertIn("module/state/provider/lifecycle/dependency/migration", text)
        self.assertIn("material architecture decision", text)

    def test_evidence_auditor_avoids_numeric_confidence(self):
        text = (ROOT / "prompts" / "evidence-auditor.md").read_text().lower()
        self.assertIn("high/medium/low", text)
        self.assertNotIn("score from 0 to 100", text)


if __name__ == "__main__":
    unittest.main()
