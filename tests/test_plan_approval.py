import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED_PROMPTS = ROOT / ".generated" / "prompts"


class PlanApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env.setdefault("RELIABILITY_PROFILE", "normal")
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=env, check=True)

    def test_policy_defaults_to_changes_mode(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(policy["plan_approval"]["default_mode"], "changes")

    def test_only_v2_loads_the_plan_gate(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertNotIn("./runtime/plugins/plan-approval-v1.js", v1["plugin"])
        self.assertIn("./runtime/plugins/plan-approval-v2.ts", v2["plugins"])

    def test_plan_approval_markers_are_v2_only(self):
        v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())
        self.assertIn("plan", v1["command"])
        for command in v1["command"].values():
            self.assertNotIn("PLAN_APPROVAL_REQUIRED", command["template"])
            self.assertNotIn("PLAN_REAPPROVAL_REQUIRED", command["template"])
        self.assertIn("PLAN_APPROVAL_REQUIRED", v2["commands"]["plan"]["template"])
        self.assertIn("PLAN_APPROVAL_REQUIRED", v2["commands"]["ship"]["template"])
        self.assertIn("PLAN_REAPPROVAL_REQUIRED", v2["commands"]["ship"]["template"])

    def test_v1_prompts_disable_plan_approval(self):
        v1_prompts = ROOT / ".generated" / "prompts-v1"
        for name in ["meta-router", "orchestrator", "planner", "builder", "tester"]:
            text = (v1_prompts / f"{name}.md").read_text()
            self.assertIn("Effective `PLAN_APPROVAL_MODE`: `off`", text, name)
            self.assertIn("Do not pause solely for PLAN_APPROVAL_REQUIRED", text, name)

    def test_generated_prompts_include_global_plan_contract(self):
        for name in ["meta-router", "orchestrator", "planner", "builder", "tester"]:
            text = (GENERATED_PROMPTS / f"{name}.md").read_text()
            self.assertIn("## Plan approval contract", text, name)
            self.assertIn("PLAN_APPROVAL_REQUIRED", text, name)
            self.assertIn("PLAN_REAPPROVAL_REQUIRED", text, name)

    def test_leads_expose_plan_boundary_specific_behavior(self):
        orchestrator = (GENERATED_PROMPTS / "orchestrator.md").read_text()
        router = (GENERATED_PROMPTS / "meta-router.md").read_text()
        planner = (GENERATED_PROMPTS / "planner.md").read_text()
        self.assertIn("## Plan-first delivery", orchestrator)
        self.assertIn("user approval", orchestrator.lower())
        self.assertIn("## Plan approval routing", router)
        self.assertIn("root user", router.lower())
        self.assertIn("AFFECTED FILES / COMPONENTS", planner)
        self.assertIn("ROLLBACK", planner)

    def test_environment_documents_all_plan_modes(self):
        text = (ROOT / ".env.example").read_text()
        self.assertIn("PLAN_APPROVAL_MODE=changes", text)
        self.assertIn("off", text)
        self.assertIn("always", text)

    def test_runtime_gate_is_fail_closed_for_mutation(self):
        core = (ROOT / "runtime" / "plugins" / "plan-approval-core.js").read_text()
        v1 = (ROOT / "runtime" / "plugins" / "plan-approval-v1.js").read_text()
        v2 = (ROOT / "runtime" / "plugins" / "plan-approval-v2.ts").read_text()
        self.assertIn("toolRequiresPlanApproval", core)
        self.assertIn("runtime-blocked-unapproved-change", core)
        self.assertIn('"tool.execute.before"', v1)
        self.assertIn('ctx.tool.hook("execute.before"', v2)
        self.assertIn("throw new Error(blockedMessage(decision))", v1)
        self.assertIn("throw new Error(blockedMessage(decision))", v2)


if __name__ == "__main__":
    unittest.main()
