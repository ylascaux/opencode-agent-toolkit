import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
GENERATED_PROMPTS = ROOT / ".generated" / "prompts"
LEADS = ["meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead"]
READ_ONLY_GIT = ["git status*", "git diff*", "git log*", "git show*", "git rev-parse*"]


def source_agents() -> list[str]:
    return sorted(
        path.name
        for path in AGENTS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    )


class ReliabilityPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env.setdefault("RELIABILITY_PROFILE", "normal")
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=env, check=True)

    def test_policy_has_profiles_and_conservative_normal_defaults(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(policy["default_profile"], "normal")
        self.assertEqual(set(policy["profiles"]), {"cheap", "normal", "premium"})
        normal = policy["profiles"]["normal"]
        self.assertEqual(normal["max_parallel_subagents"], 3)
        self.assertEqual(normal["queue_timeout_seconds"], 600)
        self.assertEqual(normal["max_same_error"], 2)
        self.assertEqual(normal["max_subagent_retries"], 2)
        self.assertGreater(normal["heartbeat_timeout_seconds"], 0)
        self.assertGreater(normal["max_child_cost"], 0)
        self.assertGreater(normal["max_run_cost"], normal["max_child_cost"])
        self.assertLessEqual(policy["step_caps"]["orchestrator"], 16)
        self.assertLessEqual(policy["step_caps"]["builder"], 16)

    def test_policy_exposes_per_lead_parallel_overrides(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(set(policy["lead_parallel_env"]), set(LEADS))
        self.assertEqual(policy["lead_parallel_env"]["orchestrator"], "MAX_PARALLEL_ORCHESTRATOR")

    def test_every_agent_has_editable_local_files(self):
        names = source_agents()
        self.assertEqual(len(names), 37)
        for name in names:
            directory = AGENTS_DIR / name
            self.assertTrue((directory / "agent.json").exists(), name)
            self.assertTrue((directory / "prompt.md").exists(), name)
            self.assertTrue((directory / "permissions.json").exists(), name)
            self.assertIsInstance(json.loads((directory / "agent.json").read_text()), dict, name)
            self.assertIsInstance(json.loads((directory / "permissions.json").read_text()), dict, name)

    def test_default_permission_policy_is_open_but_destructive_safe(self):
        default = json.loads((AGENTS_DIR / "_defaults" / "permissions.json").read_text())
        self.assertEqual(default["websearch"], "allow")
        self.assertEqual(default["webfetch"], "allow")
        self.assertEqual(default["edit"], "ask")
        self.assertEqual(default["bash"]["*"], "ask")
        self.assertEqual(default["read"]["*.env"], "ask")
        self.assertEqual(default["external_directory"]["*"], "ask")
        for command in ["rm -rf*", "git reset --hard*", "git push --force*", "terraform apply*", "kubectl delete*"]:
            self.assertEqual(default["bash"][command], "deny", command)

    def test_v1_config_is_step_capped_and_loads_watchdog(self):
        config = json.loads((ROOT / "opencode.jsonc").read_text())
        self.assertLessEqual(config["agent"]["orchestrator"]["steps"], 16)
        self.assertLessEqual(config["agent"]["builder"]["steps"], 16)
        self.assertIn("./.opencode/plugins/reliability-v1.js", config["plugin"])

    def test_v2_config_is_step_capped_and_loads_watchdog(self):
        config = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertLessEqual(config["agents"]["orchestrator"]["steps"], 16)
        self.assertLessEqual(config["agents"]["builder"]["steps"], 16)
        self.assertIn("./.opencode/plugins/reliability-v2.ts", config["plugins"])

    def test_every_agent_can_websearch_webfetch_and_use_read_only_git_v1(self):
        config = json.loads((ROOT / "opencode.jsonc").read_text())
        for name, agent in config["agent"].items():
            permission = agent["permission"]
            self.assertEqual(permission["websearch"], "allow", name)
            self.assertEqual(permission["webfetch"], "allow", name)
            bash = permission["bash"]
            self.assertIsInstance(bash, dict, name)
            self.assertEqual(bash["*"], "ask", name)
            for pattern in READ_ONLY_GIT:
                self.assertEqual(bash.get(pattern), "allow", f"{name}: {pattern}")

    def test_every_agent_can_websearch_webfetch_and_use_read_only_git_v2(self):
        config = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        for name, agent in config["agents"].items():
            rules = agent["permissions"]
            for action in ["websearch", "webfetch"]:
                web = [r for r in rules if r.get("action") == action and r.get("resource") == "*"]
                self.assertTrue(web, f"{name}: {action}")
                self.assertEqual(web[-1]["effect"], "allow", f"{name}: {action}")
            shell_default = [r for r in rules if r.get("action") == "shell" and r.get("resource") == "*"]
            self.assertTrue(shell_default, name)
            self.assertEqual(shell_default[-1]["effect"], "ask", name)
            for pattern in READ_ONLY_GIT:
                git_rules = [
                    r for r in rules
                    if r.get("action") == "shell" and r.get("resource") == pattern
                ]
                self.assertTrue(git_rules, f"{name}: {pattern}")
                self.assertEqual(git_rules[-1]["effect"], "allow", f"{name}: {pattern}")

    def test_step_override_can_lower_but_never_raise_generator_boundary(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        builder_cap = policy["step_caps"]["builder"]

        low_env = os.environ.copy()
        low_env["MAX_STEPS_BUILDER"] = "7"
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=low_env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=low_env, check=True)
        lowered = json.loads((ROOT / "opencode.jsonc").read_text())
        self.assertEqual(lowered["agent"]["builder"]["steps"], 7)

        high_env = os.environ.copy()
        high_env["MAX_STEPS_BUILDER"] = "999"
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=high_env, check=True)
        raw = json.loads((ROOT / "opencode.jsonc").read_text())
        raw_steps = raw["agent"]["builder"]["steps"]
        self.assertGreater(raw_steps, builder_cap)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=high_env, check=True)
        bounded = json.loads((ROOT / "opencode.jsonc").read_text())
        self.assertEqual(bounded["agent"]["builder"]["steps"], builder_cap)
        self.assertLess(bounded["agent"]["builder"]["steps"], raw_steps)

        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, check=True)

    def test_lead_prompts_include_supervision_contract(self):
        for name in LEADS:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text().lower()
            self.assertIn("## reliability and child supervision", text, name)
            self.assertIn("runtime slot", text, name)
            self.assertIn("waiting_permission is not stalled", text, name)
            self.assertIn("waiting_on_child", text, name)
            self.assertIn("retry only that failed child", text, name)
            self.assertIn("task_id", text, name)
            self.assertIn("checkpoint", text, name)

    def test_all_prompts_include_external_research_contract(self):
        config = json.loads((ROOT / "opencode.jsonc").read_text())
        for name in config["agent"]:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text().lower()
            self.assertIn("## external research", text, name)
            self.assertIn("websearch", text, name)
            self.assertIn("webfetch", text, name)
            self.assertIn("primary sources", text, name)

    def test_v1_watchdog_has_advanced_runtime_guards(self):
        text = (ROOT / ".opencode" / "plugins" / "reliability-v1.js").read_text()
        for needle in [
            "client.session.children", "client.session.abort", "reservations",
            "consumeOldestReservation", "lead_parallel_env", "MAX_CHILD_COST",
            "MAX_RUN_COST", "MAX_SUBAGENT_RETRIES", "RELIABILITY_STATE_DIR",
            "writeCheckpoint", "same tool call produced the same result",
            "WAITING_PERMISSION", "retryable_failed", "task_id",
            "usedSlots(state.id) > 0", "createCallIdTracker",
            "createProgressAwareRepeatDetector",
        ]:
            self.assertIn(needle, text)

    def test_v2_watchdog_keeps_parity_and_retry_policy(self):
        text = (ROOT / ".opencode" / "plugins" / "reliability-v2.ts").read_text()
        for needle in [
            "session.interrupt", "reconcileChildren", "reservations",
            "consumeOldestReservation", "lead_parallel_env", "MAX_CHILD_COST",
            "MAX_RUN_COST", "MAX_SUBAGENT_RETRIES", "RELIABILITY_STATE_DIR",
            "writeCheckpoint", "same tool call produced the same result",
            "MAX_PROVIDER_RETRIES", "retryable_failed", "task_id",
            "usedSlots(state.id) > 0", "createCallIdTracker",
            "createProgressAwareRepeatDetector", "providerRetryDecision",
        ]:
            self.assertIn(needle, text)

    def test_shared_runtime_core_contains_terminal_and_delegation_retry_policy(self):
        text = (ROOT / ".opencode" / "plugins" / "reliability-core.js").read_text()
        self.assertIn("[400, 401, 403, 404]", text)
        self.assertIn("createCallIdTracker", text)
        self.assertIn("createProgressAwareRepeatDetector", text)
        self.assertIn("delegationFailureClass", text)
        self.assertIn("delegationTaskKey", text)
        self.assertIn("task cancel", text)

    def test_env_exposes_new_reliability_controls(self):
        text = (ROOT / ".env.example").read_text()
        for key in [
            "RELIABILITY_PROFILE=", "OPENCODE_PREFLIGHT_AUTH=",
            "OPENCODE_PREFLIGHT_MODELS=", "MAX_PARALLEL_SUBAGENTS=",
            "MAX_SUBAGENT_RETRIES=", "MAX_CHILD_COST=", "MAX_RUN_COST=",
        ]:
            self.assertIn(key, text)
        self.assertIn("MAX_PARALLEL_ORCHESTRATOR", text)
        self.assertIn("RELIABILITY_STATE_DIR", text)

    def test_preflight_is_macos_bash_compatible(self):
        text = (ROOT / "scripts" / "preflight").read_text()
        self.assertNotIn("mapfile", text)
        self.assertIn("configured_models=()", text)
        self.assertIn("OPENCODE_PREFLIGHT_AUTH", text)
        self.assertIn("OPENCODE_PREFLIGHT_MODELS", text)


if __name__ == "__main__":
    unittest.main()
