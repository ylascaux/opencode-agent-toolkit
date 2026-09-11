import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
RUNTIME = ROOT / "runtime" / "plugins"
GENERATED_PROMPTS = ROOT / ".generated" / "prompts"
LEADS = ["meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead"]
READ_ONLY_GIT = ["git status*", "git diff*", "git log*", "git show*", "git rev-parse*"]


def source_agents() -> list[str]:
    return sorted(path.name for path in AGENTS_DIR.iterdir() if path.is_dir() and not path.name.startswith("_"))


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
        self.assertNotIn("max_child_cost", normal)
        self.assertNotIn("max_run_cost", normal)
        self.assertLessEqual(policy["step_caps"]["orchestrator"], 16)
        self.assertLessEqual(policy["step_caps"]["builder"], 16)

    def test_policy_exposes_per_lead_parallel_overrides(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(set(policy["lead_parallel_env"]), set(LEADS))
        self.assertEqual(policy["lead_parallel_env"]["orchestrator"], "MAX_PARALLEL_ORCHESTRATOR")

    def test_every_agent_has_editable_local_files(self):
        names = source_agents()
        self.assertEqual(len(names), 40)
        for name in names:
            directory = AGENTS_DIR / name
            for filename in ["agent.json", "prompt.md", "permissions.json"]:
                self.assertTrue((directory / filename).exists(), f"{name}: {filename}")

    def test_default_permission_policy_is_open_but_destructive_safe(self):
        default = json.loads((AGENTS_DIR / "_defaults" / "permissions.json").read_text())
        self.assertEqual(default["websearch"], "allow")
        self.assertEqual(default["webfetch"], "allow")
        self.assertEqual(default["edit"], "ask")
        self.assertEqual(default["bash"]["*"], "ask")
        self.assertEqual(default["read"]["*.env"], "ask")
        self.assertEqual(default["read"]["**/.ssh/**"], "deny")
        self.assertEqual(default["read"]["**/.aws/**"], "deny")
        self.assertEqual(default["external_directory"]["*"], "deny")
        for command in ["rm -rf*", "git reset --hard*", "git push --force*", "terraform apply*", "kubectl delete*"]:
            self.assertEqual(default["bash"][command], "deny", command)

    def test_generated_configs_load_isolated_runtime_plugins(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertLessEqual(v1["agent"]["orchestrator"]["steps"], 16)
        self.assertLessEqual(v2["agents"]["orchestrator"]["steps"], 16)
        self.assertIn("./runtime/plugins/reliability-v1.js", v1["plugin"])
        self.assertIn("./runtime/plugins/reliability-v2.ts", v2["plugins"])
        self.assertNotIn("./plugins/reliability-approval", v2["plugins"])
        self.assertFalse((ROOT / ".opencode" / "plugins").exists())

    def test_every_agent_can_websearch_webfetch_and_use_read_only_git_v1(self):
        config = json.loads((ROOT / "opencode.jsonc").read_text())
        for name, agent in config["agent"].items():
            permission = agent["permission"]
            self.assertEqual(permission["websearch"], "allow", name)
            self.assertEqual(permission["webfetch"], "allow", name)
            self.assertEqual(permission["bash"]["*"], "ask", name)
            for pattern in READ_ONLY_GIT:
                self.assertEqual(permission["bash"].get(pattern), "allow", f"{name}: {pattern}")

    def test_every_agent_can_websearch_webfetch_and_use_read_only_git_v2(self):
        config = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        for name, agent in config["agents"].items():
            rules = agent["permissions"]
            for action in ["websearch", "webfetch"]:
                matched = [r for r in rules if r.get("action") == action and r.get("resource") == "*"]
                self.assertTrue(matched, f"{name}: {action}")
                self.assertEqual(matched[-1]["effect"], "allow", f"{name}: {action}")
            shell_default = [r for r in rules if r.get("action") == "shell" and r.get("resource") == "*"]
            self.assertEqual(shell_default[-1]["effect"], "ask", name)

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

        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, check=True)

    def test_lead_prompts_include_supervision_contract(self):
        for name in LEADS:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text().lower()
            for needle in [
                "## reliability and child supervision", "runtime slot", "waiting_permission is not stalled",
                "waiting_on_child", "stall_suspected", "approval-based watchdog killing is temporarily disabled",
                "retry only that failed child", "task_id", "checkpoint",
            ]:
                self.assertIn(needle, text, f"{name}: {needle}")

    def test_all_prompts_include_external_research_contract(self):
        config = json.loads((ROOT / "opencode.jsonc").read_text())
        for name in config["agent"]:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text().lower()
            for needle in ["## external research", "websearch", "webfetch", "primary sources"]:
                self.assertIn(needle, text, f"{name}: {needle}")

    def test_legacy_v1_watchdog_keeps_runtime_guards_for_compatibility(self):
        text = (RUNTIME / "reliability-v1-legacy.js").read_text()
        for needle in [
            "client.session.children", "client.session.abort", "reservations", "consumeOldestReservation",
            "lead_parallel_env", "MAX_SUBAGENT_RETRIES", "RELIABILITY_STATE_DIR", "writeCheckpoint",
            "same tool call produced the same result", "WAITING_PERMISSION", "retryable_failed", "task_id",
            "usedSlots(state.id) > 0", "createCallIdTracker", "createProgressAwareRepeatDetector",
        ]:
            self.assertIn(needle, text)

    def test_legacy_v2_watchdog_keeps_retry_and_task_identity_logic(self):
        text = (RUNTIME / "reliability-v2-legacy.ts").read_text()
        for needle in [
            "session.interrupt", "reconcileChildren", "reservations", "consumeOldestReservation",
            "lead_parallel_env", "MAX_SUBAGENT_RETRIES", "RELIABILITY_STATE_DIR", "writeCheckpoint",
            "same tool call produced the same result", "MAX_PROVIDER_RETRIES", "retryable_failed", "task_id",
            "usedSlots(state.id) > 0", "createCallIdTracker", "createProgressAwareRepeatDetector", "providerRetryDecision",
        ]:
            self.assertIn(needle, text)

    def test_active_wrappers_disable_heuristic_auto_kills(self):
        for filename in ["reliability-v1.js", "reliability-v2.ts"]:
            text = (RUNTIME / filename).read_text()
            for needle in [
                'MAX_CHILD_COST: "0"', 'MAX_RUN_COST: "0"',
                'SUBAGENT_STALLED_TIMEOUT_SECONDS: "2147483647"',
                'SUBAGENT_MAX_DURATION_SECONDS: "2147483647"', 'MAX_SAME_ERROR: "2147483647"',
            ]:
                self.assertIn(needle, text, f"{filename}: {needle}")

    def test_v2_approval_plugin_is_user_gated_and_fail_open(self):
        server = (ROOT / "plugins" / "reliability-approval" / "index.ts").read_text()
        tui = (ROOT / "plugins" / "reliability-approval" / "tui.ts").read_text()
        rpc = (ROOT / "plugins" / "reliability-approval" / "rpc.ts").read_text()
        for needle in ['events.emit("suspected"', 'if (!pending.has(sessionID)) return { status: "stale" }', 'ctx.session.interrupt({ sessionID, continue: false })', "no destructive fallback"]:
            self.assertIn(needle, server)
        self.assertIn("context.ui.dialog.confirm", tui)
        self.assertIn('confirm: "Kill"', tui)
        self.assertIn('cancel: "Keep running"', tui)
        self.assertIn('enum: ["kill", "keep"]', rpc)

    def test_shared_runtime_core_contains_terminal_and_delegation_retry_policy(self):
        text = (RUNTIME / "reliability-core.js").read_text()
        for needle in ["[400, 401, 403, 404]", "createCallIdTracker", "createProgressAwareRepeatDetector", "delegationFailureClass", "delegationTaskKey", "task cancel"]:
            self.assertIn(needle, text)

    def test_env_exposes_reliability_controls_without_cost_kill_budgets(self):
        text = (ROOT / ".env.example").read_text()
        for key in [
            "RELIABILITY_PROFILE=", "OPENCODE_PREFLIGHT_AUTH=", "OPENCODE_PREFLIGHT_MODELS=",
            "MAX_PARALLEL_SUBAGENTS=", "MAX_SUBAGENT_RETRIES=", "SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS=",
        ]:
            self.assertIn(key, text)
        self.assertNotIn("MAX_CHILD_COST=", text)
        self.assertNotIn("MAX_RUN_COST=", text)
        self.assertIn("MAX_PARALLEL_ORCHESTRATOR", text)
        self.assertIn("RELIABILITY_STATE_DIR", text)

    def test_preflight_is_macos_bash_compatible(self):
        text = (ROOT / "scripts" / "preflight").read_text()
        self.assertNotIn("mapfile", text)
        self.assertIn("configured_models=()", text)
        self.assertIn("OPENCODE_PREFLIGHT_AUTH", text)
        self.assertIn("OPENCODE_PREFLIGHT_MODELS", text)
        self.assertNotIn("MAX_CHILD_COST", text)
        self.assertNotIn("MAX_RUN_COST", text)


if __name__ == "__main__":
    unittest.main()
