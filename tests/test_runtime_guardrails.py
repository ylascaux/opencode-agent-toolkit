import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEADS = {"meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead"}


class RuntimeGuardrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True, capture_output=True, text=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-runtime-policy")], check=True, capture_output=True, text=True)
        cls.v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        cls.v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())

    def test_default_steps_are_bounded(self):
        for name, agent in self.v1["agent"].items():
            self.assertGreaterEqual(agent["steps"], 1, name)
            self.assertLessEqual(agent["steps"], 16, name)
        for name, agent in self.v2["agents"].items():
            self.assertEqual(agent["steps"], self.v1["agent"][name]["steps"], name)

    def test_step_override_is_configurable(self):
        env = os.environ.copy()
        env["OC_STEPS_BUILDER"] = "7"
        try:
            subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True, env=env, capture_output=True, text=True)
            subprocess.run(["python3", str(ROOT / "scripts" / "apply-runtime-policy")], check=True, env=env, capture_output=True, text=True)
            data = json.loads((ROOT / "opencode.jsonc").read_text())
            self.assertEqual(data["agent"]["builder"]["steps"], 7)
        finally:
            subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True, capture_output=True, text=True)
            subprocess.run(["python3", str(ROOT / "scripts" / "apply-runtime-policy")], check=True, capture_output=True, text=True)

    def test_all_leads_receive_delegated_work_supervision(self):
        for lead in LEADS:
            text = (ROOT / "prompts" / f"{lead}.md").read_text().lower()
            self.assertIn("## delegated-work supervision", text, lead)
            self.assertIn("obey the configured subagent concurrency limit", text, lead)
            self.assertIn("waiting_permission is not a stall", text, lead)
            self.assertIn("never restart the entire workflow", text, lead)

    def test_watchdog_has_deterministic_parallel_gate_and_abort(self):
        text = (ROOT / "plugins" / "runtime-guardrails.js").read_text()
        self.assertIn("acquireSubagentSlot", text)
        self.assertIn("OC_MAX_PARALLEL_SUBAGENTS", text)
        self.assertIn("OC_MAX_PARALLEL_ORCHESTRATOR", text)
        self.assertIn('input.tool === "task" || input.tool === "subagent"', text)
        self.assertIn("client.session.abort", text)
        self.assertIn("permission.asked", text)
        self.assertIn("permission.replied", text)
        self.assertIn("maxChildCost", text)
        self.assertIn("maxRunCost", text)
        self.assertIn("lastProgressAt", text)
        self.assertIn("writeCheckpoint", text)

    def test_env_exposes_reliability_controls(self):
        text = (ROOT / ".env.example").read_text()
        for key in [
            "OC_RUNTIME_PROFILE",
            "OC_RUNTIME_GUARDS",
            "OC_PREFLIGHT",
            "OC_MAX_PARALLEL_SUBAGENTS",
            "OC_STALLED_TIMEOUT_SECONDS",
            "OC_MAX_AGENT_DURATION_SECONDS",
            "OC_MAX_SAME_FAILURE",
            "OC_MAX_CHILD_COST",
            "OC_MAX_RUN_COST",
        ]:
            self.assertIn(f"{key}=", text, key)

    def test_launcher_runs_preflight_before_exec(self):
        text = (ROOT / "scripts" / "opencode-agents").read_text()
        self.assertLess(text.index("scripts/preflight"), text.index('exec "$bin"'))
        self.assertLess(text.index("scripts/apply-runtime-policy"), text.index("scripts/preflight"))
        self.assertIn("OPENCODE_TOOLKIT_RUNTIME_GUARDS", text)

    def test_user_install_manages_watchdog_symlink(self):
        text = (ROOT / "scripts" / "user-link").read_text()
        self.assertIn("opencode-agent-toolkit-runtime.js", text)
        self.assertIn("plugins/runtime-guardrails.js", text)
        self.assertIn("global but inert", text)


if __name__ == "__main__":
    unittest.main()
