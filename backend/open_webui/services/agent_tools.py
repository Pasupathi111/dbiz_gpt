"""
Agent Tool Registry for the Global Agentic Assistant.

Each tool wraps an EXISTING finance_service function — the same function the
corresponding page's button already calls. Tools never duplicate business
logic; they only adapt a generic (user, context) call shape onto the real
service function's signature, then leave permission/risk classification and
audit logging to the caller (routers/finance.py `/agent/execute`).

To add a new tool: add a service function to finance_service.py first (or
reuse one), then register it here. No changes to the execution engine,
frontend registry, or drawer UI are needed.
"""

from typing import Any, Awaitable, Callable, Optional

from open_webui.services import finance_service as fs

READ_ONLY = "READ_ONLY"
LOW_RISK_WRITE = "LOW_RISK_WRITE"
HIGH_RISK_WRITE = "HIGH_RISK_WRITE"


class AgentToolError(Exception):
    """Raised by a tool wrapper for a user-facing, non-crash failure
    (e.g. missing required context) — rendered as a friendly message in the
    assistant drawer rather than a generic 500."""


def _period_id(context: dict) -> str:
    period_id = context.get("periodId") or context.get("period_id") or context.get("selectedPeriod")
    if not period_id:
        raise AgentToolError(
            "No reporting period is selected. Choose a period on this page and try again."
        )
    return period_id


def _entity_id(context: dict, label: str = "record") -> str:
    entity_id = (
        context.get("entityId")
        or context.get("entity_id")
        or (context.get("selectedRecords") or [None])[0]
    )
    if not entity_id:
        raise AgentToolError(f"Select a {label} on this page first, then ask me again.")
    return entity_id


class AgentTool:
    def __init__(
        self,
        name: str,
        description: str,
        risk: str,
        execute: Callable[[Any, dict], Awaitable[dict]],
        permission: Optional[str] = None,
        confirm_message: Optional[Callable[[dict], str]] = None,
    ):
        self.name = name
        self.description = description
        self.risk = risk
        self.execute = execute
        self.permission = permission
        self.confirm_message = confirm_message or (lambda ctx: f"Proceed with {name}?")


# ---------------------------------------------------------------------------
# Tool implementations (thin adapters over finance_service)
# ---------------------------------------------------------------------------


async def _portfolio_summary(user, context: dict) -> dict:
    return await fs.get_dashboard(user.id, context.get("periodId") or context.get("period_id"))


async def _list_exceptions(user, context: dict) -> dict:
    period_id = context.get("periodId") or context.get("period_id")
    return {"exceptions": await fs.get_exceptions(user.id, period_id=period_id, exc_status="OPEN")}


async def _analyze_exceptions(user, context: dict) -> dict:
    return await fs.analyze_reconciliation_exceptions(user.id, _period_id(context))


async def _run_reconciliation(user, context: dict) -> dict:
    return await fs.run_reconciliation(user.id, _period_id(context))


async def _run_reconciliation_and_summarize(user, context: dict) -> dict:
    return await fs.run_reconciliation_and_summarize(user.id, _period_id(context))


async def _reconciliation_summary(user, context: dict) -> dict:
    return await fs.get_reconciliation_summary(user.id, context.get("periodId") or context.get("period_id"))


async def _analyze_movements(user, context: dict) -> dict:
    return await fs.analyze_movements(user.id, _period_id(context))


async def _list_movements(user, context: dict) -> dict:
    period_id = context.get("periodId") or context.get("period_id")
    return {"movements": await fs.get_movements(user.id, period_id=period_id)}


async def _generate_schedule(user, context: dict) -> dict:
    return await fs.generate_schedule(user.id, _period_id(context))


async def _validate_schedule(user, context: dict) -> dict:
    return await fs.validate_schedule(user.id, _period_id(context))


async def _generate_journals(user, context: dict) -> dict:
    return await fs.generate_journals(user.id, _period_id(context))


async def _approve_journal(user, context: dict) -> dict:
    journal_id = _entity_id(context, "journal entry")
    result = await fs.approve_journal(user.id, journal_id, user=user)
    if not result:
        raise AgentToolError(f"Journal {journal_id} could not be found.")
    return result


async def _reject_journal(user, context: dict) -> dict:
    journal_id = _entity_id(context, "journal entry")
    reason = context.get("reason") or "Rejected via agentic assistant"
    result = await fs.reject_journal(user.id, journal_id, reason, user=user)
    if not result:
        raise AgentToolError(f"Journal {journal_id} could not be found.")
    return result


async def _generate_audit_schedule(user, context: dict) -> dict:
    return await fs.generate_audit_schedule(user.id, _period_id(context))


async def _generate_commentary(user, context: dict) -> dict:
    return await fs.generate_commentary(user.id, _period_id(context), force_llm=True)


async def _generate_commentary_with_movements(user, context: dict) -> dict:
    return await fs.generate_commentary_with_movements(user.id, _period_id(context))


async def _approve_commentary(user, context: dict) -> dict:
    commentary_id = _entity_id(context, "commentary section")
    result = await fs.approve_commentary(user.id, commentary_id, user=user)
    if not result:
        raise AgentToolError(f"Commentary {commentary_id} could not be found.")
    return result


async def _pending_reviews(user, context: dict) -> dict:
    return {"reviews": await fs.get_pending_reviews(user.id)}


async def _approve_review(user, context: dict) -> dict:
    review_id = _entity_id(context, "review item")
    return await fs.approve_review(user.id, {"review_id": review_id, "comments": context.get("comments")}, user=user)


async def _reject_review(user, context: dict) -> dict:
    review_id = _entity_id(context, "review item")
    reason = context.get("reason") or "Rejected via agentic assistant"
    return await fs.reject_review(user.id, {"review_id": review_id, "reason": reason}, user=user)


async def _audit_trail(user, context: dict) -> dict:
    period_id = context.get("periodId") or context.get("period_id")
    return {"entries": await fs.get_audit_trail(user.id, period_id=period_id)}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

AGENT_TOOLS: dict[str, AgentTool] = {
    "portfolio.summary": AgentTool(
        "portfolio.summary", "Summarize the current portfolio", READ_ONLY, _portfolio_summary,
    ),
    "exceptions.list": AgentTool(
        "exceptions.list", "Retrieve open reconciliation exceptions", READ_ONLY, _list_exceptions,
    ),
    "exceptions.analyze": AgentTool(
        "exceptions.analyze",
        "Group and summarize reconciliation exceptions by severity/category",
        READ_ONLY,
        _analyze_exceptions,
    ),
    "reconciliation.run": AgentTool(
        "reconciliation.run", "Run bond reconciliation for the selected period", LOW_RISK_WRITE, _run_reconciliation,
    ),
    "reconciliation.run_and_summarize": AgentTool(
        "reconciliation.run_and_summarize",
        "Run reconciliation and summarize what changed",
        LOW_RISK_WRITE,
        _run_reconciliation_and_summarize,
    ),
    "reconciliation.summary": AgentTool(
        "reconciliation.summary", "Get the latest reconciliation summary", READ_ONLY, _reconciliation_summary,
    ),
    "movements.analyze": AgentTool(
        "movements.analyze", "Analyze bond movements for the period", LOW_RISK_WRITE, _analyze_movements,
    ),
    "movements.list": AgentTool(
        "movements.list", "Retrieve bond movements", READ_ONLY, _list_movements,
    ),
    "schedule.generate": AgentTool(
        "schedule.generate", "Generate the bond schedule", LOW_RISK_WRITE, _generate_schedule,
    ),
    "schedule.validate": AgentTool(
        "schedule.validate", "Validate the bond schedule for inconsistencies", LOW_RISK_WRITE, _validate_schedule,
    ),
    "journals.generate": AgentTool(
        "journals.generate", "Generate draft journal entries", LOW_RISK_WRITE, _generate_journals,
    ),
    "journals.approve": AgentTool(
        "journals.approve",
        "Approve a draft journal entry",
        HIGH_RISK_WRITE,
        _approve_journal,
        permission="finance.approve",
        confirm_message=lambda ctx: "Approve this journal entry? This posts it and cannot be undone from here.",
    ),
    "journals.reject": AgentTool(
        "journals.reject",
        "Reject a draft journal entry",
        HIGH_RISK_WRITE,
        _reject_journal,
        permission="finance.approve",
        confirm_message=lambda ctx: "Reject this journal entry?",
    ),
    "audit_schedule.generate": AgentTool(
        "audit_schedule.generate", "Generate the audit schedule", LOW_RISK_WRITE, _generate_audit_schedule,
    ),
    "commentary.generate": AgentTool(
        "commentary.generate", "Generate month-end commentary", LOW_RISK_WRITE, _generate_commentary,
    ),
    "commentary.generate_with_movements": AgentTool(
        "commentary.generate_with_movements",
        "Generate commentary and flag unusual movements",
        LOW_RISK_WRITE,
        _generate_commentary_with_movements,
    ),
    "commentary.approve": AgentTool(
        "commentary.approve",
        "Approve a commentary section",
        HIGH_RISK_WRITE,
        _approve_commentary,
        permission="finance.approve",
        confirm_message=lambda ctx: "Approve this commentary section?",
    ),
    "review.pending": AgentTool(
        "review.pending", "List items pending review", READ_ONLY, _pending_reviews,
    ),
    "review.approve": AgentTool(
        "review.approve",
        "Approve a pending review item",
        HIGH_RISK_WRITE,
        _approve_review,
        permission="finance.approve",
        confirm_message=lambda ctx: "Approve this item?",
    ),
    "review.reject": AgentTool(
        "review.reject",
        "Reject a pending review item",
        HIGH_RISK_WRITE,
        _reject_review,
        permission="finance.approve",
        confirm_message=lambda ctx: "Reject this item?",
    ),
    "audit_trail.list": AgentTool(
        "audit_trail.list", "Retrieve recent audit trail activity", READ_ONLY, _audit_trail,
    ),
}


# Static "what to suggest next" map, keyed by the tool just executed.
NEXT_SUGGESTIONS: dict[str, list[str]] = {
    "reconciliation.run": ["exceptions.analyze", "commentary.generate"],
    "reconciliation.run_and_summarize": ["exceptions.analyze", "commentary.generate"],
    "exceptions.analyze": ["commentary.generate", "reconciliation.summary"],
    "movements.analyze": ["commentary.generate_with_movements"],
    "schedule.generate": ["schedule.validate"],
    "journals.generate": ["review.pending"],
    "audit_schedule.generate": ["audit_trail.list"],
    "commentary.generate": ["review.pending"],
    "commentary.generate_with_movements": ["review.pending"],
}


def get_tool(name: str) -> Optional[AgentTool]:
    return AGENT_TOOLS.get(name)
