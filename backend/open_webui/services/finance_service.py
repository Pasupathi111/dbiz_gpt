"""
Finance service module for Bond Copilot.

Real ORM-backed implementations for reporting periods, documents, bond records,
reconciliation, movements, schedule, journals, audit schedule, commentary,
review/approval and audit-trail.
"""

import csv
import io
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_db_context
from open_webui.services import finance_ingestion
from open_webui.models.finance import (
    AuditScheduleEntries,
    AuditScheduleEntryForm,
    BondMovements,
    BondMovementForm,
    BondRecords,
    BondRecordForm,
    BondScheduleLines,
    BondScheduleLineForm,
    BondSourceRecords,
    BondSourceRecordForm,
    Commentaries,
    CommentaryForm,
    ExtractionJobForm,
    ExtractionJobs,
    FinanceApprovals,
    FinanceApprovalForm,
    FinanceAuditLogs,
    FinanceAuditLogForm,
    FinanceDocumentForm,
    FinanceDocuments,
    FinanceExceptionForm,
    FinanceExceptions,
    JournalForm,
    JournalLineForm,
    JournalLines,
    Journals,
    ReconciliationItemForm,
    ReconciliationItems,
    ReconciliationRunForm,
    ReconciliationRuns,
    ReportingPeriodForm,
    ReportingPeriods,
    SourceReferenceForm,
    SourceReferences,
)

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ms() -> int:
    return int(time.time())


def _new_id() -> str:
    return str(uuid.uuid4())


def _to_dict(model) -> dict:
    return model.model_dump() if model is not None else None


def _to_list_of_dicts(models) -> list[dict]:
    return [m.model_dump() for m in models]


def _require_approve(user=None) -> None:
    """Defense-in-depth RBAC guard at service layer.

    The router already enforces the primary gate via has_permission + admin
    short-circuit.  This second-layer check exists so that anyone calling the
    service functions directly (e.g. tests, internal tooling, future imports)
    cannot bypass the Human-in-the-Loop approval constraint.  Only callers
    that explicitly pass a user with `role == 'admin'` are authorised.  The
    router always passes `user`, so an omitted `user` means this is being
    called from somewhere that bypassed the router-level gate — deny by
    default rather than assume that gate already ran.
    """
    role = getattr(user, "role", None) if user is not None else None
    if role != "admin":
        raise PermissionError(
            f"Finance approval rejected for user role={role!r}: "
            f"HITL requires admin or explicit finance.approve permission"
        )


async def _llm_chat(
    prompt: str,
    system_prompt: Optional[str] = None,
    *,
    temperature: float = 0.3,
    max_tokens: int = 1200,
    timeout_s: float = 30.0,
) -> Optional[str]:
    """Best-effort LLM chat completion for finance commentary.

    Supports any OpenAI-compatible provider (OpenAI API keys, or local Ollama
    `/v1/chat/completions` endpoint).  Returns ``None`` if the environment is
    not configured, the HTTP call fails, or the response body cannot be parsed
    — in those cases the caller falls back to the structured DB-aggregate text
    so the UI is never left with empty or broken content.
    """
    try:
        import httpx  # noqa: F401 — already used by MCP client; imported lazily to reduce module import cost
    except Exception:
        return None

    # Resolve provider configuration the same way the rest of Open WebUI does.
    from open_webui.config import OPENAI_API_BASE_URL, OPENAI_API_KEY, OLLAMA_BASE_URLS, Config

    api_base = None
    api_key = None
    model = None

    # 1. OpenAI-compatible (primary path): env vars or Config settings
    try:
        cfg_key = await Config.get("openai.api_key", "") if callable(getattr(Config, "get", None)) else ""
    except Exception:
        cfg_key = ""
    try:
        cfg_base = await Config.get("openai.api_base_url", "") if callable(getattr(Config, "get", None)) else ""
    except Exception:
        cfg_base = ""

    api_key = OPENAI_API_KEY or cfg_key or ""
    api_base = OPENAI_API_BASE_URL or cfg_base or ""
    try:
        cfg_model = await Config.get("openai.api_model", "") if callable(getattr(Config, "get", None)) else ""
    except Exception:
        cfg_model = ""
    model = cfg_model or "gpt-4o-mini"

    # 2. Ollama fallback: /v1 emulation endpoint if no OpenAI key configured
    if not api_base and OLLAMA_BASE_URLS:
        first = OLLAMA_BASE_URLS[0] if isinstance(OLLAMA_BASE_URLS, list) else str(OLLAMA_BASE_URLS)
        api_base = f"{first.rstrip('/')}/v1"
        api_key = api_key or "ollama"
        if not cfg_model:
            model = "llama3.1:8b"

    if not api_base:
        return None

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    endpoint = api_base.rstrip("/") + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s, connect=10.0)) as client:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = await client.post(
                endpoint,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
    except Exception:
        return None

    if resp.status_code != 200:
        return None
    try:
        payload = resp.json()
        return (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


async def get_dashboard(user_id: str, period_id: Optional[str] = None) -> dict:
    """Return KPI data for the current (or specified) reporting period."""
    period = None
    if period_id:
        period = await ReportingPeriods.get_by_id(period_id)
    if period is None:
        all_periods = await ReportingPeriods.get_all()
        period = all_periods[0] if all_periods else None

    resolved_id = period.id if period else (period_id or "")
    resolved_name = period.name if period else (period_id or "")

    total_bonds = await BondRecords.count_by_period(resolved_id) if resolved_id else 0
    total_face_value = 0.0
    total_book_value = 0.0
    total_market_value = 0.0
    status_counts: dict[str, int] = {}

    if resolved_id:
        bonds = await BondRecords.get_by_period(resolved_id)
        total_face_value = sum((b.face_value or 0.0) for b in bonds)
        total_book_value = sum((b.book_value or 0.0) for b in bonds)
        total_market_value = sum((b.market_value or 0.0) for b in bonds)
        for b in bonds:
            s = b.status or "unknown"
            status_counts[s] = status_counts.get(s, 0) + 1

    docs = await FinanceDocuments.get_by_period(resolved_id) if resolved_id else []
    docs_processed = sum(1 for d in docs if d.status in {"EXTRACTED", "VALIDATED"})
    docs_failed = sum(1 for d in docs if d.status == "FAILED")
    docs_pending = sum(1 for d in docs if d.status in {"UPLOADED", "QUEUED", "PROCESSING"})

    journals = await Journals.get_by_period(resolved_id) if resolved_id else []
    journals_approved = sum(1 for j in journals if j.status == "APPROVED")
    journals_pending = sum(1 for j in journals if j.status in {"PENDING", "SUBMITTED"})

    exceptions = await FinanceExceptions.get_by_period(resolved_id) if resolved_id else []
    exceptions_open = sum(1 for e in exceptions if e.status == "OPEN")
    exceptions_resolved = sum(1 for e in exceptions if e.status in {"RESOLVED", "CLOSED"})

    recon_items = await ReconciliationItems.get_by_run_period(resolved_id) if resolved_id else []
    matched = sum(1 for r in recon_items if r.status == "MATCHED")
    total_recon = len(recon_items) or 1
    match_rate = round(matched / total_recon * 100.0, 1) if recon_items else 0.0

    schedule_entries = await AuditScheduleEntries.get_by_period(resolved_id) if resolved_id else []
    commentary_entries = await Commentaries.get_by_period(resolved_id) if resolved_id else []
    movements = await BondMovements.get_by_period(resolved_id) if resolved_id else []

    approvals = await FinanceApprovals.get_by_period(resolved_id) if resolved_id else []
    if approvals:
        review_status = "completed" if all(a.action == "APPROVED" for a in approvals if a.object_type == "PERIOD") else "in_progress"
    elif period and period.status in {"FINALIZED", "REVIEW"}:
        review_status = "completed" if period.status == "FINALIZED" else "in_progress"
    else:
        review_status = "draft"

    return {
        "period_id": resolved_id,
        "period_name": resolved_name,
        "kpis": {
            "total_bonds": total_bonds,
            "total_face_value": total_face_value,
            "total_book_value": total_book_value,
            "total_market_value": total_market_value,
            "recon_rate": match_rate,
            "reconciled_count": status_counts.get("reconciled", 0) or matched,
            "exceptions_open": exceptions_open,
            "exceptions_resolved": exceptions_resolved,
            "journal_count": len(journals),
            "journals_pending_review": journals_pending,
            "journals_approved": journals_approved,
            "documents_uploaded": len(docs),
            "documents_processed": docs_processed,
            "documents_failed": docs_failed,
            "documents_pending": docs_pending,
            "schedule_generated": len(schedule_entries) > 0,
            "commentary_generated": len(commentary_entries) > 0,
            "movements_count": len(movements),
            "review_status": review_status,
        },
        "generated_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# Reporting Periods
# ---------------------------------------------------------------------------


async def list_periods(user_id: str) -> list[dict]:
    periods = await ReportingPeriods.get_all()
    return _to_list_of_dicts(periods)


async def create_period(user_id: str, data: dict) -> dict:
    # Accept start_date/end_date from router form, map to year/month if provided.
    payload = {**data}
    if "start_date" in payload and "year" not in payload:
        try:
            y = int(str(payload["start_date"]).split("-")[0])
            m = int(str(payload["start_date"]).split("-")[1])
            payload.setdefault("year", y)
            payload.setdefault("month", m)
        except (ValueError, IndexError):
            payload.setdefault("year", 1970)
            payload.setdefault("month", 1)
    form = ReportingPeriodForm(**{
        "name": payload.get("name") or f"Period {payload.get('year', 1970)}-{payload.get('month', 1):02d}",
        "year": int(payload.get("year") or 1970),
        "month": int(payload.get("month") or 1),
        "previous_period_id": payload.get("previous_period_id"),
        "status": payload.get("status") or "DRAFT",
    })
    created = await ReportingPeriods.insert(user_id, form)
    if created is None:
        raise RuntimeError("Failed to create reporting period")
    return _to_dict(created)


async def get_period(user_id: str, period_id: str) -> Optional[dict]:
    period = await ReportingPeriods.get_by_id(period_id)
    if not period:
        return None
    period_d = _to_dict(period)

    docs = await FinanceDocuments.get_by_period(period_id)
    bonds = await BondRecords.get_by_period(period_id)
    journals = await Journals.get_by_period(period_id)
    commentaries = await Commentaries.get_by_period(period_id)
    recon_runs = await ReconciliationRuns.get_by_period(period_id)

    docs_total = len(docs)
    docs_processed = sum(1 for d in docs if d.status in {"EXTRACTED", "VALIDATED"})
    docs_failed = sum(1 for d in docs if d.status == "FAILED")
    docs_pending = docs_total - docs_processed - docs_failed

    journals_total = len(journals)
    journals_approved = sum(1 for j in journals if j.status == "APPROVED")
    journals_pending = sum(1 for j in journals if j.status in {"PENDING", "SUBMITTED"})

    if recon_runs:
        last_run = sorted(recon_runs, key=lambda r: r.created_at, reverse=True)[0]
        recon_stats = {
            "status": last_run.status,
            "match_rate": last_run.match_rate or 0.0,
            "total_bonds": last_run.total_bonds,
            "matched": last_run.matched,
            "variances": last_run.variances,
            "missing": last_run.missing,
        }
    else:
        recon_stats = {"status": "NOT_RUN", "match_rate": 0.0}

    period_d["processing_status"] = {
        "documents": {"total": docs_total, "processed": docs_processed, "failed": docs_failed, "pending": docs_pending},
        "reconciliation": recon_stats,
        "journals": {"total": journals_total, "approved": journals_approved, "pending": journals_pending},
        "schedule": {"status": "generated" if len(bonds) > 0 else "not_generated", "bonds": len(bonds)},
        "commentary": {"status": "generated" if len(commentaries) > 0 else "not_generated", "sections": len(commentaries)},
    }
    return period_d


async def update_period(user_id: str, period_id: str, data: dict) -> Optional[dict]:
    updated = await ReportingPeriods.update_by_id(period_id, data)
    log.info("Updated period %s by user %s", period_id, user_id)
    return _to_dict(updated) if updated else None


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


async def upload_document(
    user_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    document_type: str,
    reporting_period_id: str,
    file_path: str,
    file_hash: Optional[str] = None,
) -> dict:
    form = FinanceDocumentForm(
        reporting_period_id=reporting_period_id,
        document_type=document_type,
        filename=filename,
        original_filename=filename,
        file_path=file_path,
        file_size=file_size,
        file_hash=file_hash,
        mime_type=content_type,
        status="UPLOADED",
    )
    doc = await FinanceDocuments.insert(user_id, form)
    if doc is None:
        raise RuntimeError("Failed to insert document")
    log.info("Uploaded document %s (%s) by user %s", doc.id, filename, user_id)
    return _to_dict(doc)


async def list_documents(
    user_id: str,
    period_id: Optional[str] = None,
    document_type: Optional[str] = None,
    doc_status: Optional[str] = None,
) -> list[dict]:
    if period_id:
        results = await FinanceDocuments.get_by_period(period_id)
    else:
        # Fallback: slow path, scan all docs (no generic get_all available)
        results = []
        for p in await ReportingPeriods.get_all():
            results.extend(await FinanceDocuments.get_by_period(p.id))
    if document_type:
        results = [d for d in results if d.document_type == document_type]
    if doc_status:
        results = [d for d in results if d.status == doc_status]
    return _to_list_of_dicts(results)


async def get_document(user_id: str, doc_id: str) -> Optional[dict]:
    doc = await FinanceDocuments.get_by_id(doc_id)
    return _to_dict(doc) if doc else None


_EXTRACTION_TYPE_BY_DOCUMENT_TYPE = {
    "UBS_EXCEL": "EXCEL",
    "LGI_PDF": "PDF",
}


async def process_document(user_id: str, doc_id: str) -> dict:
    """Run extraction for a document: parse the stored file (UBS Excel /
    LGI PDF) and persist BondRecord + BondSourceRecord rows from it.
    """
    doc = await FinanceDocuments.get_by_id(doc_id)
    if doc is None:
        raise ValueError(f"document {doc_id} not found")

    extraction_type = _EXTRACTION_TYPE_BY_DOCUMENT_TYPE.get(doc.document_type, "GENERIC")
    job_form = ExtractionJobForm(
        document_id=doc.id,
        status="RUNNING",
        extraction_type=extraction_type,
    )
    job = await ExtractionJobs.insert(job_form)
    job_id = job.id if job else _new_id()
    await ExtractionJobs.update_by_id(job_id, {"started_at": _now_ms()})
    await FinanceDocuments.update_by_id(doc.id, {"status": "PROCESSING"})
    log.info("Processing document %s triggered by user %s", doc_id, user_id)

    if doc.document_type not in _EXTRACTION_TYPE_BY_DOCUMENT_TYPE:
        errors = [f"Unsupported document_type for extraction: {doc.document_type}"]
        await ExtractionJobs.update_by_id(
            job_id, {"status": "FAILED", "errors": errors, "completed_at": _now_ms()}
        )
        await FinanceDocuments.update_by_id(
            doc.id,
            {"status": "FAILED", "validation_status": "ERROR", "validation_messages": errors},
        )
        return {
            "task_id": job_id,
            "document_id": doc_id,
            "status": "FAILED",
            "message": errors[0],
            "started_at": _utc_now(),
        }

    try:
        # Imported lazily (like the config import above) to keep this heavy,
        # multi-cloud-SDK-backed module out of finance_service's import cost.
        from open_webui.storage.provider import Storage

        local_path = Storage.get_file(doc.file_path)
        with open(local_path, "rb") as f:
            contents = f.read()
        rows = finance_ingestion.parse_document(doc.document_type, contents)
        records_created, source_type = await _persist_extracted_bond_rows(
            doc, rows
        )

        await ExtractionJobs.update_by_id(
            job_id,
            {
                "status": "COMPLETED",
                "records_extracted": len(rows),
                "completed_at": _now_ms(),
            },
        )
        validation_status = "VALID" if rows else "WARNING"
        validation_messages = None if rows else ["No bond records could be parsed from this file"]
        await FinanceDocuments.update_by_id(
            doc.id,
            {
                "status": "EXTRACTED",
                "validation_status": validation_status,
                "validation_messages": validation_messages,
                "processed_at": _now_ms(),
            },
        )
        log.info(
            "Extracted %s bond record(s) from document %s (source=%s)",
            len(rows), doc_id, source_type,
        )
        return {
            "task_id": job_id,
            "document_id": doc_id,
            "status": "COMPLETED",
            "message": f"Extracted {len(rows)} bond record(s)",
            "records_extracted": len(rows),
            "started_at": _utc_now(),
        }
    except Exception as e:
        log.exception("Extraction failed for document %s: %s", doc_id, e)
        errors = [str(e)]
        await ExtractionJobs.update_by_id(
            job_id, {"status": "FAILED", "errors": errors, "completed_at": _now_ms()}
        )
        await FinanceDocuments.update_by_id(
            doc.id,
            {"status": "FAILED", "validation_status": "ERROR", "validation_messages": errors},
        )
        return {
            "task_id": job_id,
            "document_id": doc_id,
            "status": "FAILED",
            "message": f"Extraction failed: {e}",
            "started_at": _utc_now(),
        }


async def _persist_extracted_bond_rows(doc, rows: list[dict]) -> tuple[int, str]:
    source_type = "UBS" if doc.document_type == "UBS_EXCEL" else "LGI"
    created = 0
    for row in rows:
        bond_id = row.get("bond_id")
        if not bond_id:
            continue

        existing = await BondRecords.get_by_bond_id(bond_id, doc.reporting_period_id)
        existing_same_source = next(
            (r for r in existing if r.source_type == source_type), None
        )

        bond_fields = {
            "reporting_period_id": doc.reporting_period_id,
            "bond_id": bond_id,
            "isin": row.get("isin"),
            "description": row.get("description"),
            "issuer": row.get("issuer"),
            "currency": row.get("currency"),
            "face_value": row.get("face_value"),
            "book_value": row.get("book_value"),
            "market_value": row.get("market_value"),
            "coupon_rate": row.get("coupon_rate"),
            "accrued_interest": row.get("accrued_interest"),
            "maturity_date": row.get("maturity_date"),
            "purchase_date": row.get("purchase_date"),
            "settlement_date": row.get("settlement_date"),
            "quantity": row.get("quantity"),
            "source_document_id": doc.id,
            "source_type": source_type,
            "extraction_confidence": row.get("_confidence"),
        }

        if existing_same_source:
            bond_record_id = existing_same_source.id
            await BondRecords.update_by_id(bond_record_id, bond_fields)
        else:
            form = BondRecordForm(**bond_fields)
            inserted = await BondRecords.insert(form)
            if inserted is None:
                continue
            bond_record_id = inserted.id
            created += 1

        source_form = BondSourceRecordForm(
            bond_record_id=bond_record_id,
            document_id=doc.id,
            source_type=source_type,
            raw_data=row.get("_raw_data") or {},
            sheet_name=row.get("_sheet_name"),
            row_number=row.get("_row_number"),
            page_number=row.get("_page_number"),
            cell_references=row.get("_cell_references"),
            extraction_confidence=row.get("_confidence"),
        )
        await BondSourceRecords.insert(source_form)

    return created, source_type


async def delete_document(user_id: str, doc_id: str) -> bool:
    ok = await FinanceDocuments.delete_by_id(doc_id)
    if ok:
        log.info("Deleted document %s by user %s", doc_id, user_id)
    return ok


# ---------------------------------------------------------------------------
# Bond Records
# ---------------------------------------------------------------------------


async def list_bonds(
    user_id: str,
    period_id: Optional[str] = None,
    source: Optional[str] = None,
    bond_status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    if period_id:
        results = await BondRecords.get_by_period(period_id)
    else:
        results = []
        for p in await ReportingPeriods.get_all():
            results.extend(await BondRecords.get_by_period(p.id))
    if source:
        results = [b for b in results if (b.source_type or "") == source]
    if bond_status:
        results = [b for b in results if (b.status or "") == bond_status]
    if search:
        q = search.lower()
        results = [
            b for b in results
            if q in (b.bond_id or "").lower()
            or q in (b.isin or "").lower()
            or q in (b.issuer or "").lower()
            or q in (b.description or "").lower()
        ]
    return _to_list_of_dicts(results)


async def get_bond(user_id: str, bond_id: str) -> Optional[dict]:
    bond = await BondRecords.get_by_id(bond_id)
    if not bond:
        return None
    return _to_dict(bond)


async def update_bond(user_id: str, bond_id: str, data: dict) -> Optional[dict]:
    updated = await BondRecords.update_by_id(bond_id, data)
    log.info("Updated bond %s by user %s", bond_id, user_id)
    return _to_dict(updated) if updated else None


async def get_bond_sources(user_id: str, bond_id: str) -> list[dict]:
    # Join through BondSourceRecords filtered by bond_record_id = bond_id
    sources = await BondSourceRecords.get_by_bond_record(bond_id)
    out = []
    for s in sources:
        out.append({
            "id": s.id,
            "bond_id": bond_id,
            "source": s.source_type,
            "raw_data": s.raw_data,
            "face_value": (s.raw_data or {}).get("face_value") if isinstance(s.raw_data, dict) else None,
            "market_value": (s.raw_data or {}).get("market_value") if isinstance(s.raw_data, dict) else None,
            "accrued_interest": (s.raw_data or {}).get("accrued_interest") if isinstance(s.raw_data, dict) else None,
            "extracted_from": s.document_id,
            "extracted_at": datetime.fromtimestamp(s.created_at, tz=timezone.utc).isoformat() if s.created_at else None,
            "sheet_name": s.sheet_name,
            "row_number": s.row_number,
            "page_number": s.page_number,
            "extraction_confidence": s.extraction_confidence,
        })
    return out


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


_RECON_SOURCE_ALIASES = {
    "UBS": {"ubs", "ubs_excel", "bloomberg"},
    "LGI": {"lgi", "lgi_pdf", "custodian"},
    "SCHEDULE": {"schedule", "previous_schedule"},
}


async def run_reconciliation(user_id: str, period_id: str) -> dict:
    # Re-running reconciliation for a period replaces the prior run's rows
    # rather than accumulating alongside them (items are read joined across
    # all runs for a period via get_by_run_period).
    for prior_run in await ReconciliationRuns.get_by_period(period_id):
        await ReconciliationItems.delete_by_run(prior_run.id)
    await ReconciliationRuns.delete_by_period(period_id)

    bonds = await BondRecords.get_by_period(period_id)

    # Ingestion persists one BondRecord *per source* per bond_id (a UBS-sourced
    # row and an LGI-sourced row are separate rows, each source_type-tagged —
    # see _persist_extracted_bond_rows). So the 3-way reconciliation groups by
    # bond_id across those rows rather than treating each BondRecord as a
    # single bond with multiple attached BondSourceRecords.
    by_bond_id: dict[str, dict[str, Any]] = {}
    for b in bonds:
        key = b.bond_id or b.id
        group = by_bond_id.setdefault(key, {"isin": b.isin})
        source_type = (b.source_type or "").lower()
        for canonical, aliases in _RECON_SOURCE_ALIASES.items():
            if source_type in aliases and canonical not in group:
                group[canonical] = b
        group["isin"] = group.get("isin") or b.isin

    form = ReconciliationRunForm(
        reporting_period_id=period_id,
        status="RUNNING",
        total_bonds=len(by_bond_id),
        matched=0,
        variances=0,
        missing=0,
        duplicates=0,
        match_rate=0.0,
        run_by=user_id,
        started_at=_now_ms(),
    )
    run = await ReconciliationRuns.insert(form)
    if run is None:
        raise RuntimeError("Failed to create reconciliation run")

    matched = 0
    variances = 0
    missing = 0
    items_to_insert: list[ReconciliationItemForm] = []

    for bond_id, group in by_bond_id.items():
        ubs: Optional[Any] = group.get("UBS")
        lgi: Optional[Any] = group.get("LGI")
        schedule: Optional[Any] = group.get("SCHEDULE")

        ubs_value = ubs.market_value if ubs else None
        lgi_value = lgi.market_value if lgi else None
        schedule_value = schedule.market_value if schedule else None

        is_missing = ubs is None or lgi is None
        variance_amount = 0.0
        variance_percent = 0.0
        if not is_missing:
            variance_amount = float(ubs_value or 0) - float(lgi_value or 0)
            variance_percent = (
                (variance_amount / float(ubs_value) * 100.0) if abs(float(ubs_value or 0)) > 1e-9 else 0.0
            )

        if is_missing:
            missing += 1
            status = "MISSING_SOURCE"
        elif abs(variance_amount) < 0.01:
            matched += 1
            status = "MATCHED"
        else:
            variances += 1
            status = "VARIANCE"

        items_to_insert.append(ReconciliationItemForm(
            reconciliation_run_id=run.id,
            bond_id=bond_id,
            isin=group.get("isin"),
            status=status,
            ubs_value=float(ubs_value) if ubs_value is not None else None,
            lgi_value=float(lgi_value) if lgi_value is not None else None,
            schedule_value=float(schedule_value) if schedule_value is not None else None,
            previous_value=None,
            variance_amount=float(variance_amount),
            variance_percentage=float(variance_percent),
            field_name="market_value",
            reason="Missing UBS or LGI source" if is_missing else "reconciliation diff",
            ai_explanation=None,
        ))

    for item_form in items_to_insert:
        await ReconciliationItems.insert(item_form)

    duplicates = 0
    total_for_rate = max(matched + variances + missing, 1)
    match_rate = round(matched / total_for_rate * 100.0, 1)

    completed = await ReconciliationRuns.update_by_id(run.id, {
        "status": "COMPLETED",
        "matched": matched,
        "variances": variances,
        "missing": missing,
        "duplicates": duplicates,
        "match_rate": match_rate,
        "completed_at": _now_ms(),
    })

    return {
        "task_id": run.id,
        "period_id": period_id,
        "status": completed.status if completed else "COMPLETED",
        "total_bonds": len(by_bond_id),
        "matched": matched,
        "variances": variances,
        "missing": missing,
        "match_rate": match_rate,
        "message": "Reconciliation completed",
        "started_at": datetime.fromtimestamp(run.started_at, tz=timezone.utc).isoformat(),
    }


async def get_reconciliation_results(
    user_id: str,
    period_id: Optional[str] = None,
    recon_status: Optional[str] = None,
) -> list[dict]:
    items = await ReconciliationItems.get_by_run_period(period_id) if period_id else await ReconciliationItems.get_all()
    if recon_status:
        items = [i for i in items if i.status == recon_status]
    return _to_list_of_dicts(items)


async def get_reconciliation_summary(user_id: str, period_id: Optional[str] = None) -> dict:
    runs = await ReconciliationRuns.get_by_period(period_id) if period_id else []
    items = await ReconciliationItems.get_by_run_period(period_id) if period_id else await ReconciliationItems.get_all()
    last_run = sorted(runs, key=lambda r: r.created_at, reverse=True)[0] if runs else None

    total_ubs = sum(float(i.ubs_value or 0) for i in items)
    total_lgi = sum(float(i.lgi_value or 0) for i in items)
    total_schedule = sum(float(i.schedule_value or 0) for i in items)
    matched = sum(1 for i in items if i.status == "MATCHED")
    exceptions = sum(1 for i in items if i.status in {"VARIANCE", "MISSING_SOURCE"})
    total_items = len(items)
    match_rate = round(matched / total_items * 100.0, 1) if total_items else 0.0

    return {
        "period_id": period_id or "",
        "run_id": last_run.id if last_run else None,
        "run_status": last_run.status if last_run else "NOT_RUN",
        "total_bonds": total_items,
        "matched": matched,
        "exceptions": exceptions,
        "match_rate": match_rate,
        "total_face_value_bloomberg": total_ubs,
        "total_face_value_custodian": total_lgi,
        "total_face_value_diff": round(total_ubs - total_lgi, 2),
        "total_schedule_value": total_schedule,
        "generated_at": _utc_now(),
    }


async def get_exceptions(
    user_id: str,
    period_id: Optional[str] = None,
    exc_status: Optional[str] = None,
) -> list[dict]:
    excs = await FinanceExceptions.get_by_period(period_id) if period_id else await FinanceExceptions.get_all()
    if exc_status:
        excs = [e for e in excs if e.status == exc_status]
    return _to_list_of_dicts(excs)


async def update_exception(user_id: str, exception_id: str, data: dict) -> Optional[dict]:
    updated = await FinanceExceptions.update_by_id(exception_id, data)
    log.info("Updated exception %s by user %s", exception_id, user_id)
    return _to_dict(updated) if updated else None


# ---------------------------------------------------------------------------
# Movements
# ---------------------------------------------------------------------------


async def analyze_movements(user_id: str, period_id: str) -> dict:
    """Compare current period bonds vs previous period and populate BondMovements table."""
    current = await ReportingPeriods.get_by_id(period_id)
    if not current:
        raise ValueError(f"period {period_id} not found")

    previous_period_id = current.previous_period_id
    curr_bonds = {b.bond_id or b.id: b for b in await BondRecords.get_by_period(period_id)}
    prev_bonds: dict = {}
    if previous_period_id:
        prev_bonds = {b.bond_id or b.id: b for b in await BondRecords.get_by_period(previous_period_id)}

    all_bond_keys = set(curr_bonds.keys()) | set(prev_bonds.keys())
    created_movements: list[dict] = []

    for key in all_bond_keys:
        curr = curr_bonds.get(key)
        prev = prev_bonds.get(key)
        if curr and prev:
            for field in ("face_value", "book_value", "market_value", "accrued_interest"):
                cv = float(getattr(curr, field) or 0)
                pv = float(getattr(prev, field) or 0)
                if abs(cv - pv) > 0.01:
                    movement_type = {
                        "face_value": "position_change",
                        "book_value": "amortisation",
                        "market_value": "fair_value_change",
                        "accrued_interest": "accrual",
                    }[field]
                    form = BondMovementForm(
                        reporting_period_id=period_id,
                        bond_id=curr.bond_id or curr.id,
                        isin=curr.isin,
                        movement_type=movement_type.upper(),
                        previous_value=pv,
                        current_value=cv,
                        variance=round(cv - pv, 2),
                        previous_status=prev.status or "DRAFT",
                        current_status=curr.status or "DRAFT",
                        ai_explanation=f"auto-movement: {field} changed from {pv:.2f} to {cv:.2f}",
                        explanation_confidence=0.8,
                    )
                    mv = await BondMovements.insert(form)
                    if mv:
                        created_movements.append(_to_dict(mv))
        elif curr and not prev:
            form = BondMovementForm(
                reporting_period_id=period_id,
                bond_id=curr.bond_id or curr.id,
                isin=curr.isin,
                movement_type="PURCHASE",
                previous_value=0.0,
                current_value=float(curr.face_value or 0),
                variance=float(curr.face_value or 0),
                previous_status="NON_EXISTENT",
                current_status=curr.status or "DRAFT",
                ai_explanation="new bond in period, interpreted as purchase",
                explanation_confidence=0.7,
            )
            mv = await BondMovements.insert(form)
            if mv:
                created_movements.append(_to_dict(mv))
        else:  # prev but no current
            assert prev is not None
            prev_status = (prev.status or "").upper()
            # Prefer the bond's own recorded status (set via bond review/HITL,
            # e.g. PUT /bonds/{id}) to tell a sale/transfer apart from a
            # genuine maturity when a bond drops out of the current period.
            if prev_status == "SOLD":
                movement_type = "SALE"
                current_status = "SOLD"
                explanation = "bond marked SOLD in prior period and no longer present, interpreted as sale"
            elif prev_status == "TRANSFERRED":
                movement_type = "TRANSFER"
                current_status = "TRANSFERRED"
                explanation = "bond marked TRANSFERRED in prior period and no longer present, interpreted as transfer"
            else:
                movement_type = "MATURITY"
                current_status = "RETIRED"
                explanation = "bond removed in current period, interpreted as maturity/sale"
            form = BondMovementForm(
                reporting_period_id=period_id,
                bond_id=prev.bond_id or prev.id,
                isin=prev.isin,
                movement_type=movement_type,
                previous_value=float(prev.face_value or 0),
                current_value=0.0,
                variance=-1 * float(prev.face_value or 0),
                previous_status=prev.status or "DRAFT",
                current_status=current_status,
                ai_explanation=explanation,
                explanation_confidence=0.6,
            )
            mv = await BondMovements.insert(form)
            if mv:
                created_movements.append(_to_dict(mv))

    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "completed",
        "movements_created": len(created_movements),
        "movements": created_movements,
        "message": "Movement analysis completed",
        "started_at": _utc_now(),
    }


async def get_movements(
    user_id: str,
    period_id: Optional[str] = None,
    movement_type: Optional[str] = None,
) -> list[dict]:
    if period_id:
        results = await BondMovements.get_by_period(period_id)
    else:
        results = await BondMovements.get_all()
    if movement_type:
        results = [m for m in results if m.movement_type == movement_type.upper()]
    return _to_list_of_dicts(results)


async def update_movement(user_id: str, movement_id: str, data: dict) -> Optional[dict]:
    updated = await BondMovements.update_by_id(movement_id, data)
    log.info("Updated movement %s by user %s", movement_id, user_id)
    return _to_dict(updated) if updated else None


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


async def generate_schedule(user_id: str, period_id: str) -> dict:
    """Populate BondScheduleLines table from current period bond records.

    movement_type/variance are derived against the previous period's bond
    (by bond_id) so validate_schedule's roll-forward check — which
    reconstructs previous_value as market_value - variance — has a real
    variance to check rather than always seeing 0.
    """
    bonds = await BondRecords.get_by_period(period_id)

    current_period = await ReportingPeriods.get_by_id(period_id)
    prev_bonds_by_id: dict[str, Any] = {}
    if current_period and current_period.previous_period_id:
        prev_bonds_by_id = {
            (b.bond_id or b.id): b
            for b in await BondRecords.get_by_period(current_period.previous_period_id)
        }

    created_count = 0
    for b in bonds:
        bond_key = b.bond_id or b.id
        prev = prev_bonds_by_id.get(bond_key)
        current_value = float(b.market_value or 0)
        if prev is None:
            movement_type = "NEW"
            variance = current_value
        else:
            previous_value = float(prev.market_value or 0)
            variance = round(current_value - previous_value, 2)
            movement_type = "UNCHANGED" if abs(variance) < 0.01 else "VALUE_CHANGE"

        form = BondScheduleLineForm(
            reporting_period_id=period_id,
            bond_id=bond_key,
            isin=b.isin,
            issuer=b.issuer,
            currency=b.currency,
            face_value=float(b.face_value or 0),
            book_value=float(b.book_value or 0),
            market_value=float(b.market_value or 0),
            coupon_rate=float(b.coupon_rate or 0),
            maturity_date=b.maturity_date or "",
            accrued_interest=float(b.accrued_interest or 0),
            movement_type=movement_type,
            variance=variance,
            source_document_id=b.source_document_id,
            validation_status="VALID",
            validation_messages=[],
        )
        line = await BondScheduleLines.insert(form)
        if line:
            created_count += 1
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "completed",
        "lines_generated": created_count,
        "message": "Bond schedule generation completed",
        "started_at": _utc_now(),
    }


async def get_schedule(
    user_id: str,
    period_id: Optional[str] = None,
) -> list[dict]:
    if period_id:
        results = await BondScheduleLines.get_by_period(period_id)
    else:
        results = await BondScheduleLines.get_all()
    return _to_list_of_dicts(results)


async def export_schedule(user_id: str, period_id: Optional[str] = None) -> dict:
    lines = await get_schedule(user_id, period_id)
    return {
        "task_id": _new_id(),
        "status": "completed",
        "row_count": len(lines),
        "csv": _schedule_to_csv(lines),
        "message": "Schedule export completed",
        "started_at": _utc_now(),
    }


def _schedule_to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


async def validate_schedule(user_id: str, period_id: str) -> dict:
    lines = await BondScheduleLines.get_by_period(period_id)
    bonds = await BondRecords.get_by_period(period_id)

    total_fv_lines = sum(float(l.face_value or 0) for l in lines)
    total_fv_bonds = sum(float(b.face_value or 0) for b in bonds)
    face_ok = abs(total_fv_lines - total_fv_bonds) < 0.01

    ai_checks = []
    for l in lines:
        try:
            cv = float(getattr(l, "current_value", None) or l.market_value or l.book_value or 0)
            pv = float(getattr(l, "previous_value", None) or ((l.market_value or l.book_value or 0) - (l.variance or 0)))
            expected_var = round(cv - pv, 2)
            if abs(expected_var - float(l.variance or 0)) > 0.01:
                ai_checks.append((l.id, "rollforward_variance_mismatch"))
        except (TypeError, ValueError):
            pass

    warning_stale = sum(1 for b in bonds if (b.updated_at or 0) and (b.updated_at < _now_ms() - 5 * 86400))

    return {
        "period_id": period_id,
        "validation_status": "passed" if face_ok and not ai_checks else ("warning" if face_ok else "failed"),
        "checks": [
            {"check": "face_value_total", "status": "passed" if face_ok else "failed",
             "message": f"lines={total_fv_lines:.2f} bonds={total_fv_bonds:.2f}"},
            {"check": "rollforward", "status": "passed" if not ai_checks else "failed",
             "message": f"{len(ai_checks)} rollforward mismatches"},
            {"check": "pricing_freshness", "status": ("warning" if warning_stale else "passed"),
             "message": f"{warning_stale} bonds not updated in >5 days"},
        ],
        "validated_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# Journals
# ---------------------------------------------------------------------------


async def generate_journals(user_id: str, period_id: str) -> dict:
    """Generate journal header + lines for accrued interest and FV adjustment from schedule lines."""
    lines = await BondScheduleLines.get_by_period(period_id)
    total_accrued = sum(float(l.accrued_interest or 0) for l in lines)
    total_fv_change = sum((float(l.market_value or 0) - float(l.book_value or 0)) for l in lines)

    journals_created: list[dict] = []

    if total_accrued > 0.005:
        jform = JournalForm(
            reporting_period_id=period_id,
            journal_number=f"AI-{period_id[:8]}",
            description=f"Monthly accrued interest recognition for period {period_id}",
            total_debit=round(total_accrued, 2),
            total_credit=round(total_accrued, 2),
            is_balanced=True,
            status="PENDING",
            ai_rationale=f"Auto-generated: accrued interest across {len(lines)} bonds",
        )
        journal = await Journals.insert(user_id, jform)
        if journal:
            debit_line = await JournalLines.insert(JournalLineForm(
                journal_id=journal.id,
                line_number=1,
                account_code="1210",
                account_description="Accrued Interest Receivable",
                debit=round(total_accrued, 2),
                credit=0.0,
                currency=(lines[0].currency if lines else "SGD"),
                bond_id=None,
                description="Accrued interest on bond portfolio",
                source_reference=f"period:{period_id}:accrued_interest",
            ))
            credit_line = await JournalLines.insert(JournalLineForm(
                journal_id=journal.id,
                line_number=2,
                account_code="4110",
                account_description="Interest Income - Bonds",
                debit=0.0,
                credit=round(total_accrued, 2),
                currency=(lines[0].currency if lines else "SGD"),
                bond_id=None,
                description="Interest income recognition",
                source_reference=f"period:{period_id}:accrued_interest",
            ))
            journals_created.append({"journal": _to_dict(journal), "lines": [_to_dict(debit_line), _to_dict(credit_line)]})

    if abs(total_fv_change) > 0.005:
        fv_debit = round(max(total_fv_change, 0), 2)
        fv_credit = round(max(-1 * total_fv_change, 0), 2)
        jform = JournalForm(
            reporting_period_id=period_id,
            journal_number=f"FV-{period_id[:8]}",
            description=f"Fair value adjustment for period {period_id}",
            total_debit=fv_debit or fv_credit,
            total_credit=fv_credit or fv_debit,
            is_balanced=True,
            status="PENDING",
            ai_rationale=f"Auto-generated: FV adjustment delta={total_fv_change:.2f} for {len(lines)} bonds",
        )
        journal = await Journals.insert(user_id, jform)
        if journal:
            d_line = await JournalLines.insert(JournalLineForm(
                journal_id=journal.id,
                line_number=1,
                account_code="1110",
                account_description="Investment in Bonds - FVOCI",
                debit=fv_debit,
                credit=fv_credit,
                currency=(lines[0].currency if lines else "SGD"),
                bond_id=None,
                description="Fair value adjustment",
                source_reference=f"period:{period_id}:fv_adjustment",
            ))
            c_line = await JournalLines.insert(JournalLineForm(
                journal_id=journal.id,
                line_number=2,
                account_code="3210",
                account_description="OCI - Fair Value Reserve",
                debit=fv_credit,
                credit=fv_debit,
                currency=(lines[0].currency if lines else "SGD"),
                bond_id=None,
                description="OCI fair value reserve movement",
                source_reference=f"period:{period_id}:fv_adjustment",
            ))
            journals_created.append({"journal": _to_dict(journal), "lines": [_to_dict(d_line), _to_dict(c_line)]})

    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "completed",
        "journals_created": len(journals_created),
        "journals": journals_created,
        "message": "Draft journal generation completed",
        "started_at": _utc_now(),
    }


async def list_journals(
    user_id: str,
    period_id: Optional[str] = None,
    journal_status: Optional[str] = None,
) -> list[dict]:
    if journal_status and period_id:
        results = await Journals.get_by_status(journal_status.upper(), period_id)
    elif journal_status:
        results = await Journals.get_by_status(journal_status.upper())
    elif period_id:
        results = await Journals.get_by_period(period_id)
    else:
        results = await Journals.get_all()
    # Summary without lines (already done by models), include line_count summary
    out = []
    for j in results:
        jd = _to_dict(j)
        jd["lines"] = None
        jd["lines_count"] = len(await JournalLines.get_by_journal(j.id))
        out.append(jd)
    return out


async def get_journal(user_id: str, journal_id: str) -> Optional[dict]:
    journal = await Journals.get_by_id(journal_id)
    if not journal:
        return None
    lines = await JournalLines.get_by_journal(journal_id)
    jd = _to_dict(journal)
    jd["lines"] = _to_list_of_dicts(lines)
    return jd


async def update_journal(user_id: str, journal_id: str, data: dict) -> Optional[dict]:
    # Only update header fields recognised on the Journal ORM
    known_header = {"journal_number", "description", "total_debit", "total_credit", "is_balanced", "status", "ai_rationale"}
    header_data = {k: v for k, v in data.items() if k in known_header}
    updated = None
    if header_data:
        updated = await Journals.update_by_id(journal_id, header_data)

    # If lines were provided, rebuild them by deletion + re-insert
    if "lines" in data and isinstance(data["lines"], list):
        await JournalLines.delete_by_journal(journal_id)
        for idx, line in enumerate(data["lines"] or [], start=1):
            lform = JournalLineForm(
                journal_id=journal_id,
                line_number=line.get("line_number") or idx,
                account_code=str(line.get("account_code") or ""),
                account_description=line.get("account_description") or line.get("account_name") or "",
                debit=float(line.get("debit") or 0),
                credit=float(line.get("credit") or 0),
                currency=line.get("currency") or "SGD",
                bond_id=line.get("bond_id"),
                description=line.get("description"),
                source_reference=line.get("source_reference"),
            )
            await JournalLines.insert(lform)
        updated = updated or await Journals.get_by_id(journal_id)

    log.info("Updated journal %s by user %s", journal_id, user_id)
    if not updated:
        return None
    full = _to_dict(updated)
    full["lines"] = _to_list_of_dicts(await JournalLines.get_by_journal(journal_id))
    return full


async def approve_journal(user_id: str, journal_id: str, user: Any = None) -> Optional[dict]:
    """Set status=APPROVED + record FinanceApproval row. RBAC gating applied in router + service."""
    _require_approve(user)
    journal = await Journals.get_by_id(journal_id)
    if not journal:
        return None
    updated = await Journals.update_by_id(journal_id, {
        "status": "APPROVED",
        "reviewed_by": user_id,
        "reviewed_at": _now_ms(),
        "review_comment": "Approved",
    })
    if updated:
        await FinanceApprovals.insert(FinanceApprovalForm(
            reporting_period_id=journal.reporting_period_id,
            object_type="JOURNAL",
            object_id=journal.id,
            action="APPROVED",
            previous_status=journal.status,
            new_status="APPROVED",
            user_id=user_id,
            user_role=getattr(user, "role", None),
            comment="Approved via service approve_journal",
        ))
    log.info("Approved journal %s by user %s", journal_id, user_id)
    if not updated:
        return None
    full = _to_dict(updated)
    full["lines"] = _to_list_of_dicts(await JournalLines.get_by_journal(journal_id))
    return full


async def reject_journal(user_id: str, journal_id: str, reason: str, user: Any = None) -> Optional[dict]:
    _require_approve(user)
    journal = await Journals.get_by_id(journal_id)
    if not journal:
        return None
    updated = await Journals.update_by_id(journal_id, {
        "status": "REJECTED",
        "reviewed_by": user_id,
        "reviewed_at": _now_ms(),
        "review_comment": reason,
    })
    if updated:
        await FinanceApprovals.insert(FinanceApprovalForm(
            reporting_period_id=journal.reporting_period_id,
            object_type="JOURNAL",
            object_id=journal.id,
            action="REJECTED",
            previous_status=journal.status,
            new_status="REJECTED",
            user_id=user_id,
            user_role=getattr(user, "role", None),
            comment=reason,
        ))
    log.info("Rejected journal %s by user %s: %s", journal_id, user_id, reason)
    if not updated:
        return None
    full = _to_dict(updated)
    full["lines"] = _to_list_of_dicts(await JournalLines.get_by_journal(journal_id))
    full["rejection_reason"] = reason
    full["rejected_by"] = user_id
    return full


# ---------------------------------------------------------------------------
# Audit Schedule
# ---------------------------------------------------------------------------


async def generate_audit_schedule(user_id: str, period_id: str) -> dict:
    """Populate AuditScheduleEntries from schedule lines + movements."""
    # Re-generating for a period replaces the prior entries rather than
    # appending duplicate rows on top of them.
    await AuditScheduleEntries.delete_by_period(period_id)

    lines = await BondScheduleLines.get_by_period(period_id)
    movements_by_bond: dict[str, list] = {}
    for mv in await BondMovements.get_by_period(period_id):
        movements_by_bond.setdefault(mv.bond_id, []).append(mv)

    created = 0
    for l in lines:
        mv_purchases = sum(float(m.current_value or 0) for m in movements_by_bond.get(l.bond_id, []) if m.movement_type == "PURCHASE")
        mv_sales = abs(sum(float(m.variance or 0) for m in movements_by_bond.get(l.bond_id, []) if m.movement_type == "SALE"))
        mv_maturities = abs(sum(float(m.variance or 0) for m in movements_by_bond.get(l.bond_id, []) if m.movement_type == "MATURITY"))
        mv_transfers = sum(float(m.variance or 0) for m in movements_by_bond.get(l.bond_id, []) if m.movement_type == "TRANSFER")
        mv_interest = sum(float(m.variance or 0) for m in movements_by_bond.get(l.bond_id, []) if m.movement_type == "ACCRUAL")
        fv_change = float(l.market_value or 0) - float(l.book_value or 0)

        form = AuditScheduleEntryForm(
            reporting_period_id=period_id,
            bond_id=l.bond_id,
            opening_balance=float(l.book_value or 0) - float(l.variance or 0),
            purchases=mv_purchases,
            sales=mv_sales,
            maturities=mv_maturities,
            transfers=mv_transfers,
            interest=mv_interest,
            fair_value_changes=fv_change,
            closing_balance=float(l.book_value or 0),
            source_references=[l.id],
            reconciliation_status=l.validation_status or "UNKNOWN",
        )
        if await AuditScheduleEntries.insert(form):
            created += 1
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "completed",
        "entries_created": created,
        "message": "Audit schedule generation completed",
        "started_at": _utc_now(),
    }


async def get_audit_schedule(
    user_id: str,
    period_id: Optional[str] = None,
) -> list[dict]:
    if period_id:
        results = await AuditScheduleEntries.get_by_period(period_id)
    else:
        results = await AuditScheduleEntries.get_all()
    return _to_list_of_dicts(results)


async def export_audit_schedule(user_id: str, period_id: Optional[str] = None) -> dict:
    rows = await get_audit_schedule(user_id, period_id)
    return {
        "task_id": _new_id(),
        "status": "completed",
        "row_count": len(rows),
        "csv": _schedule_to_csv(rows),
        "message": "Audit schedule export completed",
        "started_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# Commentary
# ---------------------------------------------------------------------------


async def generate_commentary(
    user_id: str,
    period_id: str,
    sections: Optional[list[str]] = None,
    *,
    force_llm: bool = False,
) -> dict:
    """Kick off commentary generation.

    Builds structured section summaries from DB aggregates (bond, movement,
    reconciliation and exception data) and *optionally* sends them to the
    configured LLM for polish (Task 6).  The LLM call is best-effort — any
    connection/auth/parse error or missing config falls back cleanly to the
    structured DB text, so the UI never sees empty or broken content.
    """
    sections_wanted = sections or [
        "portfolio_overview",
        "movement_analysis",
        "reconciliation_summary",
        "risk_assessment",
    ]
    created_ids: list[str] = []
    any_llm_success = False

    bonds = await BondRecords.get_by_period(period_id)
    movements = await BondMovements.get_by_period(period_id)
    reconciliations = await ReconciliationRuns.get_by_period(period_id)
    exceptions = await FinanceExceptions.get_by_period(period_id)

    period = None
    if period_id:
        period = await ReportingPeriods.get_by_id(period_id)
    period_name = period.name if period else period_id
    period_label = f"{period_name} (period {period_id})"

    total_fv = sum(float(b.face_value or 0) for b in bonds)
    total_mv = sum(float(b.market_value or 0) for b in bonds)
    curr_counts: dict[str, int] = {}
    for b in bonds:
        c = b.currency or "UNKNOWN"
        curr_counts[c] = curr_counts.get(c, 0) + 1

    last_recon = sorted(reconciliations, key=lambda r: r.created_at, reverse=True)[0] if reconciliations else None
    matched_pct = (last_recon.match_rate if last_recon else 0) or 0
    total_bonds_recon = last_recon.total_bonds if last_recon else len(bonds)
    open_exc = sum(1 for e in exceptions if e.status == "OPEN")
    high_exc = sum(1 for e in exceptions if e.severity == "HIGH")
    med_exc = sum(1 for e in exceptions if e.severity == "MEDIUM")
    low_exc = sum(1 for e in exceptions if e.severity == "LOW")
    mvmt_purch = sum(1 for m in movements if (m.movement_type or "").upper() == "PURCHASE")
    mvmt_sale = sum(1 for m in movements if (m.movement_type or "").upper() in {"SALE", "SELL", "SOLD"})
    mvmt_mat = sum(1 for m in movements if (m.movement_type or "").upper() == "MATURITY")
    mvmt_fv = sum(1 for m in movements if (m.movement_type or "").upper() == "FAIR_VALUE_CHANGE")

    structured: dict[str, str] = {
        "portfolio_overview": (
            f"Portfolio Overview — {period_label}\n\n"
            f"- Bonds in portfolio: {len(bonds)}\n"
            f"- Total face value: {total_fv:,.2f}\n"
            f"- Total market value: {total_mv:,.2f}\n"
            f"- Currency mix: {curr_counts}\n"
            f"- Generated {_utc_now()} from finance tables."
        ),
        "movement_analysis": (
            f"Movement Analysis — {period_label}\n\n"
            f"- Purchases: {mvmt_purch}\n"
            f"- Sales/maturities: {mvmt_sale + mvmt_mat} (sales {mvmt_sale}, maturity {mvmt_mat})\n"
            f"- Fair value changes: {mvmt_fv}\n"
            f"- Total movement records: {len(movements)}\n"
            f"Rows persisted in finance_bond_movement; drill into the Movements view for line-level detail."
        ),
        "reconciliation_summary": (
            f"Reconciliation Summary — {period_label}\n\n"
            f"- Last run status: {last_recon.status if last_recon else 'NOT_RUN'}\n"
            f"- Match rate: {matched_pct}%\n"
            f"- Bonds evaluated: {total_bonds_recon}\n"
            f"- Open exceptions: {open_exc}\n"
            f"Review the Exceptions page for individual variance cases."
        ),
        "risk_assessment": (
            f"Risk Assessment — {period_label}\n\n"
            f"- High severity: {high_exc}\n"
            f"- Medium severity: {med_exc}\n"
            f"- Low severity: {low_exc}\n"
            f"Total open exceptions = {open_exc}. Escalate HIGH items to the review queue immediately."
        ),
    }

    # System prompt shared across all section polish requests
    system = (
        "You are a senior fixed-income portfolio analyst writing month-end bond "
        "commentary for an audit-signed finance report. Write clear, concise prose "
        "in 3–6 short paragraphs per section. Use specific numbers from the input "
        "snapshot. Avoid bullet list formatting; prefer flowing narrative. Never "
        "invent data you cannot see. If the input snapshot is empty, simply state "
        "that there is no data for this period and recommend uploading source "
        "documents."
    )

    for section in sections_wanted:
        existing = await Commentaries.get_by_period_and_type(period_id, section)
        if existing and not force_llm:
            continue

        stub = structured.get(section) or structured.get("portfolio_overview")
        llm_text: Optional[str] = None
        try:
            llm_text = await _llm_chat(
                prompt=f"Please write the {section.replace('_', ' ')} section for {period_label} using these structured inputs:\n\n{stub}",
                system_prompt=system,
                temperature=0.2,
                max_tokens=1400,
            )
        except Exception:
            llm_text = None

        if llm_text and llm_text.strip():
            any_llm_success = True

        final_text = (llm_text and llm_text.strip()) or stub

        if existing:
            updated = await Commentaries.update_by_id(existing.id, {
                "content": final_text,
                "status": "DRAFT",
                "generated_by_ai": True,
                "rationale": f"Regenerated {_utc_now()} via LLM pipeline with DB-aggregate backing.",
            })
            if updated:
                created_ids.append(updated.id)
        else:
            form = CommentaryForm(
                reporting_period_id=period_id,
                content=final_text,
                content_type=section,
                status="DRAFT",
                generated_by_ai=True,
                rationale=(
                    f"LLM polish applied {_utc_now()}; raw DB aggregates kept as fallback."
                    if llm_text else
                    f"DB-aggregate only (LLM unavailable) {_utc_now()}."
                ),
            )
            inserted = await Commentaries.insert(user_id, form)
            if inserted:
                created_ids.append(inserted.id)

    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "sections": sections_wanted,
        "status": "completed",
        "ids_created": created_ids,
        "message": (
            "Commentary rows persisted; LLM polish applied where available."
            if any_llm_success else
            "Commentary rows persisted (DB-aggregate based; LLM unreachable or unconfigured)."
        ),
        "started_at": _utc_now(),
    }


async def regenerate_commentary(
    user_id: str,
    commentary_id: str,
) -> Optional[dict]:
    """Regenerate a single commentary row via LLM (Task 6).

    Refetches the underlying period data and reruns the LLM pipeline for the
    specific commentary section, then updates the existing commentary row in
    place.  Returns the updated row dict, or ``None`` if the row does not
    exist, and always falls back to the structured DB-aggregate text if the
    LLM call is unavailable.
    """
    existing = await Commentaries.get_by_id(commentary_id)
    if existing is None:
        return None

    period_id = existing.reporting_period_id
    section = existing.content_type or "portfolio_overview"

    result = await generate_commentary(
        user_id,
        period_id,
        sections=[section],
        force_llm=True,
    )
    refreshed = await Commentaries.get_by_id(commentary_id)
    if refreshed is None and result.get("ids_created"):
        refreshed = await Commentaries.get_by_id(result["ids_created"][0])
    return _to_dict(refreshed)


async def get_commentary(
    user_id: str,
    period_id: Optional[str] = None,
) -> list[dict]:
    if period_id:
        results = await Commentaries.get_by_period(period_id)
    else:
        results = await Commentaries.get_all()
    out = []
    for c in results:
        cd = _to_dict(c)
        cd["section"] = c.content_type
        cd["title"] = f"Commentary: {c.content_type}"
        cd["generated_by"] = "ai" if c.generated_by_ai else "human"
        cd["approved_by"] = c.approved_by
        out.append(cd)
    return out


async def update_commentary(user_id: str, commentary_id: str, data: dict) -> Optional[dict]:
    known = {"content", "content_type", "status", "edited_by"}
    payload = {k: v for k, v in data.items() if k in known}
    payload.setdefault("edited_by", user_id)
    updated = await Commentaries.update_by_id(commentary_id, payload)
    log.info("Updated commentary %s by user %s", commentary_id, user_id)
    return _to_dict(updated) if updated else None


async def approve_commentary(user_id: str, commentary_id: str, user: Any = None) -> Optional[dict]:
    _require_approve(user)
    commentary = await Commentaries.get_by_id(commentary_id)
    if not commentary:
        return None
    updated = await Commentaries.update_by_id(commentary_id, {
        "status": "APPROVED",
        "approved_by": user_id,
        "approved_at": _now_ms(),
    })
    if updated:
        await FinanceApprovals.insert(FinanceApprovalForm(
            reporting_period_id=commentary.reporting_period_id,
            object_type="COMMENTARY",
            object_id=commentary.id,
            action="APPROVED",
            previous_status=commentary.status,
            new_status="APPROVED",
            user_id=user_id,
            user_role=getattr(user, "role", None),
            comment="Approved via approve_commentary",
        ))
    log.info("Approved commentary %s by user %s", commentary_id, user_id)
    return _to_dict(updated) if updated else None


# ---------------------------------------------------------------------------
# Review & Approval (generic FinanceApprovals driven view)
# ---------------------------------------------------------------------------


async def submit_for_review(user_id: str, data: dict) -> dict:
    """Create a FINANCE_APPROVAL row with action=SUBMITTED as canonical record of review queue."""
    object_type_map = {"journal": "JOURNAL", "commentary": "COMMENTARY", "schedule": "SCHEDULE",
                       "audit_schedule": "AUDIT_SCHEDULE", "period": "PERIOD"}
    object_type = object_type_map.get((data.get("output_type") or "").lower(), data.get("output_type", "UNKNOWN").upper())

    existing_period = None
    object_id = data.get("output_id")
    if object_type == "JOURNAL":
        j = await Journals.get_by_id(object_id)
        if j:
            existing_period = j.reporting_period_id
            await Journals.update_by_id(object_id, {"status": "SUBMITTED"})
    elif object_type == "COMMENTARY":
        c = await Commentaries.get_by_id(object_id)
        if c:
            existing_period = c.reporting_period_id
            await Commentaries.update_by_id(object_id, {"status": "SUBMITTED"})

    period_id = data.get("period_id") or existing_period or ""
    approval_form = FinanceApprovalForm(
        reporting_period_id=period_id,
        object_type=object_type,
        object_id=object_id,
        action="SUBMITTED",
        previous_status=None,
        new_status="SUBMITTED",
        user_id=user_id,
        user_role=None,
        comment=data.get("title"),
    )
    approval = await FinanceApprovals.insert(approval_form)
    if approval is None:
        raise RuntimeError("Failed to insert FinanceApproval (submit_for_review)")

    return {
        "id": approval.id,
        "review_id": approval.id,
        "output_type": object_type,
        "output_id": object_id,
        "period_id": period_id,
        "title": data.get("title"),
        "status": "pending",
        "submitted_by": user_id,
        "submitted_at": datetime.fromtimestamp(approval.created_at, tz=timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "comments": None,
    }


async def approve_review(user_id: str, data: dict, user: Any = None) -> dict:
    _require_approve(user)
    review_id = data.get("review_id")
    if not review_id:
        raise ValueError("review_id required")
    # review_id == FinanceApproval.id (created in submit step) — now APPROVED sibling
    approval = await FinanceApprovals.get_by_id(review_id)
    if approval is None:
        raise ValueError(f"review_id {review_id} not found")
    approved_form = FinanceApprovalForm(
        reporting_period_id=approval.reporting_period_id,
        object_type=approval.object_type,
        object_id=approval.object_id,
        action="APPROVED",
        previous_status=approval.new_status,
        new_status="APPROVED",
        user_id=user_id,
        user_role=getattr(user, "role", None),
        comment=data.get("comments"),
    )
    final = await FinanceApprovals.insert(approved_form)
    # Set related objects status
    if approval.object_type == "JOURNAL":
        await Journals.update_by_id(approval.object_id, {
            "status": "APPROVED",
            "reviewed_by": user_id,
            "reviewed_at": _now_ms(),
            "review_comment": data.get("comments"),
        })
    elif approval.object_type == "COMMENTARY":
        await Commentaries.update_by_id(approval.object_id, {
            "status": "APPROVED",
            "approved_by": user_id,
            "approved_at": _now_ms(),
        })
    log.info("Approved review %s by user %s", review_id, user_id)
    return {
        "review_id": review_id,
        "approval_id": final.id if final else None,
        "status": "approved",
        "reviewed_by": user_id,
        "reviewed_at": _utc_now(),
        "comments": data.get("comments"),
    }


async def reject_review(user_id: str, data: dict, user: Any = None) -> dict:
    _require_approve(user)
    review_id = data.get("review_id")
    if not review_id:
        raise ValueError("review_id required")
    approval = await FinanceApprovals.get_by_id(review_id)
    if approval is None:
        raise ValueError(f"review_id {review_id} not found")
    form = FinanceApprovalForm(
        reporting_period_id=approval.reporting_period_id,
        object_type=approval.object_type,
        object_id=approval.object_id,
        action="CHANGES_REQUESTED",
        previous_status=approval.new_status,
        new_status="CHANGES_REQUESTED",
        user_id=user_id,
        user_role=getattr(user, "role", None),
        comment=data.get("reason"),
    )
    final = await FinanceApprovals.insert(form)
    if approval.object_type == "JOURNAL":
        await Journals.update_by_id(approval.object_id, {
            "status": "REJECTED",
            "reviewed_by": user_id,
            "reviewed_at": _now_ms(),
            "review_comment": data.get("reason"),
        })
    elif approval.object_type == "COMMENTARY":
        await Commentaries.update_by_id(approval.object_id, {"status": "CHANGES_REQUESTED"})
    log.info("Rejected review %s by user %s: %s", review_id, user_id, data.get("reason"))
    return {
        "review_id": review_id,
        "approval_id": final.id if final else None,
        "status": "rejected",
        "reviewed_by": user_id,
        "reviewed_at": _utc_now(),
        "comments": data.get("comments"),
        "reason": data.get("reason"),
    }


async def get_pending_reviews(user_id: str) -> list[dict]:
    """Pending reviews = the most recent FinanceApproval row per (object_type, object_id)
       whose action is SUBMITTED (no subsequent APPROVED/REJECTED/CHANGES_REQUESTED exists).
    """
    all_approvals = await FinanceApprovals.get_all()
    latest_by_object: dict[tuple[str, str], Any] = {}
    for a in all_approvals:
        key = (a.object_type, a.object_id)
        existing = latest_by_object.get(key)
        if existing is None or a.created_at > existing.created_at:
            latest_by_object[key] = a

    pending = []
    for (ot, oid), a in latest_by_object.items():
        if a.action != "SUBMITTED":
            continue
        pending.append({
            "id": a.id,
            "review_id": a.id,
            "output_type": ot.lower(),
            "output_id": oid,
            "period_id": a.reporting_period_id,
            "title": a.comment or f"{ot} review",
            "status": "pending",
            "submitted_by": a.user_id,
            "submitted_at": datetime.fromtimestamp(a.created_at, tz=timezone.utc).isoformat(),
            "reviewed_by": None,
            "reviewed_at": None,
            "comments": None,
        })
    return pending


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------


async def log_audit_trail(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    period_id: Optional[str] = None,
    details: Optional[str] = None,
    previous_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    source: Optional[str] = None,
) -> Optional[str]:
    """Persist to finance_audit_log table (truth, not stub log).

    Returns the inserted row's id (used as an execution id by the agentic
    assistant), or None if the insert failed.
    """
    form = FinanceAuditLogForm(
        reporting_period_id=period_id,
        user_id=user_id,
        action=action,
        object_type=entity_type,
        object_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
        source=source or "finance_service",
        details=details,
    )
    try:
        row = await FinanceAuditLogs.insert(form)
        return row.id if row else None
    except Exception as e:  # pragma: no cover - best-effort audit log
        log.exception("Failed to write finance_audit_log row: %s", e)
        return None


async def get_audit_log_entry(execution_id: str) -> Optional[dict]:
    row = await FinanceAuditLogs.get_by_id(execution_id)
    if not row:
        return None
    ts = datetime.fromtimestamp(row.created_at, tz=timezone.utc)
    return {
        "id": row.id,
        "action": row.action,
        "entity_type": row.object_type,
        "entity_id": row.object_id,
        "period_id": row.reporting_period_id,
        "user_id": row.user_id,
        "details": row.details,
        "timestamp": ts.isoformat(),
        "source": row.source,
    }


async def get_audit_trail(
    user_id: str,
    period_id: Optional[str] = None,
    action_filter: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict]:
    logs = await FinanceAuditLogs.get_by_period(period_id) if period_id else await FinanceAuditLogs.get_all()
    if action_filter:
        logs = [l for l in logs if action_filter in (l.action or "")]
    if entity_type:
        logs = [l for l in logs if (l.object_type or "") == entity_type]
    out = []
    for l in logs:
        ts = datetime.fromtimestamp(l.created_at, tz=timezone.utc)
        iso = ts.isoformat()
        if start_date and iso < start_date:
            continue
        if end_date and iso > end_date:
            continue
        out.append({
            "id": l.id,
            "action": l.action,
            "entity_type": l.object_type,
            "entity_id": l.object_id,
            "period_id": l.reporting_period_id,
            "user_id": l.user_id,
            "user_name": l.user_id,
            "details": l.details,
            "timestamp": iso,
            "source": l.source,
            "ip_address": l.ip_address,
        })
    return sorted(out, key=lambda x: x["timestamp"], reverse=True)


# ---------------------------------------------------------------------------
# Agentic Assistant — compound/multi-step tools
#
# These orchestrate 2+ existing service functions into one call so the
# assistant can satisfy a single user intent (e.g. "run reconciliation and
# tell me what changed") without the user manually chaining page actions.
# They never duplicate business logic — each step below calls the exact same
# function the corresponding page button already calls.
# ---------------------------------------------------------------------------


async def analyze_reconciliation_exceptions(user_id: str, period_id: str) -> dict:
    """Fetch exceptions for a period, group by severity/category, summarize."""
    exceptions = await get_exceptions(user_id, period_id=period_id)
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    open_count = 0
    high_or_critical: list[dict] = []
    for e in exceptions:
        sev = (e.get("severity") or "UNKNOWN").upper()
        cat = e.get("category") or "UNKNOWN"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        if (e.get("status") or "").upper() == "OPEN":
            open_count += 1
            if sev in ("HIGH", "CRITICAL"):
                high_or_critical.append(e)

    if not exceptions:
        summary_text = (
            "No reconciliation exceptions are recorded for this period. "
            "Note: exceptions are currently only created via manual review — "
            "reconciliation variances are tracked separately and are not yet "
            "auto-promoted into exceptions."
        )
    else:
        parts = [f"{open_count} open exception(s) out of {len(exceptions)} total."]
        if by_severity:
            parts.append("By severity: " + ", ".join(f"{k}={v}" for k, v in sorted(by_severity.items())) + ".")
        if high_or_critical:
            parts.append(f"{len(high_or_critical)} are HIGH/CRITICAL severity and open — review these first.")
        summary_text = " ".join(parts)

    return {
        "period_id": period_id,
        "total": len(exceptions),
        "open_count": open_count,
        "by_severity": by_severity,
        "by_category": by_category,
        "high_priority": high_or_critical[:10],
        "exceptions": exceptions[:20],
        "summary_text": summary_text,
        "steps": [
            {"label": "Retrieved exceptions for period", "status": "done"},
            {"label": "Grouped by severity and category", "status": "done"},
            {"label": "Generated summary", "status": "done"},
        ],
    }


async def run_reconciliation_and_summarize(user_id: str, period_id: str) -> dict:
    """Run reconciliation, then summarize what differed (variances/missing)."""
    run_result = await run_reconciliation(user_id, period_id)
    items = await get_reconciliation_results(user_id, period_id=period_id)
    variance_items = sorted(
        [i for i in items if i.get("status") == "VARIANCE"],
        key=lambda i: abs(i.get("variance_amount") or 0),
        reverse=True,
    )
    missing_items = [i for i in items if i.get("status") == "MISSING_SOURCE"]

    parts = [
        f"Processed {run_result.get('total_bonds', 0)} bonds: "
        f"{run_result.get('matched', 0)} matched, "
        f"{run_result.get('variances', 0)} variance(s), "
        f"{run_result.get('missing', 0)} missing source record(s)."
    ]
    if variance_items:
        top = variance_items[0]
        parts.append(
            f"Largest variance: bond {top.get('bond_id')} "
            f"(UBS {top.get('ubs_value')} vs LGI {top.get('lgi_value')}, "
            f"diff {top.get('variance_amount'):.2f})."
        )
    if missing_items:
        parts.append(f"{len(missing_items)} bond(s) are missing a source record entirely.")

    return {
        **run_result,
        "variance_items": variance_items[:10],
        "missing_items": missing_items[:10],
        "summary_text": " ".join(parts),
        "steps": [
            {"label": "Ran reconciliation", "status": "done"},
            {"label": "Identified differences", "status": "done"},
            {"label": "Generated summary", "status": "done"},
        ],
    }


async def generate_commentary_with_movements(user_id: str, period_id: str) -> dict:
    """Analyze movements, flag unusual ones, then generate month-end commentary."""
    movement_result = await analyze_movements(user_id, period_id)
    movements = await get_movements(user_id, period_id=period_id)
    unusual = sorted(
        [m for m in movements if m.get("movement_type") not in (None, "UNCHANGED")],
        key=lambda m: abs(m.get("variance") or 0),
        reverse=True,
    )[:5]
    commentary_result = await generate_commentary(user_id, period_id, force_llm=True)

    parts = [f"Analyzed {len(movements)} bond movement(s) for this period."]
    if unusual:
        top = unusual[0]
        parts.append(
            f"Most significant: bond {top.get('bond_id')} — {top.get('movement_type')} "
            f"(variance {top.get('variance')})."
        )
    sections = commentary_result.get("sections", [])
    parts.append(f"Commentary generated for {len(sections)} section(s).")

    return {
        "movement_summary": movement_result,
        "unusual_movements": unusual,
        "commentary": commentary_result,
        "summary_text": " ".join(parts),
        "steps": [
            {"label": "Analyzed bond movements", "status": "done"},
            {"label": "Flagged unusual movements", "status": "done"},
            {"label": "Generated commentary", "status": "done"},
        ],
    }


# ---------------------------------------------------------------------------
# Utility: CSV download readers (Task 7)
# ---------------------------------------------------------------------------


async def export_bonds_csv(user_id: str, period_id: Optional[str] = None) -> str:
    bonds = await list_bonds(user_id, period_id=period_id)
    if not bonds:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(bonds[0].keys()))
    writer.writeheader()
    for r in bonds:
        writer.writerow(r)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Finance Copilot Chat — real DB-driven answers (stub commentary; LLM via Task 6)
# ---------------------------------------------------------------------------


async def copilot_chat(
    user_id: str,
    query: str,
    reporting_period_id: Optional[str] = None,
) -> dict:
    """AI Bond Copilot chat handler.

    Matches query intent and pulls real data from the finance tables so the
    response is always dynamic (no hardcoded mock strings).  Task 6 replaces
    the text rendering with a real LLM call; the shape we keep unchanged so
    the frontend contract is stable.
    """
    q = (query or "").strip().lower()
    period_id = reporting_period_id

    content = ""
    tool_calls: list[dict[str, str]] = []

    # --- Action intents: let the user trigger a page's action from chat -----
    # Checked before the read-only intents below so "generate journals" is
    # not swallowed by the "journal" reporting branch. Each action reuses the
    # exact same service function the corresponding page button calls.
    action_verbs = ("generate", "run", "analyze", "re-run", "rerun", "create", "build", "regenerate", "kick off", "execute")
    action_topics = (
        ("audit schedule", "audit_schedule"),
        ("reconcil", "reconciliation"),
        ("movement", "movements"),
        ("commentary", "commentary"),
        ("journal", "journals"),
        ("schedule", "schedule"),
    )
    has_action_verb = any(v in q for v in action_verbs)
    matched_topic = next((topic for phrase, topic in action_topics if phrase in q), None) if has_action_verb else None

    # --- Compound flows: multi-step intents recognised ahead of the single-
    # action dispatch below, e.g. "run reconciliation and tell me what
    # changed" orchestrates run + diff-summary in one call instead of just
    # running reconciliation and stopping. Each still calls real service
    # functions only (see the "Agentic Assistant — compound/multi-step
    # tools" section of this file) — no separate business logic here.
    compound_flows = (
        (("reconcil",), ("what changed", "what differ", "difference", "summar"), "reconciliation_and_summarize"),
        (("exception",), ("analy", "prioriti", "group", "categori"), "analyze_exceptions"),
        (("commentary",), ("movement", "unusual"), "commentary_with_movements"),
    )
    matched_compound = next(
        (
            flow for topic_kws, extra_kws, flow in compound_flows
            if any(k in q for k in topic_kws) and any(k in q for k in extra_kws)
        ),
        None,
    )

    if matched_compound and not period_id:
        content = (
            "I can do that, but no reporting period is selected. "
            "Choose a period from the dropdown above and ask me again."
        )
        tool_calls = []

    elif matched_compound == "reconciliation_and_summarize":
        try:
            result = await run_reconciliation_and_summarize(user_id, period_id)
            content = result.get("summary_text", "Reconciliation completed.")
            tool_calls = [{"name": "reconciliation.run_and_summarize", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Reconciliation run failed: {ex}"

    elif matched_compound == "analyze_exceptions":
        try:
            result = await analyze_reconciliation_exceptions(user_id, period_id)
            content = result.get("summary_text", "No exceptions found.")
            tool_calls = [{"name": "exceptions.analyze", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Exception analysis failed: {ex}"

    elif matched_compound == "commentary_with_movements":
        try:
            result = await generate_commentary_with_movements(user_id, period_id)
            content = result.get("summary_text", "Commentary generated.")
            tool_calls = [{"name": "commentary.generate_with_movements", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Commentary generation failed: {ex}"

    elif matched_topic and not period_id:
        content = (
            "I can do that, but no reporting period is selected. "
            "Choose a period from the dropdown above and ask me again."
        )
        tool_calls = []

    elif matched_topic == "reconciliation":
        try:
            result = await run_reconciliation(user_id, period_id)
            content = (
                f"Reconciliation run complete for this period: "
                f"**{result.get('matched', 0)}/{result.get('total_bonds', 0)} matched** "
                f"({result.get('match_rate', 0)}% match rate), "
                f"**{result.get('variances', 0)} variances**, **{result.get('missing', 0)} missing**."
            )
            tool_calls = [{"name": "run_reconciliation", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Reconciliation run failed: {ex}"

    elif matched_topic == "movements":
        try:
            result = await analyze_movements(user_id, period_id)
            content = f"Movement analysis complete: **{result.get('movements_created', 0)} movements** identified for this period."
            tool_calls = [{"name": "analyze_movements", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Movement analysis failed: {ex}"

    elif matched_topic == "audit_schedule":
        try:
            result = await generate_audit_schedule(user_id, period_id)
            content = f"Audit schedule generated: **{result.get('entries_created', 0)} bond entries** created."
            tool_calls = [{"name": "generate_audit_schedule", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Audit schedule generation failed: {ex}"

    elif matched_topic == "schedule":
        try:
            result = await generate_schedule(user_id, period_id)
            content = f"Bond schedule generated: **{result.get('lines_generated', 0)} line items** created."
            tool_calls = [{"name": "generate_schedule", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Schedule generation failed: {ex}"

    elif matched_topic == "journals":
        try:
            result = await generate_journals(user_id, period_id)
            content = f"Draft journals generated: **{result.get('journals_created', 0)} journal(s)** created."
            tool_calls = [{"name": "generate_journals", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Journal generation failed: {ex}"

    elif matched_topic == "commentary":
        try:
            # force_llm=True: an explicit chat request to (re)generate should
            # behave like the UI's Regenerate button, not silently skip
            # sections that already exist for this period.
            result = await generate_commentary(user_id, period_id, force_llm=True)
            sections = result.get("sections", [])
            content = f"Commentary generated for **{len(sections)} section(s)**: {', '.join(sections) or 'none'}."
            tool_calls = [{"name": "generate_commentary", "result": json.dumps(result, default=str, indent=2)}]
        except Exception as ex:
            content = f"Commentary generation failed: {ex}"

    elif q in ("", "hi", "hello", "hey", "help"):
        dashboard = await get_dashboard(user_id, period_id)
        stats = dashboard.get("kpis") or {}
        pending_reviews = len(await get_pending_reviews(user_id))
        content = (
            f"Hello! I'm the AI Bond Copilot.\n\n"
            f"Current reporting period: **{dashboard.get('period_name', 'N/A')}**\n\n"
            f"- **{stats.get('total_bonds', 0)} bonds** in active portfolio\n"
            f"- **Portfolio market value:** {stats.get('total_market_value', 'N/A')}\n"
            f"- **{stats.get('exceptions_open', 0)} open exceptions**\n"
            f"- **{pending_reviews} pending reviews**\n\n"
            f"I can help with portfolio analysis, reconciliation, journals, commentary, and approvals.  What would you like to know?"
        )
        tool_calls = [{
            "name": "get_portfolio_summary",
            "result": json.dumps(dashboard, default=str, indent=2),
        }]

    elif "exception" in q or "issue" in q or "problem" in q or "open" in q:
        exceptions = await get_exceptions(user_id, period_id=period_id, exc_status="OPEN")
        resolved_count = 0
        try:
            all_exc = await get_exceptions(user_id, period_id=period_id)
            resolved_count = len([e for e in all_exc if str(e.get("status", "")).upper() != "OPEN"])
        except Exception:
            resolved_count = 0
        content = (
            f"There are currently **{len(exceptions)} open exceptions** requiring attention.\n\n"
        )
        if exceptions:
            for e in exceptions[:5]:
                content += (
                    f"- **{e.get('severity', 'N/A')}** — {e.get('title', e.get('description', 'Exception'))}\n"
                )
        else:
            content += "All exceptions have been resolved.  Well done!"
        tool_calls = [{
            "name": "get_open_exceptions",
            "result": json.dumps({
                "open_count": len(exceptions),
                "resolved_count": resolved_count,
                "exceptions": exceptions[:10],
            }, default=str, indent=2),
        }]

    elif "portfolio" in q or "bond" in q or "summary" in q or "holding" in q:
        dashboard = await get_dashboard(user_id, period_id)
        bonds = await list_bonds(user_id, period_id=period_id)
        stats = dashboard.get("kpis") or {}
        currencies = sorted(set(b.get("currency") or "UNKNOWN" for b in bonds))
        top = sorted(
            bonds,
            key=lambda b: float(b.get("market_value") or b.get("face_value") or 0),
            reverse=True,
        )[:5]
        content = (
            f"Here is your current portfolio summary for **{dashboard.get('period_name', 'this period')}**.\n\n"
            f"- Total bonds: **{stats.get('total_bonds', 0)}**\n"
            f"- Total market value: **{stats.get('total_market_value', 'N/A')}**\n"
            f"- Total face value: **{stats.get('total_face_value', 'N/A')}**\n"
            f"- Reconciliation match rate: **{stats.get('recon_rate', 'N/A')}**\n"
            f"- Currency breakdown: **{len(currencies)} currencies**"
        )
        tool_calls = [{
            "name": "get_portfolio_summary",
            "result": json.dumps({
                "total_bonds": stats.get("total_bonds", 0),
                "total_market_value": stats.get("total_market_value"),
                "total_face_value": stats.get("total_face_value"),
                "reconciliation_rate": stats.get("recon_rate"),
                "currencies": currencies,
                "top_holdings": [
                    {
                        "name": b.get("issuer_name") or b.get("isin") or b.get("bond_id"),
                        "value": b.get("market_value") or b.get("face_value"),
                    } for b in top
                ],
            }, default=str, indent=2),
        }]

    elif "reconciliation" in q or "recon" in q or "match" in q:
        summary = await get_reconciliation_summary(user_id, period_id)
        content = (
            f"Reconciliation status: **{summary.get('run_status', 'NOT_RUN')}**.\n\n"
            f"- Total bonds: **{summary.get('total_bonds', 0)}**\n"
            f"- Matched: **{summary.get('matched', 0)}**\n"
            f"- Exceptions (variances + missing): **{summary.get('exceptions', 0)}**\n"
            f"- Match rate: **{summary.get('match_rate', 'N/A')}%**"
        )
        tool_calls = [{
            "name": "get_reconciliation_summary",
            "result": json.dumps(summary, default=str, indent=2),
        }]

    elif "review" in q or "pending" in q or "approval" in q or "queue" in q:
        reviews = await get_pending_reviews(user_id)
        content = f"There are **{len(reviews)} items** pending review in the approval queue.\n\n"
        if reviews:
            for r in reviews[:6]:
                content += (
                    f"- **{r.get('output_type', 'UNKNOWN')}** — {r.get('title', r.get('review_id', ''))} "
                    f"(submitted {r.get('submitted_at', 'N/A')})\n"
                )
        else:
            content += "The approval queue is empty.  No action items pending."
        tool_calls = [{
            "name": "get_pending_reviews",
            "result": json.dumps({
                "pending_count": len(reviews),
                "items": reviews,
            }, default=str, indent=2),
        }]

    elif "commentary" in q or "narrative" in q or "report" in q:
        commentary = await get_commentary(user_id, period_id)
        sections = sorted({c.get("content_type", "unknown") for c in commentary})
        total_words = sum(
            len(str(c.get("content", "")).split()) for c in commentary
        )
        period_name = ""
        if period_id:
            p = await get_period(user_id, period_id)
            period_name = p.get("name", "") if p else ""
        content = (
            f"Month-end commentary for **{period_name or 'the selected period'}**:\n\n"
            f"- **{len(commentary)} sections** covered\n"
            f"- **{len(sections)} content types**: {', '.join(sections)}\n"
            f"- Approximately **{total_words} words**\n\n"
            f"Run `/commentary/generate` to (re)build fresh sections for the current period."
        )
        tool_calls = [{
            "name": "get_commentary",
            "result": json.dumps({
                "section_count": len(commentary),
                "total_words": total_words,
                "sections": sections,
            }, default=str, indent=2),
        }]

    elif "journal" in q or "entries" in q or "accounting" in q:
        journals = await list_journals(user_id, period_id=period_id)
        by_status: dict[str, int] = {}
        total_debits = 0.0
        total_credits = 0.0
        for j in journals:
            st = str(j.get("status", "UNKNOWN")).upper()
            by_status[st] = by_status.get(st, 0) + 1
            total_debits += float(j.get("total_debit") or 0)
            total_credits += float(j.get("total_credit") or 0)
        is_balanced = abs(total_debits - total_credits) < 0.01
        content = (
            f"There are **{len(journals)} journal entries** for this period.\n\n"
            f"- Status breakdown: {', '.join(f'{k}={v}' for k, v in by_status.items()) or 'none'}\n"
            f"- Total debits: **{total_debits:,.2f}**\n"
            f"- Total credits: **{total_credits:,.2f}**\n"
            f"- Balanced: **{is_balanced}**"
        )
        tool_calls = [{
            "name": "get_journal_summary",
            "result": json.dumps({
                "total_journals": len(journals),
                "status_summary": by_status,
                "total_debits": total_debits,
                "total_credits": total_credits,
                "balanced": is_balanced,
            }, default=str, indent=2),
        }]

    elif "audit" in q or "schedule" in q:
        try:
            schedule = await get_audit_schedule(user_id, period_id)
            lines = schedule.get("lines") or schedule if isinstance(schedule, dict) else []
            total_lines = len(lines) if isinstance(lines, list) else 0
            content = (
                f"The audit schedule for this period has been generated with **{total_lines} bond line items**.\n\n"
                f"Run the `/audit-schedule/export` endpoint to download the CSV, or use the export button in the UI."
            )
            tool_calls = [{
                "name": "get_audit_schedule",
                "result": json.dumps({"line_count": total_lines}, default=str, indent=2),
            }]
        except Exception as ex:
            content = f"Audit schedule data unavailable: {ex}.  Run audit-schedule generation first."
            tool_calls = []

    else:
        dashboard = await get_dashboard(user_id, period_id)
        stats = dashboard.get("kpis") or {}
        pending_reviews = len(await get_pending_reviews(user_id))
        content = (
            f"I understood your question about **{query[:120]}**.\n\n"
            f"Current period snapshot:\n"
            f"- Bonds: **{stats.get('total_bonds', 0)}**\n"
            f"- Market value: **{stats.get('total_market_value', 'N/A')}**\n"
            f"- Open exceptions: **{stats.get('exceptions_open', 0)}**\n"
            f"- Pending reviews: **{pending_reviews}**\n"
            f"- Match rate: **{stats.get('recon_rate', 'N/A')}**\n\n"
            f"Try asking about 'portfolio', 'exceptions', 'reconciliation', 'journals', 'commentary', or 'reviews'."
        )
        tool_calls = [{
            "name": "get_portfolio_summary",
            "result": json.dumps(dashboard, default=str, indent=2),
        }]

    return {
        "content": content,
        "tool_calls": tool_calls,
    }
