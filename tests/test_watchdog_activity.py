import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WatchdogActivityTests(unittest.TestCase):
    def test_v1_and_v2_use_activity_aware_stall_detection(self):
        for relative in [
            Path(".opencode/plugins/reliability-v1.js"),
            Path(".opencode/plugins/reliability-v2.ts"),
        ]:
            text = (ROOT / relative).read_text()
            for needle in [
                "SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS",
                "createStallDetector",
                "hasInFlightTool",
                "confirmationMs: watchMs",
                "preserveRetryableDelegation",
                'delegation.status = "retryable_failed"',
            ]:
                self.assertIn(needle, text, f"{relative}: {needle}")

    def test_heartbeat_control_is_exposed_to_users(self):
        env = (ROOT / ".env.example").read_text()
        self.assertIn("SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS=", env)


if __name__ == "__main__":
    unittest.main()
