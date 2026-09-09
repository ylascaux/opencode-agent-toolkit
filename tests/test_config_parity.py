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
SENSITIVE_PATTERNS = {
    "*.env", "*.env.*", "**/.env", "**/.env.*", "*.pem", "*.key",
    "**/.ssh/**", "**/.aws/credentials", "*id_rsa*", "*id_ed25519*",
}
READ_ONLY_GIT = {
    "git status*", "git diff*", "git show*", "git log*", "git rev-parse*",
    "git rev-list*", "git ls-files*", "git ls-tree*", "git grep*", "git blame*",
}


def last_v2_effect(agent: dict, action: str, resource: str) -> str | None:
    effect = None
    for rule in agent["permissions"]:
        if rule.get("action") != action:
            continue
        if rule.get("resource") in {"*", resource}:
            effect = rule.get("effect")
    return effect


class ConfigPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True, capture_output=True, text=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], check=True, capture_output=True, text=True)
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

    def test_leaf_agents_cannot_delegate_unattended(self):
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
                self.assertEqual(last_v2_effect(agent, "subagent", "arbitrary-agent"), "deny", name)

    def test_meta_router_catalog_is_small_and_hierarchical(self):
        task = self.v1["agent"]["meta-router"]["permission"]["task"]
        allowed = {name for name, effect in task.items() if name != "*" and effect == "allow"}
        self.assertEqual(allowed, EXPECTED_META_CHILDREN)
        self.assertLessEqual(len(allowed), 8)

    def test_every_agent_has_open_web_and_prompted_skill_policy(self):
        for name, agent in self.v1["agent"].items():
            p = agent["permission"]
            self.assertEqual(p["webfetch"], "allow", name)
            self.assertEqual(p["websearch"], "allow", name)
            self.assertEqual(p["skill"], "ask", name)
        for name, agent in self.v2["agents"].items():
            self.assertEqual(last_v2_effect(agent, "webfetch", "*"), "allow", name)
            self.assertEqual(last_v2_effect(agent, "websearch", "*"), "allow", name)
            self.assertEqual(last_v2_effect(agent, "skill", "*"), "ask", name)

    def test_sensitive_reads_require_approval_instead_of_hard_deny(self):
        for name, agent in self.v1["agent"].items():
            read = agent["permission"]["read"]
            for pattern in SENSITIVE_PATTERNS:
                self.assertEqual(read[pattern], "ask", f"{name}: {pattern}")
        for name, agent in self.v2["agents"].items():
            for pattern in SENSITIVE_PATTERNS:
                self.assertEqual(last_v2_effect(agent, "read", pattern), "ask", f"{name}: {pattern}")

    def test_edit_is_allow_for_writers_and_ask_for_everyone_else(self):
        for name, agent in self.v1["agent"].items():
            expected = "allow" if name in WRITERS else "ask"
            self.assertEqual(agent["permission"]["edit"], expected, name)
        for name, agent in self.v2["agents"].items():
            expected = "allow" if name in WRITERS else "ask"
            self.assertEqual(last_v2_effect(agent, "edit", "*"), expected, name)

    def test_non_destructive_shell_defaults_to_ask_and_safe_git_is_allowed(self):
        for name, agent in self.v1["agent"].items():
            bash = agent["permission"]["bash"]
            self.assertEqual(bash["*"], "ask", name)
            for command in READ_ONLY_GIT:
                self.assertEqual(bash[command], "allow", f"{name}: {command}")
        for name, agent in self.v2["agents"].items():
            self.assertEqual(last_v2_effect(agent, "shell", "some harmless custom command"), "ask", name)
            for command in READ_ONLY_GIT:
                self.assertEqual(last_v2_effect(agent, "shell", command), "allow", f"{name}: {command}")

    def test_platform_architect_can_delegate_durable_document_writing(self):
        agent = self.v1["agent"]["platform-architect"]
        self.assertEqual(agent["permission"]["edit"], "ask")
        self.assertEqual(agent["permission"]["task"]["docs-writer"], "allow")

    def test_project_scanner_can_read_projects_without_prompt(self):
        agent = self.v1["agent"]["project-scanner"]
        external = agent["permission"]["external_directory"]
        self.assertEqual(external["*"], "ask")
        self.assertEqual(external["~/Projects/**"], "allow")

    def test_review_lead_can_independently_recheck_architecture_evidence(self):
        agent = self.v1["agent"]["review-lead"]
        task = agent["permission"]["task"]
        for child in [
            "reviewer", "project-scanner", "aws-platform", "kubernetes", "sre",
            "observability", "finops", "database", "networking", "iac-security",
        ]:
            self.assertEqual(task[child], "allow", child)

    def test_architecture_command_requires_independent_post_design_review(self):
        template = self.v1["command"]["architecture"]["template"].lower()
        self.assertIn("platform-architect", template)
        self.assertIn("docs-writer", template)
        self.assertIn("review-lead", template)
        self.assertIn("security-lead", template)
        self.assertIn("parallel", template)
        self.assertIn("self-review", template)

    def test_architecture_review_command_is_independent(self):
        template = self.v1["command"]["architecture-review"]["template"].lower()
        self.assertIn("review-lead", template)
        self.assertIn("project-scanner", template)
        self.assertIn("producer handoff", template)

    def test_destructive_commands_stay_denied(self):
        for name, agent in self.v1["agent"].items():
            bash = agent["permission"]["bash"]
            for command in [
                "rm -rf*", "git reset --hard*", "git push --force*",
                "terraform apply*", "terraform destroy*", "tofu apply*",
                "tofu destroy*", "terragrunt apply*", "terragrunt destroy*",
                "kubectl delete*", "helm uninstall*",
            ]:
                self.assertEqual(bash[command], "deny", f"{name}: {command}")


if __name__ == "__main__":
    unittest.main()
