"""Campus Customs desk API.

Shop facts and the cash payment go through the MCP server.
This process does not query the shop database itself.
Start from this folder:

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from audit import AUDIT_PATH
from mcp_client import ShopMcp
from team import run_boss

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"

app = FastAPI(title="Campus Customs Desk")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveRequest(BaseModel):
    approved_by: str = Field(description="Name of the human who clicked approve.")


def _events(limit: int) -> dict:
    if not AUDIT_PATH.is_file():
        return {"events": []}
    try:
        payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"events": []}
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    events = []
    for entry in entries:
        said = (entry.get("short_result") or "").strip()
        tool = entry.get("tool_name")
        if not said and not tool:
            continue
        events.append(
            {
                "timestamp": entry.get("timestamp"),
                "run_id": entry.get("run_id"),
                "agent": entry.get("agent"),
                "said": said,
                "tool": tool,
                "stop_reason": entry.get("stop_reason"),
            }
        )
    return {"events": events[-limit:]}


def _latest_run_events() -> list:
    events = _events(400)["events"]
    if not events:
        return []
    run_id = events[-1]["run_id"]
    return [event for event in events if event["run_id"] == run_id]


@app.get("/tickets")
async def tickets() -> dict:
    """The three board tickets and whether each is open or resolved."""
    async with ShopMcp() as mcp:
        return await mcp.call("list_board_tickets", {})


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict:
    """Run the agent team on one ticket. Agents prepare work. They do not pay."""
    async with ShopMcp() as mcp:
        board = await mcp.call("list_board_tickets", {})
    known = {row["id"] for row in board.get("tickets", [])}
    if ticket_id not in known:
        raise HTTPException(status_code=404, detail="No ticket with that id.")
    task = (
        f"Work only ticket {ticket_id}. "
        "Use the lookup tool that matches this ticket. "
        "Delegate only the roles this ticket needs. "
        "If money is due, prepare the recommendation and name the stored amount. "
        "Do not pay. Do not email anyone."
    )
    answer = await run_boss(task)
    events = _latest_run_events()
    resolved = None
    if not answer.refused:
        async with ShopMcp() as mcp:
            resolved = await mcp.call("resolve_ticket", {"ticket_id": ticket_id})
    return {
        "ticket_id": ticket_id,
        "result": answer.model_dump(),
        "events": events,
        "resolved": resolved,
    }


@app.get("/events")
def events(limit: int = 40) -> dict:
    """Recent agent turns: what each role said and which tool it used."""
    limit = max(1, min(limit, 200))
    return _events(limit)


@app.post("/tickets/{ticket_id}/approve")
async def approve(ticket_id: int, body: ApproveRequest) -> dict:
    """A human clicked approve. This call is what moves cash."""
    async with ShopMcp() as mcp:
        result = await mcp.call(
            "pay_approved_obligation",
            {"ticket_id": ticket_id, "approved_by": body.approved_by},
        )
    if not result.get("paid"):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.get("/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts, through MCP."""
    async with ShopMcp() as mcp:
        return await mcp.call("get_checking_balance", {})


@app.post("/reset")
def reset() -> dict:
    """Copy the original shop database over the working copy."""
    if not ORIGINAL_DB.is_file():
        raise HTTPException(status_code=500, detail="Original database is missing.")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    return {"reset": True, "database": "data/campus_customs_new.db"}
