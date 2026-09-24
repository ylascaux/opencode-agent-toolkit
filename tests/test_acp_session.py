from __future__ import annotations

import json
import os
import sys
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

session_id = "sess_fake"

def send(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    rid = request.get("id")
    if method == "initialize":
        inline = os.environ.get("OPENCODE_CONFIG_CONTENT", "")
        if "oat-acp" in inline:
            send({"jsonrpc":"2.0","id":rid,"error":{"code":-32000,"message":"recursive oat-acp leaked"}})
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
        self.agent.write_text(textwrap.dedent(FAKE_AGENT))
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
            {"mcp": {"servers": {"oat-acp": {"type": "local"}, "context7": {"type": "remote"}}}}
        )
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


if __name__ == "__main__":
    unittest.main()
