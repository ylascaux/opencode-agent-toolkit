import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
CONTRACTS = ROOT / "contracts"

RESEARCH_AGENTS = {
    "source-discovery": ("low", "fast"),
    "structured-extractor": ("medium", "general"),
    "entity-resolver": ("medium", "reasoning"),
}


class ResearchPipelineTests(unittest.TestCase):
    def test_research_agents_are_generic_bounded_leaves(self):
        for name, (tier, profile) in RESEARCH_AGENTS.items():
            config = json.loads((AGENTS / name / "agent.json").read_text())
            prompt = (AGENTS / name / "prompt.md").read_text().lower()
            self.assertIn("orchestrator", config["parents"], name)
            self.assertIn("research-runner", config["parents"], name)
            self.assertEqual(config["mode"], "subagent", name)
            self.assertEqual(config["tier"], tier, name)
            self.assertEqual(config["model_profile"], profile, name)
            self.assertNotIn("livalyo", prompt, name)
            self.assertIn("do not", prompt, name)

    def test_external_runner_has_no_local_mutation_capabilities(self):
        config = json.loads((AGENTS / "research-runner" / "agent.json").read_text())
        permissions = json.loads((AGENTS / "research-runner" / "permissions.json").read_text())
        prompt = (AGENTS / "research-runner" / "prompt.md").read_text().lower()
        self.assertEqual(config["parents"], ["meta-router"])
        self.assertEqual(config["tier"], "low")
        for permission in ["edit", "bash", "read", "skill"]:
            self.assertEqual(permissions[permission], "deny")
        self.assertIn("untrusted", prompt)
        self.assertIn("never mutate", prompt)

    def test_research_contracts_are_strict_generic_envelopes(self):
        job = json.loads((CONTRACTS / "research-job.schema.json").read_text())
        result = json.loads((CONTRACTS / "research-result.schema.json").read_text())

        self.assertFalse(job["additionalProperties"])
        self.assertFalse(result["additionalProperties"])
        self.assertEqual(job["properties"]["schema_version"]["const"], "1")
        self.assertEqual(result["properties"]["schema_version"]["const"], "1")
        self.assertIn("target_schema", job["properties"])
        self.assertIn("policy", job["required"])
        self.assertIn("data", result["required"])
        self.assertIn("evidence", result["required"])
        self.assertIn("confidence", result["required"])

    def test_contracts_keep_domain_rules_outside_toolkit(self):
        text = (
            (CONTRACTS / "research-job.schema.json").read_text()
            + (CONTRACTS / "research-result.schema.json").read_text()
        ).lower()
        for forbidden in [
            "livalyo",
            "repair score",
            "replace score",
            "iot score",
            "canonical device",
        ]:
            self.assertNotIn(forbidden, text)

    def test_escalation_contract_uses_capability_tiers_not_provider_models(self):
        job = json.loads((CONTRACTS / "research-job.schema.json").read_text())
        result = json.loads((CONTRACTS / "research-result.schema.json").read_text())
        self.assertEqual(job["properties"]["policy"]["properties"]["max_tier"]["enum"], ["low", "medium", "high"])
        self.assertEqual(result["properties"]["execution"]["properties"]["tier"]["enum"], ["low", "medium", "high"])
        self.assertNotIn("gpt-", json.dumps(job).lower())
        self.assertNotIn("gpt-", json.dumps(result).lower())


if __name__ == "__main__":
    unittest.main()
