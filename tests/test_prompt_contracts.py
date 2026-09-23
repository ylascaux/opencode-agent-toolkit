import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / ".generated" / "prompts"
CORE = {
    "meta-router", "orchestrator", "builder", "debugger", "tester",
    "reviewer", "platform-architect", "security-lead", "research-runner",
}


class PromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], check=True)
        cls.config = json.loads((ROOT / "opencode.jsonc").read_text())

    def test_every_active_agent_has_structured_prompt(self):
        self.assertEqual(set(self.config["agent"]), CORE)
        required = [
            "# Role",
            "## Operating method",
            "## Non-negotiables",
            "## Evidence discipline",
            "## Runtime contracts",
            "## Stop conditions",
            "## Handoff",
            "## External research",
        ]
        for name in CORE:
            text = (PROMPTS / f"{name}.md").read_text()
            for heading in required:
                self.assertIn(heading, text, f"{name}: {heading}")

    def test_handoff_schema_supports_mediated_agent_communication(self):
        data = json.loads((ROOT / "contracts" / "agent-handoff.schema.json").read_text())
        self.assertEqual(data["title"], "Agent Handoff")
        self.assertIn("confidence", data["required"])
        self.assertIn("state_updates", data["properties"])
        request = data["properties"]["handoff_request"]
        self.assertEqual(request["required"], ["agent", "reason", "task"])
        self.assertIn("required_evidence", request["properties"])

    def test_generated_prompts_embed_handoff_contract_without_runtime_schema_reads(self):
        for name in CORE:
            text = (PROMPTS / f"{name}.md").read_text()
            self.assertNotIn("contracts/agent-handoff.schema.json", text, name)
            self.assertIn("Agent Handoff required fields:", text, name)
            self.assertIn("state_updates", text, name)
            self.assertIn("handoff_request", text, name)
            self.assertIn("Do not try to read them from the target repository at runtime.", text, name)

    def test_router_and_orchestrator_define_mediated_handoffs(self):
        router = (PROMPTS / "meta-router.md").read_text().lower()
        orch = (PROMPTS / "orchestrator.md").read_text().lower()
        self.assertIn("## agent communication", router)
        self.assertIn("do not hold free-form peer conversations", router)
        self.assertIn("compact mission state", router)
        self.assertIn("## agent communication", orch)
        self.assertIn("children return structured handoffs", orch)
        self.assertIn("maximum delegation depth is two", orch)

    def test_architecture_security_and_research_are_self_contained(self):
        architect = (PROMPTS / "platform-architect.md").read_text().lower()
        security = (PROMPTS / "security-lead.md").read_text().lower()
        research = (PROMPTS / "research-runner.md").read_text().lower()
        self.assertIn("not separate agent identities", architect)
        self.assertIn("do not delegate to appsec/iac/pentest/secrets subagents", security)
        self.assertIn("context7", research)
        self.assertIn("single agent", research)

    def test_reviewer_is_independent_and_read_only(self):
        text = (PROMPTS / "reviewer.md").read_text().lower()
        self.assertIn("independent read-only review", text)
        self.assertIn("do not implement fixes", text)
        self.assertIn("producer's summary", text)


if __name__ == "__main__":
    unittest.main()
