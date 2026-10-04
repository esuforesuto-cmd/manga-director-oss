"""Local stdio JSON-RPC server implementing the MCP tool/resource/prompt surface."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from typing import Any, TextIO

from manga_director._version import __version__
from manga_director.mcp.contracts import McpToolResult
from manga_director.mcp.prompts import McpPromptLoader
from manga_director.mcp.registry import ToolRegistry
from manga_director.mcp.resources import McpResourceProvider

LOGGER = logging.getLogger(__name__)


class McpServer:
    """Expose validated local tools over MCP-compatible JSON-RPC on stdio only."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        resources: McpResourceProvider,
        prompts: McpPromptLoader,
    ) -> None:
        self._tool_registry = tool_registry
        self._resources = resources
        self._prompts = prompts

    def tools(self) -> list[dict[str, Any]]:
        return self._tool_registry.list()

    def resources(self) -> list[dict[str, Any]]:
        return [resource.model_dump(by_alias=True) for resource in self._resources.list()]

    def prompts(self) -> list[dict[str, Any]]:
        return [prompt.model_dump() for prompt in self._prompts.list()]

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> McpToolResult:
        LOGGER.info("MCP tool started: %s", name)
        result = self._tool_registry.invoke(name, dict(arguments or {}))
        level = logging.INFO if result.success else logging.WARNING
        LOGGER.log(level, "MCP tool finished: %s success=%s", name, result.success)
        return result

    def read_resource(self, uri: str) -> dict[str, str]:
        LOGGER.info("MCP resource read: %s", uri)
        return self._resources.read(uri)

    def get_prompt(self, name: str, arguments: Mapping[str, str] | None = None) -> str:
        LOGGER.info("MCP prompt requested: %s", name)
        return self._prompts.get(name, dict(arguments or {}))

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC request; notifications intentionally return no response."""
        request_id = request.get("id")
        method = request.get("method")
        if not isinstance(method, str):
            return self._error(request_id, -32600, "Invalid request: method is required.")
        if method == "notifications/initialized":
            return None
        try:
            result = self._dispatch(method, request.get("params", {}))
        except Exception as exc:
            LOGGER.exception("MCP request failed: %s", method)
            del exc
            return self._error(request_id, -32000, "Request could not be completed.")
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def serve_stdio(
        self, input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout
    ) -> None:
        """Serve line-delimited JSON-RPC over stdio; no HTTP transport is exposed."""
        LOGGER.info("MCP stdio server started")
        for line in input_stream:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError("request must be a JSON object")
                response = self.handle(request)
            except (json.JSONDecodeError, ValueError) as exc:
                response = self._error(None, -32700, f"Parse error: {exc}")
            if response is not None:
                output_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
                output_stream.flush()
        LOGGER.info("MCP stdio server stopped")

    def _dispatch(self, method: str, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise ValueError("params must be an object")
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": "manga-director", "version": __version__},
            }
        if method == "tools/list":
            return {"tools": self.tools()}
        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                raise ValueError("tools/call requires a tool name")
            result = self.call_tool(name, params.get("arguments"))
            return {
                "content": [{"type": "text", "text": result.model_dump_json()}],
                "isError": not result.success,
            }
        if method == "resources/list":
            return {"resources": self.resources()}
        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str):
                raise ValueError("resources/read requires a URI")
            return {"contents": [self.read_resource(uri)]}
        if method == "prompts/list":
            return {"prompts": self.prompts()}
        if method == "prompts/get":
            name = params.get("name")
            if not isinstance(name, str):
                raise ValueError("prompts/get requires a prompt name")
            prompt = self.get_prompt(name, params.get("arguments"))
            return {"messages": [{"role": "user", "content": {"type": "text", "text": prompt}}]}
        raise ValueError(f"Method not found: {method}")

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
