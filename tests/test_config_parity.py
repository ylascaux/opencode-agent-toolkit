import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEADS = {"meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead"}
EXPECTED_META_CHILDREN = {
    "orchestrator", "review-lead", "platform-architect", "security-lead",
    "arbiter", "deep-reasoner", "evidence-auditor",
}
WRITERS = {
    "builder", "tester", "mock-generator", "debugger", "python-specialist",
    "go-specialist", "cicd", "docs-writer", "terraform-terragrunt",
}
SECRET_PATTERNS = {
    "*.env", "*.env.*", "**/.env", "**/.env.*", "*.pem", "*.key",
    "**/.ssh/**", "**/.aws/credentials", "*id_rsa*", "*id_ed25519*",
}


class ConfigPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True, capture_output=True, text=True)
        cls.v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        cls.v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())

    def test_agent_sets_match_and_count(self):
        self.assertEqual(set(self.v1["agent"]), set(self.v2["agents"]))
        self.assertEqual(len(self.v1["agent"]), 37)

    def test_command_sets_match(self):
        self.assertEqual(set(self.v1["command"]), set(self.v2["commands"]))

    def test_meta_router_is_default(self):
        self.assertEqual(self.v1["default_agent"], "meta-router")
        self.assertEqual(self.v2["default_agent"], "meta-router")
        self.assertEqual(self.v1["agent"]["meta-router"]["mode"], "primary")
        self.assertEqual(self.v2["agents"]["meta-router"]["mode"], "primary")

    def test_nested_subagents_stay_bounded(self):
        self.assertEqual(self.v1["subagent_depth"], 2)
        self.assertEqual(self.v2["experimental"]["subagent_depth"], 2)
        self.assertEqual(self.v1["agent"]["orchestrator"]["mode"], "all")
        self.assertEqual(self.v2["agents"]["orchestrator"]["mode"], "all")

    def test_every_model_env_has_a_tier(self):
        tiers = json.loads((ROOT / "profiles" / "agent-tiers.json").read_text())
        expected_model_envs = set()
        for agent in self.v2["agents"].values():
            match = re.fullmatch(r"\{env:(MODEL_[A-Z0-9_]+)\}", agent["model"])
            self.assertIsNotNone(match, agent["model"])
            expected_model_envs.add(match.group(1))
        self.assertEqual(len(expected_model_envs), 37)
        self.assertEqual(set(tiers), expected_model_envs)
        self.assertTrue(set(tiers.values()) <= {"low", "medium", "high"})

    def test_default_env_defines_three_tiers(self):
        env_text = (ROOT / ".env.example").read_text()
        for variable in ["MODEL_PROFILE", "MODEL_LOW", "MODEL_MEDIUM", "MODEL_HIGH"]:
            self.assertRegex(env_text, rf"(?m)^{variable}=.+$")
        self.assertIn("MODEL_PROFILE=copilot", env_text)
        self.assertIn("github-copilot/gpt-5.6-luna", env_text)
        self.assertIn("github-copilot/gpt-5.6-terra", env_text)
        self.assertIn("github-copilot/gpt-5.6-sol", env_text)

    def test_leaf_agents_cannot_delegate(self):
        for name, agent in self.v1["agent"].items():
            task = agent["permission"]["task"]
            self.assertEqual(task["*"], "deny", name)
            if name not in LEADS:
                self.assertEqual(task, {"*": "deny"}, name)
        for name, agent in self.v2["agents"].items():
            rules = [r for r in agent["permissions"] if r["action"] == "subagent"]
            self.assertTrue(rules, name)
            self.assertEqual(rules[0], {"action": "subagent", "resource": "*", "effect": "deny"})
            if name not in LEADS:
                self.assertEqual(len(rules), 1, name)

    def test_meta_router_catalog_is_small_and_hierarchical(self):
        task = self.v1["agent"]["meta-router"]["permission"]["task"]
        allowed = {name for name, effect in task.items() if name != "*" and effect == "allow"}
        self.assertEqual(allowed, EXPECTED_META_CHILDREN)
        self.assertLessEqual(len(allowed), 8)

    def test_every_agent_has_explicit_web_and_skill_policy(self):
        for name, agent in self.v1["agent"].items():
            p = agent["permission"]
            self.assertIn(p["webfetch"], {"allow", "ask", "deny"}, name)
            self.assertIn(p["websearch"], {"allow", "ask", "deny"}, name)
            self.assertIn(p["skill"], {"allow", "ask", "deny"}, name)

    def test_sensitive_reads_are_denied_everywhere(self):
        for name, agent in self.v1["agent"].items():
            read = agent["permission"]["read"]
            for pattern in SECRET_PATTERNS:
                self.assertEqual(read[pattern], "deny", f"{name}: {pattern}")

    def test_only_expected_agents_can_edit(self):
        for name, agent in self.v1["agent"].items():
            expected = "allow" if name in WRITERS else "deny"
            self.assertEqual(agent["permission"]["edit"], expected, name)

    def test_reviewers_can_collect_safe_git_evidence_without_editing(self):
        for name in ["reviewer", "evidence-auditor"]:
            agent = self.v1["agent"][name]
            self.assertEqual(agent["permission"]["edit"], "deny")
            bash = agent["permission"]["bash"]
            self.assertEqual(bash["*"], "ask")
            for command in ["git status*", "git diff*", "git show*", "git log*", "git rev-parse*"]:
                self.assertEqual(bash[command], "allow")

    def test_terraform_destructive_commands_denied(self):
        bash = self.v1["agent"]["terraform-terragrunt"]["permission"]["bash"]
        for command in ["terraform apply*", "terraform destroy*", "tofu apply*", "tofu destroy*", "terragrunt apply*", "terragrunt destroy*"]:
            self.assertEqual(bash[command], "deny")


if __name__ == "__main__":
    unittest.main()
