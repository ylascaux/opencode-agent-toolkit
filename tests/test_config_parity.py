import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"

CORE = {
    "meta-router",
    "orchestrator",
    "builder",
    "debugger",
    "tester",
    "reviewer",
    "platform-architect",
    "security-lead",
    "research-runner",
}
HIGH = {"orchestrator", "reviewer", "platform-architect", "security-lead"}
WRITERS = {"builder", "debugger", "tester"}
READ_ONLY = {"reviewer", "platform-architect", "security-lead", "research-runner"}
LEGACY_NAMES = {
    "api-contract", "appsec", "arbiter", "architecture-designer", "aws-platform",
    "brainstorm", "cicd", "database", "deep-reasoner", "docs-writer",
    "entity-resolver", "evidence-auditor", "finops", "go-specialist",
    "iac-security", "kubernetes", "mock-generator", "networking", "observability",
    "pentest", "performance", "planner", "project-scanner", "python-specialist",
    "review-lead", "secrets", "source-discovery", "sre", "structured-extractor",
    "supply-chain", "terraform-terragrunt", "threat-model",
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
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, check=True)
        cls.v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        cls.v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())

    def test_agent_sets_match_core_catalog(self):
        catalog = set(json.loads((AGENTS_DIR / "catalog.json").read_text())["agents"])
        self.assertEqual(catalog, CORE)
        self.assertEqual(set(self.v1["agent"]), CORE)
        self.assertEqual(set(self.v2["agents"]), CORE)

    def test_meta_router_is_default_and_depth_is_bounded(self):
        self.assertEqual(self.v1["default_agent"], "meta-router")
        self.assertEqual(self.v2["default_agent"], "meta-router")
        self.assertEqual(self.v1["subagent_depth"], 2)
        self.assertEqual(self.v2["experimental"]["subagent_depth"], 2)

    def test_model_tiers_match_quality_policy(self):
        for name in CORE:
            cfg = json.loads((AGENTS_DIR / name / "agent.json").read_text())
            if name in HIGH:
                self.assertEqual(cfg["tier"], "high", name)
            else:
                self.assertEqual(cfg["tier"], "medium", name)

    def test_delegation_graph_is_small_and_mediated(self):
        meta = self.v1["agent"]["meta-router"]["permission"]["task"]
        self.assertEqual(
            {name for name, effect in meta.items() if name != "*" and effect == "allow"},
            {"orchestrator", "reviewer", "platform-architect", "security-lead", "research-runner"},
        )
        orch = self.v1["agent"]["orchestrator"]["permission"]["task"]
        self.assertEqual(
            {name for name, effect in orch.items() if name != "*" and effect == "allow"},
            {"builder", "debugger", "tester", "reviewer", "security-lead", "research-runner"},
        )
        for leaf in ["builder", "debugger", "tester", "reviewer", "security-lead", "research-runner"]:
            self.assertEqual(self.v1["agent"][leaf]["permission"]["task"], {"*": "deny"}, leaf)

    def test_edit_and_shell_policy_match_roles(self):
        for name, agent in self.v1["agent"].items():
            edit = agent["permission"]["edit"]
            if name in WRITERS:
                self.assertEqual(edit, "allow", name)
            elif name in READ_ONLY:
                self.assertEqual(edit, "deny", name)
            else:
                self.assertEqual(edit, "ask", name)

            bash = agent["permission"]["bash"]
            if name == "research-runner":
                self.assertEqual(bash, "deny")
            else:
                self.assertEqual(bash["*"], "ask", name)

    def test_sensitive_reads_and_destructive_commands_stay_protected(self):
        for name, agent in self.v1["agent"].items():
            read = agent["permission"]["read"]
            for pattern in ["*.env", "*.pem", "*.key"]:
                self.assertEqual(read[pattern], "ask", f"{name}: {pattern}")
            for pattern in ["**/.ssh/**", "**/.aws/**", "**/.kube/**"]:
                self.assertEqual(read[pattern], "deny", f"{name}: {pattern}")

            bash = agent["permission"]["bash"]
            if bash == "deny":
                continue
            for command in [
                "rm -rf*", "git reset --hard*", "git push --force*",
                "terraform apply*", "terraform destroy*", "tofu apply*", "tofu destroy*",
                "terragrunt apply*", "terragrunt destroy*", "kubectl delete*", "helm uninstall*",
            ]:
                self.assertEqual(bash[command], "deny", f"{name}: {command}")

    def test_v2_permissions_match_core_intent(self):
        for name, agent in self.v2["agents"].items():
            self.assertEqual(last_v2_effect(agent, "websearch", "*"), "allow", name)
            self.assertEqual(last_v2_effect(agent, "webfetch", "*"), "allow", name)
            expected_edit = "allow" if name in WRITERS else ("deny" if name in READ_ONLY else "ask")
            self.assertEqual(last_v2_effect(agent, "edit", "*"), expected_edit, name)

    def test_commands_do_not_reference_legacy_agents(self):
        for name, command in self.v2["commands"].items():
            template = command["template"]
            for legacy in LEGACY_NAMES:
                self.assertNotIn(legacy, template, f"{name}: {legacy}")

    def test_generation_is_deterministic(self):
        first = (ROOT / "opencode.v2.jsonc").read_bytes()
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, check=True)
        self.assertEqual(first, (ROOT / "opencode.v2.jsonc").read_bytes())


if __name__ == "__main__":
    unittest.main()
