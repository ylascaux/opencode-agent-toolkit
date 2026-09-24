"""ACP v1 subprocess client used by the V2 runner MCP.

One toolkit session owns one ACP child process. This intentionally avoids a
daemon and keeps process lifetime scoped to the MCP server that OpenCode already
manages for the parent session.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from runtime.common.acp import AcpRunner


class AcpError(RuntimeError):
    pass


@dataclass
class PermissionRequest:
    request_id: Any
    params: dict[str, Any]
    option_ids: tuple[str, ...]

    def view(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.params.get("sessionId"),
            "tool_call": self.params.get("toolCall"),
            "options": self.params.get("options", []),
        }


@dataclass
class AcpSession:
    runner: AcpRunner
    cwd: Path
    environ: Mapping[str, str] | None = None
    timeout_seconds: float = 600.0
    max_output_chars: int = 50_000
    process: subprocess.Popen[str] | None = field(init=False, default=None)
    session_id: str = field(init=False, default="")
    state: str = field(init=False, default="new")
    agent_capabilities: dict[str, Any] = field(init=False, default_factory=dict)
    pending_permission: PermissionRequest | None = field(init=False, default=None)
    output_text: str = field(init=False, default="")
    updates: list[dict[str, Any]] = field(init=False, default_factory=list)
    active_prompt_id: int | None = field(init=False, default=None)
    _next_id: int = field(init=False, default=1)
    _queue: queue.Queue[dict[str, Any]] = field(init=False, default_factory=queue.Queue)
    _write_lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    _reader: threading.Thread | None = field(init=False, default=None)

    def _child_env(self) -> dict[str, str]:
        env = dict(os.environ if self.environ is None else self.environ)
        env["OAT_ACP_CHILD"] = "1"
        inline = env.get("OPENCODE_CONFIG_CONTENT", "").strip()
        if inline:
            try:
                payload = json.loads(inline)
                servers = payload.get("mcp", {}).get("servers", {})
                if isinstance(servers, dict):
                    servers.pop("oat-acp", None)
                    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(payload, separators=(",", ":"))
            except (TypeError, json.JSONDecodeError):
                pass
        return env

    def start(self) -> "AcpSession":
        if self.process is not None:
            return self
        if not self.runner.trusted:
            raise AcpError(f"ACP runner is not trusted: {self.runner.id}")
        argv = self.runner.argv(self.environ)
        if not self.runner.available(self.environ):
            raise AcpError(f"ACP runner executable not found: {argv[0]}")
        self.cwd = self.cwd.expanduser().resolve()
        if not self.cwd.is_dir():
            raise AcpError(f"ACP workspace does not exist: {self.cwd}")
        self.process = subprocess.Popen(
            argv,
            cwd=str(self.cwd),
            env=self._child_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
        )
        self.state = "initializing"
        self._reader = threading.Thread(target=self._read_loop, name=f"acp-{self.runner.id}", daemon=True)
        self._reader.start()
        initialized = self._request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {},
                "clientInfo": {
                    "name": "opencode-agent-toolkit",
                    "title": "OpenCode Agent Toolkit",
                    "version": "2",
                },
            },
            allow_permission=False,
        )
        if initialized.get("protocolVersion") != 1:
            self.close(force=True)
            raise AcpError(f"unsupported ACP protocol version: {initialized.get('protocolVersion')!r}")
        capabilities = initialized.get("agentCapabilities")
        self.agent_capabilities = capabilities if isinstance(capabilities, dict) else {}
        created = self._request(
            "session/new",
            {"cwd": str(self.cwd), "mcpServers": []},
            allow_permission=False,
        )
        session_id = created.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            self.close(force=True)
            raise AcpError("ACP runner did not return a session id")
        self.session_id = session_id
        self.state = "idle"
        return self

    def _read_loop(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        try:
            for line in self.process.stdout:
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    self._queue.put({"_protocol_error": "invalid JSON from ACP runner"})
                    continue
                if isinstance(payload, dict):
                    self._queue.put(payload)
        finally:
            self._queue.put({"_eof": True})

    def _send(self, payload: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None or self.process.poll() is not None:
            raise AcpError("ACP runner is not running")
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._write_lock:
            self.process.stdin.write(encoded + "\n")
            self.process.stdin.flush()

    def _request_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def _request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        allow_permission: bool,
    ) -> dict[str, Any]:
        request_id = self._request_id()
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        return self._wait_for_response(request_id, allow_permission=allow_permission)

    def _handle_update(self, payload: dict[str, Any]) -> None:
        params = payload.get("params")
        if not isinstance(params, dict):
            return
        update = params.get("update")
        if not isinstance(update, dict):
            return
        self.updates.append(update)
        if len(self.updates) > 100:
            del self.updates[:-100]
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content")
            if isinstance(content, dict) and content.get("type") == "text":
                text = content.get("text")
                if isinstance(text, str):
                    self.output_text = (self.output_text + text)[-self.max_output_chars :]

    def _permission(self, payload: dict[str, Any]) -> PermissionRequest:
        params = payload.get("params")
        if not isinstance(params, dict):
            raise AcpError("invalid ACP permission request")
        options = params.get("options")
        if not isinstance(options, list):
            raise AcpError("invalid ACP permission options")
        option_ids: list[str] = []
        for option in options:
            if isinstance(option, dict) and isinstance(option.get("optionId"), str):
                option_ids.append(option["optionId"])
        return PermissionRequest(payload.get("id"), params, tuple(option_ids))

    def _wait_for_response(self, request_id: int, *, allow_permission: bool) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AcpError("ACP request timed out")
            try:
                payload = self._queue.get(timeout=min(1.0, remaining))
            except queue.Empty:
                if self.process is not None and self.process.poll() is not None:
                    raise AcpError(f"ACP runner exited with code {self.process.returncode}")
                continue
            if payload.get("_eof"):
                raise AcpError("ACP runner closed stdout")
            if payload.get("_protocol_error"):
                raise AcpError(str(payload["_protocol_error"]))

            if payload.get("method") == "session/update":
                self._handle_update(payload)
                continue
            if "method" in payload and "id" in payload:
                if payload.get("method") == "session/request_permission":
                    permission = self._permission(payload)
                    if not allow_permission:
                        self._send(
                            {
                                "jsonrpc": "2.0",
                                "id": permission.request_id,
                                "result": {"outcome": {"outcome": "cancelled"}},
                            }
                        )
                        continue
                    self.pending_permission = permission
                    self.state = "waiting_permission"
                    raise _PermissionNeeded(permission)
                self._send(
                    {
                        "jsonrpc": "2.0",
                        "id": payload.get("id"),
                        "error": {"code": -32601, "message": "Client method not supported"},
                    }
                )
                continue
            if payload.get("id") != request_id:
                continue
            if "error" in payload:
                error = payload.get("error")
                message = error.get("message") if isinstance(error, dict) else error
                raise AcpError(f"ACP error: {message}")
            result = payload.get("result")
            return result if isinstance(result, dict) else {}

    def _wait_prompt(self) -> dict[str, Any]:
        assert self.active_prompt_id is not None
        try:
            result = self._wait_for_response(self.active_prompt_id, allow_permission=True)
        except _PermissionNeeded as pending:
            return {
                "status": "permission_required",
                "session_id": self.session_id,
                "permission": pending.permission.view(),
                "text": self.output_text,
            }
        self.active_prompt_id = None
        self.state = "idle"
        return {
            "status": "completed",
            "session_id": self.session_id,
            "stop_reason": result.get("stopReason", "end_turn"),
            "text": self.output_text,
        }

    def prompt(self, message: str) -> dict[str, Any]:
        if self.process is None:
            self.start()
        if self.active_prompt_id is not None:
            raise AcpError("ACP session already has an active prompt")
        if not isinstance(message, str) or not message.strip():
            raise AcpError("ACP prompt must be non-empty")
        self.output_text = ""
        self.pending_permission = None
        request_id = self._request_id()
        self.active_prompt_id = request_id
        self.state = "running"
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "session/prompt",
                "params": {
                    "sessionId": self.session_id,
                    "prompt": [{"type": "text", "text": message}],
                },
            }
        )
        return self._wait_prompt()

    def respond(self, option_id: str) -> dict[str, Any]:
        pending = self.pending_permission
        if pending is None or self.active_prompt_id is None:
            raise AcpError("ACP session is not waiting for permission")
        if option_id not in pending.option_ids:
            raise AcpError(f"unknown ACP permission option: {option_id}")
        self._send(
            {
                "jsonrpc": "2.0",
                "id": pending.request_id,
                "result": {"outcome": {"outcome": "selected", "optionId": option_id}},
            }
        )
        self.pending_permission = None
        self.state = "running"
        return self._wait_prompt()

    def cancel(self) -> None:
        if self.process is None or not self.session_id:
            return
        self._send(
            {
                "jsonrpc": "2.0",
                "method": "session/cancel",
                "params": {"sessionId": self.session_id},
            }
        )
        if self.pending_permission is not None:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": self.pending_permission.request_id,
                    "result": {"outcome": {"outcome": "cancelled"}},
                }
            )
            self.pending_permission = None
        self.state = "cancelled"

    def status(self) -> dict[str, Any]:
        return {
            "runner": self.runner.id,
            "session_id": self.session_id or None,
            "state": self.state,
            "pid": self.process.pid if self.process is not None and self.process.poll() is None else None,
            "permission": self.pending_permission.view() if self.pending_permission else None,
            "text": self.output_text,
            "updates": self.updates[-20:],
        }

    def close(self, *, force: bool = False) -> None:
        process = self.process
        if process is None:
            self.state = "closed"
            return
        if process.poll() is None and self.session_id and not force:
            session_caps = self.agent_capabilities.get("sessionCapabilities")
            supports_close = isinstance(session_caps, dict) and "close" in session_caps
            if supports_close:
                try:
                    self._request("session/close", {"sessionId": self.session_id}, allow_permission=False)
                except Exception:
                    pass
            elif self.active_prompt_id is not None:
                try:
                    self.cancel()
                except Exception:
                    pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        self.process = None
        self.state = "closed"


class _PermissionNeeded(Exception):
    def __init__(self, permission: PermissionRequest) -> None:
        super().__init__("permission required")
        self.permission = permission
