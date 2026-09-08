import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReliabilityPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env.setdefault("MAX_PARALLEL_SUBAGENTS", "3")
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], cwd=ROOT, env=env, check=True)
        subprocess.run(["python3", str(ROOT / "scripts" / "apply-reliability")], cwd=ROOT, env=env, check=True)

    def test_policy_has_conservative_parallel_default(self):
        policy = json.loads((ROOT / "reliability.json").read_text())
        self.assertEqual(policy["max_parallel_subagents"], 3)
        self.assertLessEqual(policy["step_caps"]["orchestrator"], 16)
        self.assertLessEqual(policy["step_caps"]["builder"], 16)

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

    def test_lead_prompts_include_supervision_contract(self):
        for name in ["meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead"]:
            text = (ROOT / "prompts" / f"{name}.md").read_text().lower()
            self.assertIn("## reliability and child supervision", text, name)
            self.assertIn("never have more than 3 delegated child agents", text, name)
            self.assertIn("waiting_permission is not stalled", text, name)

    def test_v2_watchdog_has_terminal_retry_policy(self):
        text = (ROOT / ".opencode" / "plugins" / "reliability-v2.ts").read_text()
        self.assertIn("[400, 401, 403, 404]", text)
        self.assertIn("MAX_PROVIDER_RETRIES", text)
        self.assertIn("MAX_PARALLEL_SUBAGENTS", text)

    def test_v1_watchdog_can_abort_children(self):
        text = (ROOT / ".opencode" / "plugins" / "reliability-v1.js").read_text()
        self.assertIn("client.session.abort", text)
        self.assertIn("MAX_PARALLEL_SUBAGENTS", text)
        self.assertIn("WAITING_PERMISSION", text)


if __name__ == "__main__":
    unittest.main()
