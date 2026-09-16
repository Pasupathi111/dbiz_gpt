"""
Finance Copilot tools for Bond Management.

Provides LLM-callable tool functions that surface bond portfolio data,
reconciliation status, exceptions, movements, journals, audit schedules,
and AI-generated commentary. Each function delegates to the finance
service layer and returns a human-readable text string.

These tools follow the OpenWebUI builtin-tool convention: every public
async function whose name does not start with ``_`` is discovered as a
tool. Parameters prefixed with ``__`` are injected by the framework and
hidden from the LLM.
"""

from __future__ import annotations

import logging
from typing import Optional

from open_webui.services import finance_service

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_sgd(value) -> str:
    """Format a numeric value as SGD currency."""
    if value is None:
        return "N/A"
    return f"SGD {value:,.2f}"


def _fmt_pct(value) -> str:
    """Format a numeric value as a percentage."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _user_id(user: dict | None) -> str:
    """Extract user id from the __user__ dict, falling back to 'anonymous'."""
    if user and isinstance(user, dict):
        return user.get("id", "anonymous")
    return "anonymous"


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

async def get_portfolio_summary(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Get bond portfolio key performance indicators (KPIs) including total bonds,
    market value, face value, reconciliation rate, and pending items.

    :return: Portfolio summary text with KPI figures in SGD
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching portfolio summary...", "done": False}})

    uid = _user_id(__user__)
    dashboard = await finance_service.get_dashboard(uid)
    kpis = dashboard.get("kpis", {})

    lines = [
        f"Portfolio Summary - {dashboard.get('period_name', 'Current Period')}",
        f"  Total bonds: {kpis.get('total_bonds', 0)}",
        f"  Total face value: {_fmt_sgd(kpis.get('total_face_value', 0))}",
        f"  Reconciliation rate: {_fmt_pct(kpis.get('recon_rate', 0))}",
        f"  Open exceptions: {kpis.get('exceptions_open', 0)}",
        f"  Resolved exceptions: {kpis.get('exceptions_resolved', 0)}",
        f"  Journal entries: {kpis.get('journal_count', 0)} total, {kpis.get('journals_pending_review', 0)} pending review",
        f"  Documents: {kpis.get('documents_uploaded', 0)} uploaded, {kpis.get('documents_processed', 0)} processed, {kpis.get('documents_failed', 0)} failed",
        f"  Schedule generated: {'Yes' if kpis.get('schedule_generated') else 'No'}",
        f"  Commentary generated: {'Yes' if kpis.get('commentary_generated') else 'No'}",
        f"  Review status: {kpis.get('review_status', 'unknown')}",
    ]

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return "\n".join(lines)


async def lookup_bond(
    query: str,
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Look up a specific bond by ID, ISIN, or issuer/description keyword search.

    :param query: Bond ID (e.g. BOND-001), ISIN (e.g. SG7M18000000), or search text
    :return: Bond details including face value, market value, coupon, maturity, and status
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Looking up bond data...", "done": False}})

    uid = _user_id(__user__)
    bonds = await finance_service.list_bonds(uid, search=query)

    if not bonds:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return f"No bonds found matching '{query}'."

    results = []
    for b in bonds:
        results.append(
            f"Bond: {b['id']} | ISIN: {b['isin']}\n"
            f"  Issuer: {b['issuer']}\n"
            f"  Description: {b['description']}\n"
            f"  Currency: {b['currency']}\n"
            f"  Face value: {_fmt_sgd(b.get('face_value'))}\n"
            f"  Market value: {_fmt_sgd(b.get('market_value'))}\n"
            f"  Coupon rate: {b.get('coupon_rate', 'N/A')}%\n"
            f"  Maturity date: {b.get('maturity_date', 'N/A')}\n"
            f"  Amortised cost: {_fmt_sgd(b.get('amortised_cost'))}\n"
            f"  Accrued interest: {_fmt_sgd(b.get('accrued_interest'))}\n"
            f"  Fair value: {_fmt_sgd(b.get('fair_value'))}\n"
            f"  Source: {b.get('source', 'N/A')}\n"
            f"  Status: {b.get('status', 'N/A')}"
        )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return f"Found {len(bonds)} bond(s):\n\n" + "\n\n".join(results)


async def get_reconciliation_status(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Get the reconciliation summary for the current period including match rate,
    exception count, and value differences between Bloomberg and custodian.

    :return: Reconciliation summary text with match percentages and value differences
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching reconciliation status...", "done": False}})

    uid = _user_id(__user__)
    summary = await finance_service.get_reconciliation_summary(uid)

    lines = [
        f"Reconciliation Summary - Period {summary.get('period_id', 'N/A')}",
        f"  Total bonds: {summary.get('total_bonds', 0)}",
        f"  Matched: {summary.get('matched', 0)}",
        f"  Exceptions: {summary.get('exceptions', 0)}",
        f"  Match rate: {_fmt_pct(summary.get('match_rate', 0))}",
        "",
        "  Face Value Comparison:",
        f"    Bloomberg: {_fmt_sgd(summary.get('total_face_value_bloomberg'))}",
        f"    Custodian: {_fmt_sgd(summary.get('total_face_value_custodian'))}",
        f"    Difference: {_fmt_sgd(summary.get('total_face_value_diff'))}",
        "",
        "  Market Value Comparison:",
        f"    Bloomberg: {_fmt_sgd(summary.get('total_market_value_bloomberg'))}",
        f"    Custodian: {_fmt_sgd(summary.get('total_market_value_custodian'))}",
        f"    Difference: {_fmt_sgd(summary.get('total_market_value_diff'))}",
    ]

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return "\n".join(lines)


async def get_open_exceptions(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    List all open (unresolved) reconciliation exceptions with their severity,
    type, bond details, and value differences.

    :return: List of open exceptions with severity and amounts
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching open exceptions...", "done": False}})

    uid = _user_id(__user__)
    exceptions = await finance_service.get_exceptions(uid, exc_status="open")

    if not exceptions:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return "No open exceptions found."

    results = []
    for exc in exceptions:
        results.append(
            f"Exception: {exc['id']} | Severity: {exc.get('severity', 'N/A').upper()}\n"
            f"  Bond: {exc.get('bond_id', 'N/A')} | ISIN: {exc.get('isin', 'N/A')}\n"
            f"  Type: {exc.get('exception_type', 'N/A')}\n"
            f"  Description: {exc.get('description', 'N/A')}\n"
            f"  Bloomberg value: {_fmt_sgd(exc.get('bloomberg_value'))}\n"
            f"  Custodian value: {_fmt_sgd(exc.get('custodian_value'))}\n"
            f"  Difference: {_fmt_sgd(exc.get('difference'))}\n"
            f"  Assigned to: {exc.get('assigned_to') or 'Unassigned'}"
        )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return f"Open Exceptions ({len(exceptions)}):\n\n" + "\n\n".join(results)


async def get_pending_reviews(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    List items currently pending human review or approval, including journals
    and commentary awaiting sign-off.

    :return: List of pending review items with type, title, and submission date
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching pending reviews...", "done": False}})

    uid = _user_id(__user__)
    reviews = await finance_service.get_pending_reviews(uid)

    if not reviews:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return "No items pending review."

    results = []
    for rev in reviews:
        results.append(
            f"Review: {rev['id']}\n"
            f"  Type: {rev.get('output_type', 'N/A')}\n"
            f"  Output ID: {rev.get('output_id', 'N/A')}\n"
            f"  Title: {rev.get('title', 'N/A')}\n"
            f"  Submitted by: {rev.get('submitted_by', 'N/A')}\n"
            f"  Submitted at: {rev.get('submitted_at', 'N/A')}"
        )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return f"Pending Reviews ({len(reviews)}):\n\n" + "\n\n".join(results)


async def get_period_movements(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Get bond movements for the current reporting period including purchases,
    sales, maturities, coupon receipts, and transfers with settlement details.

    :return: List of period movements with type, amounts, and status
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching period movements...", "done": False}})

    uid = _user_id(__user__)
    movements = await finance_service.get_movements(uid)

    if not movements:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return "No movements found for the current period."

    # Group by type for summary
    type_counts: dict[str, int] = {}
    results = []
    for mov in movements:
        mtype = mov.get("movement_type", "unknown")
        type_counts[mtype] = type_counts.get(mtype, 0) + 1
        results.append(
            f"Movement: {mov['id']} | Type: {mtype}\n"
            f"  Bond: {mov.get('bond_id', 'N/A')} | ISIN: {mov.get('isin', 'N/A')}\n"
            f"  Trade date: {mov.get('trade_date', 'N/A')}\n"
            f"  Settlement date: {mov.get('settlement_date', 'N/A')}\n"
            f"  Face value: {_fmt_sgd(mov.get('face_value'))}\n"
            f"  Settlement amount: {_fmt_sgd(mov.get('settlement_amount'))}\n"
            f"  Status: {mov.get('status', 'N/A')}\n"
            f"  Classification confidence: {_fmt_pct(mov.get('classification_confidence', 0) * 100) if mov.get('classification_confidence') is not None else 'N/A'}"
        )

    summary_parts = [f"{count} {mtype}(s)" for mtype, count in type_counts.items()]
    header = f"Period Movements ({len(movements)} total: {', '.join(summary_parts)}):"

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return header + "\n\n" + "\n\n".join(results)


async def get_journal_status(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Get journal entries status for the current period including pending,
    approved, and rejected journals with total debit/credit amounts.

    :return: Journal status summary with entry details and amounts in SGD
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching journal status...", "done": False}})

    uid = _user_id(__user__)
    journals = await finance_service.list_journals(uid)

    if not journals:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return "No journal entries found."

    # Count by status
    status_counts: dict[str, int] = {}
    total_debit = 0.0
    total_credit = 0.0
    results = []
    for jrnl in journals:
        status = jrnl.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        total_debit += jrnl.get("total_debit", 0) or 0
        total_credit += jrnl.get("total_credit", 0) or 0

        results.append(
            f"Journal: {jrnl['id']} | Type: {jrnl.get('journal_type', 'N/A')}\n"
            f"  Description: {jrnl.get('description', 'N/A')}\n"
            f"  Status: {status}\n"
            f"  Total debit: {_fmt_sgd(jrnl.get('total_debit'))}\n"
            f"  Total credit: {_fmt_sgd(jrnl.get('total_credit'))}\n"
            f"  Created by: {jrnl.get('created_by', 'N/A')}\n"
            f"  Approved by: {jrnl.get('approved_by') or 'Pending'}"
        )

    status_parts = [f"{count} {status}" for status, count in status_counts.items()]
    header = (
        f"Journal Status ({len(journals)} entries: {', '.join(status_parts)})\n"
        f"  Total debits: {_fmt_sgd(total_debit)}\n"
        f"  Total credits: {_fmt_sgd(total_credit)}"
    )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return header + "\n\n" + "\n\n".join(results)


async def get_audit_progress(
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Get audit schedule completion status including bonds covered, classification
    breakdown, impairment staging, and ECL provisions.

    :return: Audit progress summary with coverage and provision details
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Fetching audit progress...", "done": False}})

    uid = _user_id(__user__)
    schedule = await finance_service.get_audit_schedule(uid)

    if not schedule:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return "No audit schedule data available."

    total_face = sum(item.get("face_value", 0) or 0 for item in schedule)
    total_ecl = sum(item.get("ecl_provision", 0) or 0 for item in schedule)
    classifications = {}
    stages = {}
    recon_statuses = {}

    results = []
    for item in schedule:
        cls = item.get("classification", "unknown")
        classifications[cls] = classifications.get(cls, 0) + 1
        stage = item.get("impairment_stage", "unknown")
        stages[stage] = stages.get(stage, 0) + 1
        rs = item.get("reconciliation_status", "unknown")
        recon_statuses[rs] = recon_statuses.get(rs, 0) + 1

        results.append(
            f"Audit: {item['id']} | Bond: {item.get('bond_id', 'N/A')}\n"
            f"  ISIN: {item.get('isin', 'N/A')}\n"
            f"  Description: {item.get('description', 'N/A')}\n"
            f"  Face value: {_fmt_sgd(item.get('face_value'))}\n"
            f"  Amortised cost: {_fmt_sgd(item.get('amortised_cost'))}\n"
            f"  Fair value: {_fmt_sgd(item.get('fair_value'))}\n"
            f"  Classification: {cls}\n"
            f"  Impairment stage: {stage}\n"
            f"  ECL provision: {_fmt_sgd(item.get('ecl_provision'))}\n"
            f"  Reconciliation: {rs}\n"
            f"  Last audit: {item.get('last_audit_date', 'N/A')}"
        )

    cls_parts = [f"{count} {cls}" for cls, count in classifications.items()]
    stage_parts = [f"{count} {stage}" for stage, count in stages.items()]

    header = (
        f"Audit Schedule Progress ({len(schedule)} bonds covered)\n"
        f"  Total face value: {_fmt_sgd(total_face)}\n"
        f"  Total ECL provision: {_fmt_sgd(total_ecl)}\n"
        f"  Classifications: {', '.join(cls_parts)}\n"
        f"  Impairment stages: {', '.join(stage_parts)}"
    )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return header + "\n\n" + "\n\n".join(results)


async def generate_analysis(
    topic: str,
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Retrieve AI-generated commentary and analysis for a specific topic area
    such as portfolio overview, movement analysis, or reconciliation summary.

    :param topic: Analysis topic - e.g. "portfolio overview", "movement analysis", "reconciliation", "risk"
    :return: AI-generated commentary text for the requested topic
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": f"Generating analysis for '{topic}'...", "done": False}})

    uid = _user_id(__user__)
    commentaries = await finance_service.get_commentary(uid)

    if not commentaries:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return "No commentary data available. Commentary may not have been generated for the current period yet."

    # Try to match the topic to a commentary section
    topic_lower = topic.lower()
    matched = []
    for c in commentaries:
        section = (c.get("section") or "").lower()
        title = (c.get("title") or "").lower()
        content = c.get("content", "")
        if topic_lower in section or topic_lower in title or any(word in section or word in title for word in topic_lower.split()):
            matched.append(c)

    if not matched:
        # Return all available commentary if no match
        matched = commentaries

    results = []
    for c in matched:
        results.append(
            f"--- {c.get('title', 'Untitled')} ---\n"
            f"Section: {c.get('section', 'N/A')}\n"
            f"Status: {c.get('status', 'N/A')}\n"
            f"Generated by: {c.get('generated_by', 'N/A')}\n"
            f"Approved by: {c.get('approved_by') or 'Pending'}\n\n"
            f"{c.get('content', 'No content available.')}"
        )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return "\n\n".join(results)


async def search_audit_trail(
    query: str,
    __user__: dict = None,
    __event_emitter__=None,
) -> str:
    """
    Search the audit trail for specific actions, entities, or users.
    Returns a chronological log of matching activities.

    :param query: Search text to filter audit entries - matches action types, entity types, user names, or details
    :return: Matching audit trail entries with timestamps and details
    """
    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Searching audit trail...", "done": False}})

    uid = _user_id(__user__)

    # The finance service supports filtering by action_filter and entity_type.
    # We pass the query as action_filter for partial matching, and also fetch
    # all entries to do a broader text search.
    all_entries = await finance_service.get_audit_trail(uid)

    # Filter entries matching the query across multiple fields
    query_lower = query.lower()
    matched = [
        entry for entry in all_entries
        if query_lower in (entry.get("action") or "").lower()
        or query_lower in (entry.get("entity_type") or "").lower()
        or query_lower in (entry.get("user_name") or "").lower()
        or query_lower in (entry.get("details") or "").lower()
        or query_lower in (entry.get("entity_id") or "").lower()
    ]

    if not matched:
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})
        return f"No audit trail entries found matching '{query}'."

    results = []
    for entry in matched:
        results.append(
            f"[{entry.get('timestamp', 'N/A')}] {entry.get('action', 'N/A')}\n"
            f"  User: {entry.get('user_name', 'N/A')} ({entry.get('user_id', 'N/A')})\n"
            f"  Entity: {entry.get('entity_type', 'N/A')} / {entry.get('entity_id', 'N/A')}\n"
            f"  Details: {entry.get('details', 'N/A')}"
        )

    if __event_emitter__:
        await __event_emitter__({"type": "status", "data": {"description": "Done", "done": True}})

    return f"Audit Trail ({len(matched)} entries matching '{query}'):\n\n" + "\n\n".join(results)
