from __future__ import annotations

import json
import os
import runpy
import sys
import time
import tempfile
import textwrap
import unittest
from pathlib import Path

from runtime.common.acp import AcpRunner
from runtime.common.acp_session import AcpSession


FAKE_AGENT = r'''
import json
import os
import sys

session_id = f"sess_{os.getpid()}"

def send(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    rid = request.get("id")
    if method == "initialize":
        inline = os.environ.get("OPENCODE_CONFIG_CONTENT", "")
        if "oat-acp" in inline or "oat-memory" in inline or os.environ.get("OAT_MEMORY_POSTGRES_DSN"):
            send({"jsonrpc":"2.0","id":rid,"error":{"code":-32000,"message":"child isolation failed"}})
            continue
        send({
            "jsonrpc":"2.0","id":rid,
            "result":{
                "protocolVersion":1,
                "agentCapabilities":{"sessionCapabilities":{"close":{}}},
                "agentInfo":{"name":"fake","version":"1"},
                "authMethods":[]
            }
        })
    elif method == "session/new":
        send({"jsonrpc":"2.0","id":rid,"result":{"sessionId":session_id}})
    elif method == "session/prompt":
        text = request["params"]["prompt"][0]["text"]
        if text == "needs permission":
            send({
                "jsonrpc":"2.0",
                "id":"perm-1",
                "method":"session/request_permission",
                "params":{
                    "sessionId":session_id,
                    "toolCall":{"toolCallId":"call-1","status":"pending","title":"dangerous"},
                    "options":[{"optionId":"allow_once","name":"Allow once","kind":"allow_once"}]
                }
            })
            permission = json.loads(sys.stdin.readline())
            outcome = permission.get("result", {}).get("outcome", {})
            if outcome.get("optionId") != "allow_once":
                send({"jsonrpc":"2.0","id":rid,"result":{"stopReason":"cancelled"}})
                continue
            send({
                "jsonrpc":"2.0","method":"session/update",
                "params":{"sessionId":session_id,"update":{
                    "sessionUpdate":"agent_message_chunk",
                    "content":{"type":"text","text":"permission granted"}
                }}
            })
            send({"jsonrpc":"2.0","id":rid,"result":{"stopReason":"end_turn"}})
        else:
            send({
                "jsonrpc":"2.0","method":"session/update",
                "params":{"sessionId":session_id,"update":{
                    "sessionUpdate":"agent_message_chunk",
                    "content":{"type":"text","text":"reply: " + text}
                }}
            })
            send({"jsonrpc":"2.0","id":rid,"result":{"stopReason":"end_turn"}})
    elif method == "session/cancel":
        continue
    elif method == "session/close":
        send({"jsonrpc":"2.0","id":rid,"result":{}})
        break
    elif rid is not None:
        send({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"unknown"}})
'''


class AcpSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.agent = self.root / "fake_acp.py"
        self.agent.write_text(textwrap.dedent(FAKE_AGENT).lstrip())
        self.agent.chmod(0o755)
        self.runner = AcpRunner(
            id="fake",
            command=sys.executable,
            args=(str(self.agent),),
            enabled=True,
            trusted=True,
        )

    def session(self) -> AcpSession:
        env = os.environ.copy()
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(
            {
                "mcp": {
                    "servers": {
                        "oat-acp": {"type": "local"},
                        "oat-memory": {"type": "local"},
                        "context7": {"type": "remote"},
                    }
                }
            }
        )
        env["OAT_MEMORY_POSTGRES_DSN"] = "postgresql://user:secret@db/memory"
        return AcpSession(self.runner, self.root, environ=env, timeout_seconds=5).start()

    def test_prompt_round_trip_and_child_config_sanitization(self) -> None:
        session = self.session()
        self.addCleanup(session.close)
        result = session.prompt("hello")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["stop_reason"], "end_turn")
        self.assertEqual(result["text"], "reply: hello")
        self.assertEqual(session.state, "idle")

    def test_permission_is_suspended_and_resumed_explicitly(self) -> None:
        session = self.session()
        self.addCleanup(session.close)
        first = session.prompt("needs permission")
        self.assertEqual(first["status"], "permission_required")
        self.assertEqual(first["permission"]["options"][0]["optionId"], "allow_once")
        self.assertEqual(session.state, "waiting_permission")

        done = session.respond("allow_once")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["text"], "permission granted")
        self.assertEqual(session.state, "idle")

    def test_close_uses_acp_close_and_terminates_child(self) -> None:
        session = self.session()
        pid = session.process.pid
        session.close()
        self.assertEqual(session.state, "closed")
        self.assertIsNone(session.process)
        self.assertGreater(pid, 0)

    def test_runner_service_enqueues_prompt_and_reports_result_via_status(self) -> None:
        namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "acp-mcp"))
        RunnerService = namespace["RunnerService"]

        previous_bin = os.environ.get("OPENCODE_BIN")
        previous_parallel = os.environ.get("OAT_ACP_MAX_PARALLEL")
        os.environ["OPENCODE_BIN"] = str(self.agent)
        os.environ["OAT_ACP_MAX_PARALLEL"] = "1"
        service = RunnerService(self.root)
        try:
            started = service.call(
                "acp_runner",
                {"action": "start", "runner": "opencode", "message": "hello"},
            )
            self.assertEqual(started["status"], "running")
            session_id = started["session_id"]

            deadline = time.monotonic() + 5
            status = {}
            while time.monotonic() < deadline:
                status = service.call("acp_runner", {"action": "status", "session_id": session_id})
                if status.get("job", {}).get("status") == "completed":
                    break
                time.sleep(0.02)

            self.assertEqual(status["job"]["status"], "completed")
            self.assertEqual(status["job"]["text"], "reply: hello")
            service.call("acp_runner", {"action": "close", "session_id": session_id})
        finally:
            service.close_all()
            if previous_bin is None:
                os.environ.pop("OPENCODE_BIN", None)
            else:
                os.environ["OPENCODE_BIN"] = previous_bin
            if previous_parallel is None:
                os.environ.pop("OAT_ACP_MAX_PARALLEL", None)
            else:
                os.environ["OAT_ACP_MAX_PARALLEL"] = previous_parallel


if __name__ == "__main__":
    unittest.main()
