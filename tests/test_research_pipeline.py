import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
CONTRACTS = ROOT / "contracts"


class ResearchPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True)
        cls.config = json.loads((ROOT / "opencode.jsonc").read_text())

    def test_research_is_one_active_core_agent(self):
        catalog = set(json.loads((AGENTS / "catalog.json").read_text())["agents"])
        self.assertIn("research-runner", catalog)
        for legacy in ["source-discovery", "structured-extractor", "entity-resolver", "evidence-auditor", "deep-reasoner"]:
            self.assertNotIn(legacy, catalog)

        config = json.loads((AGENTS / "research-runner" / "agent.json").read_text())
        prompt = (AGENTS / "research-runner" / "prompt.md").read_text().lower()
        self.assertEqual(config["parents"], ["meta-router", "orchestrator"])
        self.assertEqual(config["tier"], "medium")
        self.assertEqual(config["mode"], "subagent")
        self.assertIn("context7", prompt)
        self.assertIn("single agent", prompt)
        self.assertIn("never mutate", prompt)

    def test_research_runner_can_read_and_use_skills_but_cannot_mutate_or_shell(self):
        permission = self.config["agent"]["research-runner"]["permission"]
        self.assertEqual(permission["edit"], "deny")
        self.assertEqual(permission["bash"], "deny")
        self.assertEqual(permission["skill"], "ask")
        self.assertEqual(permission["read"]["*"], "allow")
        self.assertEqual(permission["read"]["**/.ssh/**"], "deny")
        self.assertEqual(permission["external_directory"]["*"], "deny")
        self.assertEqual(permission["websearch"], "allow")
        self.assertEqual(permission["webfetch"], "allow")

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
