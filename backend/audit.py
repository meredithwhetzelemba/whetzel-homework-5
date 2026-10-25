"""Append-only audit trail for the agent team."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models import AuditEntry

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
_SHORT = 1200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(key): _jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(value) for value in obj]
    if hasattr(obj, "model_dump"):
        return _jsonable(obj.model_dump())
    return repr(obj)


def _shorten(value: Any, limit: int = _SHORT) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(_jsonable(value), ensure_ascii=False)
    text = " ".join(text.split())
    text = re.sub(
        r"(?i)(api[_-]?key|portkey|authorization|bearer|password)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        text,
    )
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


class AuditLogger:
    """Append to output/audit_trail.json. Never replaces the file with a fresh list."""

    def __init__(self, path: Path = AUDIT_PATH, *, run_id: Optional[str] = None) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or f"team_{uuid4().hex[:10]}"
        self.iteration = 0
        self._entries: List[Dict[str, Any]] = []
        if self.path.exists() and self.path.stat().st_size:
            try:
                existing = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = None
            if isinstance(existing, dict) and isinstance(existing.get("entries"), list):
                self._entries = list(existing["entries"])
            elif isinstance(existing, list):
                self._entries = existing

    def _flush(self) -> None:
        payload = {"entries": self._entries}
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def _append(self, entry: AuditEntry) -> None:
        self._entries.append(entry.model_dump())
        self._flush()

    def log_event(
        self,
        kind: str,
        *,
        agent: str,
        task: str,
        payload: Optional[Dict[str, Any]] = None,
        stop_reason: Optional[str] = None,
    ) -> None:
        self._append(
            AuditEntry(
                timestamp=_now(),
                run_id=self.run_id,
                agent=agent,
                iteration=self.iteration,
                node=f"event:{kind}",
                thoughts=[],
                tool_name=None,
                tool_args={},
                short_result=_shorten(payload or {}),
                stop_reason=stop_reason,
                task=_shorten(task, 240),
            )
        )

    def log_node(self, node: Any, *, agent: str, task: str) -> None:
        thoughts: List[str] = []
        tool_calls: List[tuple[Optional[str], Dict[str, Any]]] = []
        short_result = ""
        node_name = type(node).__name__

        if hasattr(node, "model_response"):
            for part in getattr(node.model_response, "parts", []) or []:
                part_name = type(part).__name__
                if part_name == "ThinkingPart":
                    content = str(getattr(part, "content", "") or "")
                    if content:
                        thoughts.append(_shorten(content, 300))
                elif part_name == "TextPart" and not short_result:
                    short_result = _shorten(getattr(part, "content", ""))
                elif part_name == "ToolCallPart":
                    raw_args = _jsonable(getattr(part, "args", None))
                    tool_calls.append(
                        (
                            getattr(part, "tool_name", None),
                            raw_args if isinstance(raw_args, dict) else {"args": raw_args},
                        )
                    )

        if hasattr(node, "content") and getattr(node, "content") is not None:
            short_result = _shorten(getattr(node, "content"))

        if not tool_calls:
            self.iteration += 1
            self._append(
                AuditEntry(
                    timestamp=_now(),
                    run_id=self.run_id,
                    agent=agent,
                    iteration=self.iteration,
                    node=node_name,
                    thoughts=thoughts,
                    tool_name=None,
                    tool_args={},
                    short_result=short_result,
                    stop_reason="continue",
                    task=_shorten(task, 240),
                )
            )
            return

        for tool_name, tool_args in tool_calls:
            self.iteration += 1
            self._append(
                AuditEntry(
                    timestamp=_now(),
                    run_id=self.run_id,
                    agent=agent,
                    iteration=self.iteration,
                    node=node_name,
                    thoughts=thoughts,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    short_result=short_result,
                    stop_reason="continue",
                    task=_shorten(task, 240),
                )
            )

    def log_final(self, answer: Any, *, agent: str, task: str, stop_reason: str) -> None:
        self._append(
            AuditEntry(
                timestamp=_now(),
                run_id=self.run_id,
                agent=agent,
                iteration=self.iteration,
                node="session_end",
                thoughts=[],
                tool_name=None,
                tool_args={},
                short_result=_shorten(answer),
                stop_reason=stop_reason,
                task=_shorten(task, 240),
            )
        )
