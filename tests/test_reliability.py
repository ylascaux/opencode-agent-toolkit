import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
RUNTIME = ROOT / "runtime" / "plugins"
GENERATED_PROMPTS = ROOT / ".generated" / "prompts"

CORE = {
    "meta-router", "orchestrator", "builder", "debugger", "tester",
    "reviewer", "platform-architect", "security-lead", "research-runner",
}
SUPERVISING_AGENTS = {"meta-router", "orchestrator", "platform-architect"}
READ_ONLY_GIT = ["git status*", "git diff*", "git log*", "git show*", "git rev-parse*"]


def source_agents() -> list[str]:
    return list(json.loads((AGENTS_DIR / "catalog.json").read_text())["agents"])


class ReliabilityPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env.setdefault("RELIABILITY_PROFILE", "normal")
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=env, check=True)

    def test_policy_has_profiles_and_small_lead_overrides(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(policy["default_profile"], "normal")
        self.assertEqual(set(policy["profiles"]), {"cheap", "normal", "premium"})
        self.assertEqual(
            policy["lead_parallel_env"],
            {
                "meta-router": "MAX_PARALLEL_META_ROUTER",
                "orchestrator": "MAX_PARALLEL_ORCHESTRATOR",
            },
        )
        self.assertEqual(set(policy["step_caps"]) - {"default"}, CORE)

    def test_active_agent_files_are_complete(self):
        names = source_agents()
        self.assertEqual(set(names), CORE)
        self.assertEqual(len(names), 9)
        for name in names:
            directory = AGENTS_DIR / name
            for filename in ["agent.json", "prompt.md", "permissions.json"]:
                self.assertTrue((directory / filename).exists(), f"{name}: {filename}")

    def test_default_permission_policy_keeps_destructive_operations_safe(self):
        default = json.loads((AGENTS_DIR / "_defaults" / "permissions.json").read_text())
        self.assertEqual(default["websearch"], "allow")
        self.assertEqual(default["webfetch"], "allow")
        self.assertEqual(default["bash"]["*"], "ask")
        self.assertEqual(default["read"]["*.env"], "ask")
        self.assertEqual(default["read"]["**/.ssh/**"], "deny")
        for command in ["rm -rf*", "git reset --hard*", "git push --force*", "terraform apply*", "kubectl delete*"]:
            self.assertEqual(default["bash"][command], "deny", command)

    def test_generated_configs_contain_only_core_agents(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertEqual(set(v1["agent"]), CORE)
        self.assertEqual(set(v2["agents"]), CORE)
        self.assertIn("./runtime/plugins/reliability-v1.js", v1["plugin"])
        self.assertIn("./runtime/plugins/reliability-v2", v2["plugins"])

    def test_research_runner_is_read_only_and_non_shell(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        p = v1["agent"]["research-runner"]["permission"]
        self.assertEqual(p["edit"], "deny")
        self.assertEqual(p["bash"], "deny")
        self.assertEqual(p["skill"], "ask")
        self.assertIsInstance(p["read"], dict)
        self.assertEqual(p["read"]["**/.ssh/**"], "deny")

    def test_other_agents_keep_expected_read_only_git_baseline(self):
        config = json.loads((ROOT / "opencode.jsonc").read_text())
        for name, agent in config["agent"].items():
            if name == "research-runner":
                continue
            bash = agent["permission"]["bash"]
            self.assertEqual(bash["*"], "ask", name)
            for pattern in READ_ONLY_GIT:
                self.assertEqual(bash.get(pattern), "allow", f"{name}: {pattern}")

    def test_supervising_prompts_get_reliability_contract(self):
        for name in SUPERVISING_AGENTS:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text().lower()
            self.assertIn("## reliability and child supervision", text, name)
            self.assertIn("waiting_on_child", text, name)
            self.assertIn("retry only that failed child", text, name)

        for name in CORE - SUPERVISING_AGENTS:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text().lower()
            self.assertNotIn("## reliability and child supervision", text, name)

    def test_step_override_can_lower_but_never_raise_generator_boundary(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        builder_cap = policy["step_caps"]["builder"]

        low_env = os.environ.copy()
        low_env["MAX_STEPS_BUILDER"] = "7"
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=low_env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=low_env, check=True)
        self.assertEqual(json.loads((ROOT / "opencode.jsonc").read_text())["agent"]["builder"]["steps"], 7)

        high_env = os.environ.copy()
        high_env["MAX_STEPS_BUILDER"] = "999"
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=high_env, check=True)
        raw = json.loads((ROOT / "opencode.jsonc").read_text())["agent"]["builder"]["steps"]
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=high_env, check=True)
        bounded = json.loads((ROOT / "opencode.jsonc").read_text())["agent"]["builder"]["steps"]
        self.assertGreater(raw, builder_cap)
        self.assertEqual(bounded, builder_cap)

    def test_active_wrappers_disable_heuristic_auto_kills(self):
        v1 = (RUNTIME / "reliability-v1.js").read_text()
        v2 = (RUNTIME / "reliability-v2.ts").read_text()
        self.assertNotIn("session.abort", v1)
        self.assertNotIn("session.abort", v2)


if __name__ == "__main__":
    unittest.main()
