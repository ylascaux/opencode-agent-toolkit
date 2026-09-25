"""Minimal stdio MCP server used by toolkit-owned local tools.

Supports legacy initialize and the modern 2026-07-28 metadata envelope without
pulling an MCP framework into the daily launcher.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

MODERN_PROTOCOL = "2026-07-28"
LEGACY_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PROTOCOL_META = "io.modelcontextprotocol/protocolVersion"
CLIENT_INFO_META = "io.modelcontextprotocol/clientInfo"
CLIENT_CAPS_META = "io.modelcontextprotocol/clientCapabilities"
SERVER_INFO_META = "io.modelcontextprotocol/serverInfo"


class McpStdioServer:
    def __init__(
        self,
        *,
        name: str,
        version: str,
        tools: list[dict[str, Any]],
        call_tool: Callable[[str, dict[str, Any]], dict[str, Any]],
        instructions: str,
    ) -> None:
        self.name = name
        self.version = version
        self.tools = tools
        self.call_tool = call_tool
        self.instructions = instructions
        self.era: str | None = None
        self.initialized = False
        self.ready = False

    def _error(self, request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": error}

    @staticmethod
    def _meta(request: dict[str, Any]) -> dict[str, Any] | None:
        params = request.get("params")
        if not isinstance(params, dict):
            return None
        meta = params.get("_meta")
        return meta if isinstance(meta, dict) else None

    def _validate_modern(self, request: dict[str, Any]) -> dict[str, Any] | None:
        meta = self._meta(request)
        if meta is None:
            return self._error(request.get("id"), -32602, "Invalid modern MCP metadata")
        requested = meta.get(PROTOCOL_META)
        if requested != MODERN_PROTOCOL:
            return self._error(
                request.get("id"),
                -32022,
                "Unsupported protocol version",
                {"supported": [MODERN_PROTOCOL], "requested": requested},
            )
        if not isinstance(meta.get(CLIENT_CAPS_META), dict):
            return self._error(request.get("id"), -32602, "Missing client capabilities")
        return None

    def _modernize(self, result: dict[str, Any], *, cacheable: bool = False) -> dict[str, Any]:
        meta = result.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
        output = dict(result)
        output["resultType"] = "complete"
        if cacheable:
            output["ttlMs"] = 0
            output["cacheScope"] = "private"
        output["_meta"] = {
            **meta,
            SERVER_INFO_META: {"name": self.name, "version": self.version},
        }
        return output

    def handle(self, request: Any) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return self._error(None, -32600, "Invalid request")
        request_id = request.get("id")
        method = request["method"]
        meta = self._meta(request)
        version = meta.get(PROTOCOL_META) if meta else None

        if self.era is None:
            if method == "initialize":
                self.era = "legacy"
            elif method == "server/discover" or version is not None:
                invalid = self._validate_modern(request)
                if invalid:
                    return invalid
                self.era = "modern"
                self.ready = True
        elif self.era == "modern":
            invalid = self._validate_modern(request)
            if invalid:
                return invalid
        elif version == MODERN_PROTOCOL or method == "server/discover":
            return self._error(request_id, -32601, "Method not found")

        if request_id is None:
            if self.era == "legacy" and method == "notifications/initialized" and self.initialized:
                self.ready = True
            return None

        def ok(result: dict[str, Any], *, cacheable: bool = False) -> dict[str, Any]:
            if self.era == "modern":
                result = self._modernize(result, cacheable=cacheable)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        if self.era == "modern":
            if method == "server/discover":
                return ok(
                    {
                        "supportedVersions": [MODERN_PROTOCOL],
                        "capabilities": {"tools": {}},
                        "instructions": self.instructions,
                    },
                    cacheable=True,
                )
            if method in {"initialize", "ping"}:
                return self._error(request_id, -32601, "Method not found")
        else:
            if method == "ping":
                return ok({})
            if method == "initialize":
                params = request.get("params")
                if self.initialized or not isinstance(params, dict):
                    return self._error(request_id, -32602, "Invalid initialization")
                requested = params.get("protocolVersion")
                if not isinstance(requested, str):
                    return self._error(request_id, -32602, "Invalid initialization")
                self.initialized = True
                protocol = requested if requested in LEGACY_PROTOCOLS else LEGACY_PROTOCOLS[0]
                return ok(
                    {
                        "protocolVersion": protocol,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": self.name, "version": self.version},
                    }
                )
            if not self.ready:
                return self._error(request_id, -32000, "Server is not initialized")

        if method == "tools/list":
            return ok({"tools": self.tools}, cacheable=self.era == "modern")
        if method != "tools/call":
            return self._error(request_id, -32601, "Method not found")

        params = request.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            return self._error(request_id, -32602, "Invalid tool call")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return self._error(request_id, -32602, "Invalid tool arguments")
        try:
            result = self.call_tool(params["name"], arguments)
            text = json.dumps(result, ensure_ascii=False)
            return ok({"content": [{"type": "text", "text": text}], "structuredContent": result})
        except Exception as exc:
            result = {"code": "operation_failed", "message": str(exc)[:1000]}
            text = json.dumps(result, ensure_ascii=False)
            return ok(
                {
                    "isError": True,
                    "content": [{"type": "text", "text": text}],
                    "structuredContent": result,
                }
            )


def run_stdio(server: McpStdioServer, *, max_line_bytes: int = 256 * 1024) -> int:
    for raw in sys.stdin.buffer:
        if len(raw) > max_line_bytes:
            response = server._error(None, -32600, "Request exceeds size limit")
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()
            continue
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            response = server._error(None, -32700, "Parse error")
        else:
            response = server.handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0
