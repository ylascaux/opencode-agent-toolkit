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
        required = ["# Role", "## Operating method", "## Non-negotiables", "## Evidence discipline", "## Stop conditions", "## Handoff"]
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

    def test_evidence_auditor_avoids_numeric_confidence(self):
        text = (ROOT / "prompts" / "evidence-auditor.md").read_text().lower()
        self.assertIn("high/medium/low", text)
        self.assertNotIn("score from 0 to 100", text)


if __name__ == "__main__":
    unittest.main()
