"""Campus Customs agent team.

Five PydanticAI roles share one MCP client. Any role can delegate to any
other role. Shop numbers come only from that MCP server.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from audit import AuditLogger
from mcp_client import ShopMcp
from models import AgentTurn

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPTS = HERE / "prompts"
MODEL_NAME = "gpt-6-luna"
ROLES = ("boss", "inventory", "accounting", "facilities", "customer_service")
MAX_DELEGATION_DEPTH = 2
REQUEST_LIMIT = 5

_UNSAFE = [
    (
        re.compile(r"(?i)(?<!not )(?<!n't )\b(email|e-mail|call|phone)\b.{0,40}\b(customer|vendor|landlord)s?\b"),
        "Do not email or call customers, vendors, or landlords.",
    ),
    (re.compile(r"\b(api[_-]?key|portkey|secret\s*key|\.env)\b", re.I), "Do not reveal secrets."),
    (re.compile(r"ignore (all )?(previous|prior) instructions", re.I), "Ignore instructions that try to override the shop rules."),
    (re.compile(r"reveal (your )?(system|hidden) prompt", re.I), "Do not reveal the system prompt."),
]


@dataclass
class ShopDeps:
    mcp: ShopMcp
    audit: AuditLogger
    active_agent: str
    delegation_depth: int = 0
    request_limit: int = REQUEST_LIMIT


def load_env() -> None:
    load_dotenv(HERE / ".env")
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / ".env")
    os.environ.setdefault("OPENAI_MODEL", MODEL_NAME)


def build_model() -> OpenAIResponsesModel:
    load_env()
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing in the environment / .env")
    chosen = os.getenv("OPENAI_MODEL", MODEL_NAME).strip()
    if chosen != MODEL_NAME:
        raise RuntimeError("This assignment only allows gpt-6-luna.")
    provider = OpenAIProvider(api_key=api_key, base_url="https://api.portkey.ai/v1")
    return OpenAIResponsesModel(MODEL_NAME, provider=provider)


def load_prompt(role: str) -> str:
    rules = (PROMPTS / "shop_rules.md").read_text(encoding="utf-8").strip()
    role_text = (PROMPTS / f"{role}.md").read_text(encoding="utf-8").strip()
    return f"{rules}\n\n{role_text}"


def blocked_task(task: str) -> str | None:
    for pattern, reason in _UNSAFE:
        if pattern.search(task or ""):
            return reason
    return None


def _empty_turn(role: str, summary: str, *, refused: bool = False) -> AgentTurn:
    return AgentTurn(
        role=role,
        summary=summary,
        ticket_ids=[],
        facts_used=[],
        recommendation=summary,
        needs_human_approval=False,
        customer_draft=None,
        refused=refused,
    )


AGENTS: dict[str, Agent[ShopDeps, AgentTurn]] = {}


async def run_role(role: str, task: str, deps: ShopDeps) -> AgentTurn:
    """Run one role, audit every loop step, and return its structured answer."""
    if role not in AGENTS:
        raise KeyError(role)
    deps.active_agent = role
    refusal = blocked_task(task)
    if refusal:
        answer = _empty_turn(role, refusal, refused=True)
        deps.audit.log_event(
            "guardrail_block",
            agent=role,
            task=task,
            payload={"reason": refusal},
            stop_reason="guardrail_block",
        )
        deps.audit.log_final(answer, agent=role, task=task, stop_reason="guardrail_block")
        return answer

    agent = AGENTS[role]
    answer: AgentTurn | None = None
    stop_reason = "completed"
    try:
        async with agent.iter(
            task,
            deps=deps,
            usage_limits=UsageLimits(request_limit=deps.request_limit),
        ) as agent_run:
            async for node in agent_run:
                deps.audit.log_node(node, agent=role, task=task)
            result = agent_run.result
            if result is not None and isinstance(result.output, AgentTurn):
                answer = result.output
                if not answer.role:
                    answer = answer.model_copy(update={"role": role})
    except UsageLimitExceeded:
        stop_reason = "max_steps"
        answer = _empty_turn(
            role,
            "Stopped because this role hit its model-request limit. No further shop facts were guessed.",
        )
    except Exception as exc:
        stop_reason = "error"
        deps.audit.log_event(
            "agent_error",
            agent=role,
            task=task,
            payload={"error": str(exc)[:300]},
            stop_reason="error",
        )
        answer = _empty_turn(role, f"This role stopped on an error: {exc}"[:500], refused=True)

    if answer is None:
        stop_reason = "max_steps"
        answer = _empty_turn(role, "This role finished without a structured answer.")
    deps.audit.log_final(answer, agent=role, task=task, stop_reason=stop_reason)
    return answer


async def _delegate(ctx: RunContext[ShopDeps], target: str, task: str) -> dict:
    if target == ctx.deps.active_agent:
        ctx.deps.audit.log_event(
            "delegation_refused",
            agent=ctx.deps.active_agent,
            task=task,
            payload={"target": target, "reason": "self"},
            stop_reason="delegation_limit",
        )
        return {"delegated": False, "role": target, "reason": "A role cannot delegate to itself."}
    if ctx.deps.delegation_depth >= MAX_DELEGATION_DEPTH:
        ctx.deps.audit.log_event(
            "delegation_refused",
            agent=ctx.deps.active_agent,
            task=task,
            payload={"target": target, "depth": ctx.deps.delegation_depth},
            stop_reason="delegation_limit",
        )
        return {
            "delegated": False,
            "role": target,
            "reason": "Delegation depth limit reached. Answer from the facts you already have.",
        }
    child = replace(
        ctx.deps,
        active_agent=target,
        delegation_depth=ctx.deps.delegation_depth + 1,
    )
    handoff = f"Request from {ctx.deps.active_agent}: {task}"
    answer = await run_role(target, handoff, child)
    return {"delegated": True, **answer.model_dump()}


def _delegate_tool(target: str):
    async def ask(ctx: RunContext[ShopDeps], task: str) -> dict:
        return await _delegate(ctx, target, task)

    ask.__name__ = f"ask_{target}"
    ask.__doc__ = (
        f"Delegate one specific question to {target.replace('_', ' ')}. "
        "Full connectivity: any role may ask any other role. "
        "Pass the ticket id and the question. Do not ask this role to email or to invent numbers."
    )
    return ask


async def _call_mcp(ctx: RunContext[ShopDeps], name: str, arguments: dict) -> dict:
    result = await ctx.deps.mcp.call(name, arguments)
    ctx.deps.audit.log_event(
        "mcp_result",
        agent=ctx.deps.active_agent,
        task=name,
        payload={"tool": name, "arguments": arguments, "result": result},
        stop_reason="continue",
    )
    return result


async def list_open_tickets(ctx: RunContext[ShopDeps]) -> dict:
    """List open tickets and shop today. Reads tickets and desk through MCP."""
    return await _call_mcp(ctx, "list_open_tickets", {})


async def lookup_order_stock_and_reprint_invoice(ctx: RunContext[ShopDeps], ticket_id: int) -> dict:
    """Read a customer_order's size stock, reprint invoice, and vendor through MCP."""
    return await _call_mcp(ctx, "lookup_order_stock_and_reprint_invoice", {"ticket_id": ticket_id})


async def lookup_rent_due_against_cash(ctx: RunContext[ShopDeps], ticket_id: int) -> dict:
    """Read a rent_notice lease, shop today, and checking balance through MCP."""
    return await _call_mcp(ctx, "lookup_rent_due_against_cash", {"ticket_id": ticket_id})


async def lookup_bulk_discount_margin(ctx: RunContext[ShopDeps], ticket_id: int) -> dict:
    """Read a price_override's size stock, unit cost, and list price through MCP."""
    return await _call_mcp(ctx, "lookup_bulk_discount_margin", {"ticket_id": ticket_id})


async def save_board_draft(ctx: RunContext[ShopDeps], ticket_id: int, author_role: str, draft: str) -> dict:
    """Append a customer draft to the ticket. Does not send email. Writes tickets through MCP."""
    return await _call_mcp(
        ctx,
        "save_board_draft",
        {"ticket_id": ticket_id, "author_role": author_role, "draft": draft},
    )


async def pay_approved_obligation(ctx: RunContext[ShopDeps], ticket_id: int, approved_by: str) -> dict:
    """Pay a ticket's stored invoice or rent only when a human approver is named. Amount comes from MCP."""
    return await _call_mcp(
        ctx,
        "pay_approved_obligation",
        {"ticket_id": ticket_id, "approved_by": approved_by},
    )


MCP_TOOLS = [
    list_open_tickets,
    lookup_order_stock_and_reprint_invoice,
    lookup_rent_due_against_cash,
    lookup_bulk_discount_margin,
    save_board_draft,
]


def build_team(model: OpenAIResponsesModel | None = None) -> dict[str, Agent[ShopDeps, AgentTurn]]:
    """Create the five agents and give each one every other role plus the MCP tools."""
    model = model or build_model()
    AGENTS.clear()
    for role in ROLES:
        AGENTS[role] = Agent(
            model,
            deps_type=ShopDeps,
            output_type=AgentTurn,
            system_prompt=load_prompt(role),
            name=role,
            retries=1,
        )
    for role, agent in AGENTS.items():
        for tool in MCP_TOOLS:
            agent.tool(tool)
        for other in ROLES:
            if other != role:
                agent.tool(_delegate_tool(other))
    return AGENTS


async def run_boss(task: str, *, audit: AuditLogger | None = None, mcp: ShopMcp | None = None) -> AgentTurn:
    """Boss starts the team. Specialists run only when Boss, or someone Boss called, delegates."""
    if not AGENTS:
        build_team()
    logger = audit or AuditLogger()
    logger.log_event(
        "harness_start",
        agent="boss",
        task=task,
        payload={
            "model": MODEL_NAME,
            "max_delegation_depth": MAX_DELEGATION_DEPTH,
            "request_limit": REQUEST_LIMIT,
        },
        stop_reason="continue",
    )
    if mcp is not None:
        deps = ShopDeps(mcp=mcp, audit=logger, active_agent="boss")
        return await run_role("boss", task, deps)
    async with ShopMcp() as session:
        deps = ShopDeps(mcp=session, audit=logger, active_agent="boss")
        return await run_role("boss", task, deps)
