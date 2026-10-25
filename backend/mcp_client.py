"""The only shop-data path for the agents: the Campus Customs MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
MCP_CONFIG_PATH = ROOT / ".mcp.json"


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    structured = getattr(value, "structured_content", None)
    if structured is not None:
        return _plain(structured)
    data = getattr(value, "data", None)
    if data is not None and not isinstance(data, (str, bytes)):
        return _plain(data)
    return value


def _abs_from_root(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    # absolute(), not resolve(): the venv python is a symlink, and following
    # it drops the virtualenv that has the server's packages.
    return str((ROOT / path).absolute())


def load_mcp_config() -> dict:
    """Read .mcp.json and resolve its command and script paths from the repo root.

    The committed file uses paths like mcp_server/.venv/bin/python so a grader's
    clone does not depend on this machine. The backend is often started from
    backend/, so those relative paths are anchored here, not on the shell cwd.
    """
    if not MCP_CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Missing MCP connection file: {MCP_CONFIG_PATH}")
    config = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    for spec in config.get("mcpServers", {}).values():
        if not isinstance(spec, dict):
            continue
        command = spec.get("command")
        if isinstance(command, str):
            spec["command"] = _abs_from_root(command)
        args = spec.get("args")
        if isinstance(args, list):
            spec["args"] = [
                _abs_from_root(arg) if isinstance(arg, str) and not arg.startswith("-") else arg
                for arg in args
            ]
    return config


class ShopMcp:
    """One stdio session to the server named in .mcp.json."""

    def __init__(self, config: dict | None = None) -> None:
        self._config = config if config is not None else load_mcp_config()
        self._client: Client | None = None

    async def __aenter__(self) -> "ShopMcp":
        self._client = Client(self._config)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    async def call(self, name: str, arguments: dict | None = None) -> dict:
        if self._client is None:
            raise RuntimeError("MCP client is not connected.")
        result = await self._client.call_tool(name, arguments or {})
        plain = _plain(result)
        if isinstance(plain, dict):
            return plain
        return {"result": plain}
