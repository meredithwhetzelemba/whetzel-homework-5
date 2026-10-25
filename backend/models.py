"""Structured types for the Campus Customs agent team."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentTurn(BaseModel):
    """What one role returns after it finishes a task."""

    role: str = Field(description="Which shop role produced this answer.")
    summary: str = Field(description="What this role found, in a few sentences, using tool facts only.")
    ticket_ids: List[int] = Field(
        default_factory=list,
        description="Ticket ids this answer is about.",
    )
    facts_used: List[str] = Field(
        default_factory=list,
        description="Short facts copied from MCP tool results, not from memory.",
    )
    recommendation: str = Field(description="The decision or next step this role recommends.")
    needs_human_approval: bool = Field(
        description="True when money should move or a discount is still undecided."
    )
    customer_draft: Optional[str] = Field(
        default=None,
        description="Customer wording saved on the board, if any. None when no draft was written.",
    )
    refused: bool = Field(
        default=False,
        description="True when a guardrail stopped the task before or during the run.",
    )


class AuditEntry(BaseModel):
    """One append-only record for a single agent-loop step."""

    timestamp: str = Field(description="ISO-8601 UTC time this step was recorded.")
    run_id: str = Field(description="Groups every step from one team run.")
    agent: str = Field(description="Role that was running on this step.")
    iteration: int = Field(description="Step number within the run. Grows across delegated agents.")
    node: str = Field(description="Graph node or event name for this step.")
    thoughts: List[str] = Field(
        default_factory=list,
        description="Model thinking text for this step, when the API returned any.",
    )
    tool_name: Optional[str] = Field(default=None, description="Tool called on this step, if any.")
    tool_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments. Secrets are redacted.",
    )
    short_result: str = Field(
        default="",
        description="Short result of the tool or the step. Not a full transcript.",
    )
    stop_reason: Optional[str] = Field(
        default=None,
        description="continue, completed, max_steps, guardrail_block, delegation_limit, or error.",
    )
    task: str = Field(description="The task text this role was given, shortened.")
