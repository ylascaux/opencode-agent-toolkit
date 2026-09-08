import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConfigParityTests(unittest.TestCase):
    def setUp(self):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True, capture_output=True, text=True)
        self.v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        self.v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())

    def test_agent_sets_match(self):
        self.assertEqual(set(self.v1["agent"]), set(self.v2["agents"]))
        self.assertEqual(len(self.v1["agent"]), 35)

    def test_command_sets_match(self):
        self.assertEqual(set(self.v1["command"]), set(self.v2["commands"]))

    def test_meta_router_is_default(self):
        self.assertEqual(self.v1["default_agent"], "meta-router")
        self.assertEqual(self.v2["default_agent"], "meta-router")
        self.assertEqual(self.v1["agent"]["meta-router"]["mode"], "primary")
        self.assertEqual(self.v2["agents"]["meta-router"]["mode"], "primary")

    def test_nested_subagents_enabled(self):
        self.assertGreaterEqual(self.v1["subagent_depth"], 2)
        self.assertGreaterEqual(self.v2["experimental"]["subagent_depth"], 2)
        self.assertEqual(self.v1["agent"]["orchestrator"]["mode"], "all")
        self.assertEqual(self.v2["agents"]["orchestrator"]["mode"], "all")

    def test_every_model_env_is_documented(self):
        env_text = (ROOT / ".env.example").read_text()
        vars_in_env = set(re.findall(r"^(MODEL_[A-Z0-9_]+)=", env_text, re.MULTILINE))
        for agent in self.v2["agents"].values():
            match = re.fullmatch(r"\{env:(MODEL_[A-Z0-9_]+)\}", agent["model"])
            self.assertIsNotNone(match, agent["model"])
            self.assertIn(match.group(1), vars_in_env)

    def test_terraform_destructive_commands_denied(self):
        bash = self.v1["agent"]["terraform-terragrunt"]["permission"]["bash"]
        for command in ["terraform apply*", "terraform destroy*", "tofu apply*", "tofu destroy*", "terragrunt apply*", "terragrunt destroy*"]:
            self.assertEqual(bash[command], "deny")


if __name__ == "__main__":
    unittest.main()
