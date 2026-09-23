import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED_PROMPTS = ROOT / ".generated" / "prompts"
CORE = [
    "meta-router",
    "orchestrator",
    "builder",
    "debugger",
    "tester",
    "reviewer",
    "platform-architect",
    "security-lead",
    "research-runner",
]


class PlanApprovalTests(unittest.TestCase):
    """Optional plan-gate compatibility without forcing approval in normal use."""

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env.setdefault("RELIABILITY_PROFILE", "normal")
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=env, check=True)

    def test_policy_defaults_to_off(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(policy["plan_approval"]["default_mode"], "off")

    def test_only_v2_loads_the_optional_plan_gate(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertNotIn("./runtime/plugins/plan-approval-v2", v1["plugin"])
        self.assertIn("./runtime/plugins/plan-approval-v2", v2["plugins"])
        self.assertTrue((ROOT / "runtime" / "plugins" / "plan-approval-v2").is_dir())

    def test_default_commands_do_not_create_an_artificial_approval_round_trip(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertIn("plan", v1["command"])
        self.assertIn("plan", v2["commands"])
        for command in list(v1["command"].values()) + list(v2["commands"].values()):
            self.assertNotIn("PLAN_APPROVAL_REQUIRED", command["template"])
            self.assertNotIn("PLAN_REAPPROVAL_REQUIRED", command["template"])

    def test_v1_prompts_disable_plan_approval(self):
        v1_prompts = ROOT / ".generated" / "prompts-v1"
        for name in CORE:
            text = (v1_prompts / f"{name}.md").read_text()
            self.assertIn("Effective `PLAN_APPROVAL_MODE`: `off`", text, name)
            self.assertIn("Do not pause solely for PLAN_APPROVAL_REQUIRED", text, name)

    def test_generated_prompts_keep_optional_global_plan_contract(self):
        for name in CORE:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text()
            self.assertIn("## Plan approval contract", text, name)
            self.assertIn("PLAN_APPROVAL_REQUIRED", text, name)
            self.assertIn("PLAN_REAPPROVAL_REQUIRED", text, name)
            self.assertIn("Effective `PLAN_APPROVAL_MODE`: `off`", text, name)

    def test_router_and_orchestrator_explicitly_avoid_extra_approval_when_off(self):
        orchestrator = (GENERATED_PROMPTS / "orchestrator.md").read_text().lower()
        router = (GENERATED_PROMPTS / "meta-router.md").read_text().lower()
        self.assertIn("do not create an artificial approval round-trip", orchestrator)
        self.assertIn("effective runtime approval mode", router)
        self.assertNotIn("planner.md", orchestrator)
        self.assertNotIn("planner.md", router)

    def test_runtime_gate_remains_available_when_explicitly_enabled(self):
        core = (ROOT / "runtime" / "plugins" / "plan-approval-core.js").read_text()
        v2 = (ROOT / "runtime" / "plugins" / "plan-approval-v2.ts").read_text()
        self.assertIn("toolRequiresPlanApproval", core)
        self.assertIn("runtime-blocked-unapproved-change", core)
        self.assertIn('ctx.tool.hook("execute.before"', v2)
        self.assertIn("throw new Error(blockedMessage(decision))", v2)

    def test_native_launcher_disables_old_gate_without_rewriting_user_profiles(self):
        bootstrap = (ROOT / "scripts" / "bootstrap").read_text()
        launcher = (ROOT / "scripts" / "opencode-agents").read_text()
        self.assertIn("PLAN_APPROVAL_MODE=off", launcher)
        self.assertNotIn("scripts/apply-reliability", launcher)
        self.assertNotIn("PLAN_APPROVAL_MODE=changes", bootstrap)
        self.assertIn('if [[ ! -f "$ROOT/.env" ]]', bootstrap)


if __name__ == "__main__":
    unittest.main()
