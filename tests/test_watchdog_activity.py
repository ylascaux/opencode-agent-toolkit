import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WatchdogActivityTests(unittest.TestCase):
    def test_active_wrappers_disable_heuristic_auto_kills(self):
        for relative in [
            Path(".opencode/plugins/reliability-v1.js"),
            Path(".opencode/plugins/reliability-v2.ts"),
        ]:
            text = (ROOT / relative).read_text()
            for needle in [
                'MAX_CHILD_COST: "0"',
                'MAX_RUN_COST: "0"',
                'SUBAGENT_STALLED_TIMEOUT_SECONDS: "2147483647"',
                'SUBAGENT_MAX_DURATION_SECONDS: "2147483647"',
                'MAX_SAME_ERROR: "2147483647"',
            ]:
                self.assertIn(needle, text, f"{relative}: {needle}")

    def test_v2_approval_plugin_requires_explicit_user_decision(self):
        server = (ROOT / "plugins" / "reliability-approval" / "index.ts").read_text()
        tui = (ROOT / "plugins" / "reliability-approval" / "tui.ts").read_text()
        rpc = (ROOT / "plugins" / "reliability-approval" / "rpc.ts").read_text()

        self.assertIn('events.emit("suspected"', server)
        self.assertIn('if (!pending.has(sessionID)) return { status: "stale" }', server)
        self.assertIn('ctx.session.interrupt({ sessionID, continue: false })', server)
        self.assertIn('context.ui.dialog.confirm', tui)
        self.assertIn('confirm: "Kill"', tui)
        self.assertIn('cancel: "Keep running"', tui)
        self.assertIn('enum: ["kill", "keep"]', rpc)

    def test_heartbeat_control_is_exposed_without_cost_kill_controls(self):
        env = (ROOT / ".env.example").read_text()
        self.assertIn("SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS=", env)
        self.assertNotIn("MAX_CHILD_COST=", env)
        self.assertNotIn("MAX_RUN_COST=", env)


if __name__ == "__main__":
    unittest.main()
