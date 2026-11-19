"""Synchronous MCP client used by the LangGraph agent to call the HR / IT tools.

The agent graph is synchronous, MCP is async: each question opens one MCP session, runs the
planned tool calls, and closes it. By default the server is started as a subprocess over stdio
(`python -m docupilot.mcp_server`); `InProcessMCPClient` talks to a server object in memory
(used by the tests and handy for debugging).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import sys
from typing import Any, Awaitable, Callable, Protocol

from mcp import ClientSession


class HRTools(Protocol):
    """What the graph needs: run several tool calls and get one dict back per call."""

    def call_many(self, calls: list[tuple[str, dict]]) -> list[dict]: ...


def _run(coro_factory: Callable[[], Awaitable[Any]]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())
    with concurrent.futures.ThreadPoolExecutor(1) as pool:  # already inside an event loop
        return pool.submit(lambda: asyncio.run(coro_factory())).result()


def parse_tool_result(result: Any) -> dict:
    if getattr(result, "isError", False):
        text = " ".join(getattr(c, "text", "") for c in result.content or [])
        return {"found": False, "error": "tool_error", "message": text or "The tool failed."}
    data = getattr(result, "structuredContent", None)
    if isinstance(data, dict):
        if set(data) == {"result"} and isinstance(data["result"], dict):
            return data["result"]
        return data
    for block in result.content or []:
        text = getattr(block, "text", None)
        if text:
            try:
                parsed = json.loads(text)
                return parsed if isinstance(parsed, dict) else {"result": parsed}
            except json.JSONDecodeError:
                return {"result": text}
    return {}


async def _call_all(session: ClientSession, calls: list[tuple[str, dict]]) -> list[dict]:
    await session.initialize()
    out = []
    for name, args in calls:
        out.append(parse_tool_result(await session.call_tool(name, {k: v for k, v in args.items() if v is not None})))
    return out


class StdioMCPClient:
    """Starts the MCP server as a subprocess for each question."""

    def __init__(self, command: str | None = None, args: list[str] | None = None, env: dict | None = None):
        self.command = command or sys.executable
        self.args = args if args is not None else ["-m", "docupilot.mcp_server"]
        self.env = env

    def call_many(self, calls: list[tuple[str, dict]]) -> list[dict]:
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self.command, args=self.args,
                                       env={**os.environ, **(self.env or {})})

        async def go():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    return await _call_all(session, calls)

        return _run(go)

    def list_tools(self) -> list[str]:
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self.command, args=self.args, env={**os.environ, **(self.env or {})})

        async def go():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return [t.name for t in (await session.list_tools()).tools]

        return _run(go)


class InProcessMCPClient:
    """Talks to a FastMCP server object over in-memory streams (real MCP protocol, no subprocess)."""

    def __init__(self, server):
        self.server = server

    def _session(self):
        from mcp.shared.memory import create_connected_server_and_client_session

        return create_connected_server_and_client_session(self.server._mcp_server)

    def call_many(self, calls: list[tuple[str, dict]]) -> list[dict]:
        async def go():
            async with self._session() as session:
                out = []
                for name, args in calls:
                    res = await session.call_tool(name, {k: v for k, v in args.items() if v is not None})
                    out.append(parse_tool_result(res))
                return out

        return _run(go)

    def list_tools(self) -> list[str]:
        async def go():
            async with self._session() as session:
                return [t.name for t in (await session.list_tools()).tools]

        return _run(go)
