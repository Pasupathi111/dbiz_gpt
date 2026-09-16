"""
Finance service module for Bond Copilot.

Provides stub implementations that return realistic sample data
so the frontend can be developed against the API contract. Actual
business logic (extraction, reconciliation, movement analysis, etc.)
will be implemented in subsequent phases.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

async def get_dashboard(user_id: str, period_id: Optional[str] = None) -> dict:
    """Return KPI data for the current (or specified) reporting period."""
    return {
        "period_id": period_id or "period-2024-12",
        "period_name": "December 2024",
        "kpis": {
            "total_bonds": 142,
            "total_face_value": 1_250_000_000.00,
            "recon_rate": 97.8,
            "exceptions_open": 3,
            "exceptions_resolved": 45,
            "journal_count": 18,
            "journals_pending_review": 2,
            "journals_approved": 16,
            "documents_uploaded": 24,
            "documents_processed": 22,
            "documents_failed": 1,
            "documents_pending": 1,
            "schedule_generated": True,
            "commentary_generated": True,
            "review_status": "in_progress",
        },
        "generated_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# Reporting Periods
# ---------------------------------------------------------------------------

SAMPLE_PERIODS = [
    {
        "id": "period-2024-12",
        "name": "December 2024",
        "start_date": "2024-12-01",
        "end_date": "2024-12-31",
        "status": "active",
        "created_by": "system",
        "created_at": "2024-12-01T00:00:00Z",
        "updated_at": "2024-12-15T08:30:00Z",
    },
    {
        "id": "period-2024-11",
        "name": "November 2024",
        "start_date": "2024-11-01",
        "end_date": "2024-11-30",
        "status": "closed",
        "created_by": "system",
        "created_at": "2024-11-01T00:00:00Z",
        "updated_at": "2024-12-02T09:00:00Z",
    },
    {
        "id": "period-2024-10",
        "name": "October 2024",
        "start_date": "2024-10-01",
        "end_date": "2024-10-31",
        "status": "closed",
        "created_by": "system",
        "created_at": "2024-10-01T00:00:00Z",
        "updated_at": "2024-11-03T10:15:00Z",
    },
]


async def list_periods(user_id: str) -> list[dict]:
    return SAMPLE_PERIODS


async def create_period(user_id: str, data: dict) -> dict:
    period = {
        "id": _new_id(),
        **data,
        "status": "active",
        "created_by": user_id,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    log.info("Created reporting period %s by user %s", period["id"], user_id)
    return period


async def get_period(user_id: str, period_id: str) -> Optional[dict]:
    for p in SAMPLE_PERIODS:
        if p["id"] == period_id:
            return {
                **p,
                "processing_status": {
                    "documents": {"total": 24, "processed": 22, "failed": 1, "pending": 1},
                    "reconciliation": {"status": "completed", "match_rate": 97.8},
                    "journals": {"total": 18, "approved": 16, "pending": 2},
                    "schedule": {"status": "generated"},
                    "commentary": {"status": "generated"},
                },
            }
    return None


async def update_period(user_id: str, period_id: str, data: dict) -> Optional[dict]:
    for p in SAMPLE_PERIODS:
        if p["id"] == period_id:
            updated = {**p, **data, "updated_at": _utc_now()}
            log.info("Updated period %s by user %s", period_id, user_id)
            return updated
    return None


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

SAMPLE_DOCUMENTS = [
    {
        "id": "doc-001",
        "filename": "MAS_Bond_Statement_Dec2024.pdf",
        "document_type": "custodian_statement",
        "reporting_period_id": "period-2024-12",
        "status": "processed",
        "file_size": 2_450_000,
        "content_type": "application/pdf",
        "uploaded_by": "user-001",
        "uploaded_at": "2024-12-05T10:30:00Z",
        "processed_at": "2024-12-05T10:32:15Z",
        "extraction_result": {
            "bonds_extracted": 85,
            "confidence": 0.96,
        },
    },
    {
        "id": "doc-002",
        "filename": "Bloomberg_Positions_Dec2024.xlsx",
        "document_type": "bloomberg_extract",
        "reporting_period_id": "period-2024-12",
        "status": "processed",
        "file_size": 1_200_000,
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "uploaded_by": "user-001",
        "uploaded_at": "2024-12-05T11:00:00Z",
        "processed_at": "2024-12-05T11:01:45Z",
        "extraction_result": {
            "bonds_extracted": 142,
            "confidence": 0.99,
        },
    },
    {
        "id": "doc-003",
        "filename": "GL_Trial_Balance_Dec2024.csv",
        "document_type": "general_ledger",
        "reporting_period_id": "period-2024-12",
        "status": "pending",
        "file_size": 850_000,
        "content_type": "text/csv",
        "uploaded_by": "user-001",
        "uploaded_at": "2024-12-06T09:00:00Z",
        "processed_at": None,
        "extraction_result": None,
    },
]


async def upload_document(
    user_id: str,
    filename: str,
    content_type: str,
    file_size: int,
    document_type: str,
    reporting_period_id: str,
) -> dict:
    doc = {
        "id": _new_id(),
        "filename": filename,
        "document_type": document_type,
        "reporting_period_id": reporting_period_id,
        "status": "pending",
        "file_size": file_size,
        "content_type": content_type,
        "uploaded_by": user_id,
        "uploaded_at": _utc_now(),
        "processed_at": None,
        "extraction_result": None,
    }
    log.info("Uploaded document %s (%s) by user %s", doc["id"], filename, user_id)
    return doc


async def list_documents(
    user_id: str,
    period_id: Optional[str] = None,
    document_type: Optional[str] = None,
    doc_status: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_DOCUMENTS
    if period_id:
        results = [d for d in results if d["reporting_period_id"] == period_id]
    if document_type:
        results = [d for d in results if d["document_type"] == document_type]
    if doc_status:
        results = [d for d in results if d["status"] == doc_status]
    return results


async def get_document(user_id: str, doc_id: str) -> Optional[dict]:
    for d in SAMPLE_DOCUMENTS:
        if d["id"] == doc_id:
            return d
    return None


async def process_document(user_id: str, doc_id: str) -> dict:
    log.info("Processing document %s triggered by user %s", doc_id, user_id)
    return {
        "task_id": _new_id(),
        "document_id": doc_id,
        "status": "processing",
        "message": "Document processing has been queued",
        "started_at": _utc_now(),
    }


async def delete_document(user_id: str, doc_id: str) -> bool:
    log.info("Deleted document %s by user %s", doc_id, user_id)
    return True


# ---------------------------------------------------------------------------
# Bond Records
# ---------------------------------------------------------------------------

SAMPLE_BONDS = [
    {
        "id": "BOND-001",
        "isin": "SG7M18000000",
        "issuer": "Monetary Authority of Singapore",
        "description": "MAS Bill 3.25% 15-Jun-2025",
        "currency": "SGD",
        "face_value": 10_000_000.00,
        "market_value": 10_125_000.00,
        "coupon_rate": 3.25,
        "maturity_date": "2025-06-15",
        "reporting_period_id": "period-2024-12",
        "source": "bloomberg",
        "status": "reconciled",
        "accrued_interest": 148_611.11,
        "amortised_cost": 10_050_000.00,
        "fair_value": 10_125_000.00,
        "created_at": "2024-12-05T11:02:00Z",
        "updated_at": "2024-12-10T14:30:00Z",
    },
    {
        "id": "BOND-002",
        "isin": "XS1234567890",
        "issuer": "Temasek Holdings",
        "description": "Temasek 2.75% 01-Mar-2029",
        "currency": "SGD",
        "face_value": 25_000_000.00,
        "market_value": 24_375_000.00,
        "coupon_rate": 2.75,
        "maturity_date": "2029-03-01",
        "reporting_period_id": "period-2024-12",
        "source": "custodian",
        "status": "reconciled",
        "accrued_interest": 229_166.67,
        "amortised_cost": 24_800_000.00,
        "fair_value": 24_375_000.00,
        "created_at": "2024-12-05T11:02:00Z",
        "updated_at": "2024-12-10T14:30:00Z",
    },
    {
        "id": "BOND-003",
        "isin": "SG3260997239",
        "issuer": "Housing & Development Board",
        "description": "HDB 3.00% 01-Sep-2027",
        "currency": "SGD",
        "face_value": 15_000_000.00,
        "market_value": 15_225_000.00,
        "coupon_rate": 3.00,
        "maturity_date": "2027-09-01",
        "reporting_period_id": "period-2024-12",
        "source": "bloomberg",
        "status": "exception",
        "accrued_interest": 125_000.00,
        "amortised_cost": 15_100_000.00,
        "fair_value": 15_225_000.00,
        "created_at": "2024-12-05T11:02:00Z",
        "updated_at": "2024-12-11T09:15:00Z",
    },
]


async def list_bonds(
    user_id: str,
    period_id: Optional[str] = None,
    source: Optional[str] = None,
    bond_status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_BONDS
    if period_id:
        results = [b for b in results if b["reporting_period_id"] == period_id]
    if source:
        results = [b for b in results if b["source"] == source]
    if bond_status:
        results = [b for b in results if b["status"] == bond_status]
    if search:
        q = search.lower()
        results = [
            b for b in results
            if q in b["id"].lower()
            or q in b["isin"].lower()
            or q in b["issuer"].lower()
            or q in b["description"].lower()
        ]
    return results


async def get_bond(user_id: str, bond_id: str) -> Optional[dict]:
    for b in SAMPLE_BONDS:
        if b["id"] == bond_id:
            return b
    return None


async def update_bond(user_id: str, bond_id: str, data: dict) -> Optional[dict]:
    for b in SAMPLE_BONDS:
        if b["id"] == bond_id:
            updated = {**b, **data, "updated_at": _utc_now()}
            log.info("Updated bond %s by user %s", bond_id, user_id)
            return updated
    return None


async def get_bond_sources(user_id: str, bond_id: str) -> list[dict]:
    return [
        {
            "id": f"src-{bond_id}-bloomberg",
            "bond_id": bond_id,
            "source": "bloomberg",
            "face_value": 10_000_000.00,
            "market_value": 10_125_000.00,
            "accrued_interest": 148_611.11,
            "extracted_from": "doc-002",
            "extracted_at": "2024-12-05T11:01:45Z",
        },
        {
            "id": f"src-{bond_id}-custodian",
            "bond_id": bond_id,
            "source": "custodian",
            "face_value": 10_000_000.00,
            "market_value": 10_120_000.00,
            "accrued_interest": 148_611.11,
            "extracted_from": "doc-001",
            "extracted_at": "2024-12-05T10:32:15Z",
        },
    ]


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

async def run_reconciliation(user_id: str, period_id: str) -> dict:
    log.info("Reconciliation run for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "processing",
        "message": "Reconciliation has been queued",
        "started_at": _utc_now(),
    }


async def get_reconciliation_results(
    user_id: str,
    period_id: Optional[str] = None,
    recon_status: Optional[str] = None,
) -> list[dict]:
    results = [
        {
            "id": "recon-001",
            "bond_id": "BOND-001",
            "isin": "SG7M18000000",
            "period_id": "period-2024-12",
            "status": "matched",
            "bloomberg_face_value": 10_000_000.00,
            "custodian_face_value": 10_000_000.00,
            "face_value_diff": 0.00,
            "bloomberg_market_value": 10_125_000.00,
            "custodian_market_value": 10_120_000.00,
            "market_value_diff": 5_000.00,
            "within_tolerance": True,
            "reconciled_at": "2024-12-10T14:30:00Z",
        },
        {
            "id": "recon-002",
            "bond_id": "BOND-002",
            "isin": "XS1234567890",
            "period_id": "period-2024-12",
            "status": "matched",
            "bloomberg_face_value": 25_000_000.00,
            "custodian_face_value": 25_000_000.00,
            "face_value_diff": 0.00,
            "bloomberg_market_value": 24_375_000.00,
            "custodian_market_value": 24_375_000.00,
            "market_value_diff": 0.00,
            "within_tolerance": True,
            "reconciled_at": "2024-12-10T14:30:00Z",
        },
        {
            "id": "recon-003",
            "bond_id": "BOND-003",
            "isin": "SG3260997239",
            "period_id": "period-2024-12",
            "status": "exception",
            "bloomberg_face_value": 15_000_000.00,
            "custodian_face_value": 14_500_000.00,
            "face_value_diff": 500_000.00,
            "bloomberg_market_value": 15_225_000.00,
            "custodian_market_value": None,
            "market_value_diff": None,
            "within_tolerance": False,
            "reconciled_at": "2024-12-10T14:30:00Z",
        },
    ]
    if period_id:
        results = [r for r in results if r["period_id"] == period_id]
    if recon_status:
        results = [r for r in results if r["status"] == recon_status]
    return results


async def get_reconciliation_summary(user_id: str, period_id: Optional[str] = None) -> dict:
    return {
        "period_id": period_id or "period-2024-12",
        "total_bonds": 142,
        "matched": 139,
        "exceptions": 3,
        "match_rate": 97.8,
        "total_face_value_bloomberg": 1_250_000_000.00,
        "total_face_value_custodian": 1_249_500_000.00,
        "total_face_value_diff": 500_000.00,
        "total_market_value_bloomberg": 1_275_000_000.00,
        "total_market_value_custodian": 1_274_800_000.00,
        "total_market_value_diff": 200_000.00,
        "generated_at": _utc_now(),
    }


SAMPLE_EXCEPTIONS = [
    {
        "id": "exc-001",
        "recon_id": "recon-003",
        "bond_id": "BOND-003",
        "isin": "SG3260997239",
        "period_id": "period-2024-12",
        "exception_type": "face_value_mismatch",
        "description": "Face value differs by SGD 500,000 between Bloomberg and custodian",
        "bloomberg_value": 15_000_000.00,
        "custodian_value": 14_500_000.00,
        "difference": 500_000.00,
        "status": "open",
        "severity": "high",
        "assigned_to": None,
        "resolution": None,
        "created_at": "2024-12-10T14:30:00Z",
        "updated_at": "2024-12-10T14:30:00Z",
    },
    {
        "id": "exc-002",
        "recon_id": "recon-003",
        "bond_id": "BOND-003",
        "isin": "SG3260997239",
        "period_id": "period-2024-12",
        "exception_type": "missing_custodian_market_value",
        "description": "Custodian statement missing market value for HDB 3.00% 01-Sep-2027",
        "bloomberg_value": 15_225_000.00,
        "custodian_value": None,
        "difference": None,
        "status": "open",
        "severity": "medium",
        "assigned_to": None,
        "resolution": None,
        "created_at": "2024-12-10T14:30:00Z",
        "updated_at": "2024-12-10T14:30:00Z",
    },
    {
        "id": "exc-003",
        "recon_id": "recon-010",
        "bond_id": "BOND-010",
        "isin": "SG7R59000003",
        "period_id": "period-2024-12",
        "exception_type": "accrued_interest_mismatch",
        "description": "Accrued interest differs by SGD 1,250 (within tolerance but flagged for review)",
        "bloomberg_value": 87_500.00,
        "custodian_value": 86_250.00,
        "difference": 1_250.00,
        "status": "resolved",
        "severity": "low",
        "assigned_to": "user-001",
        "resolution": "Difference due to day-count convention; custodian value accepted",
        "created_at": "2024-12-10T14:30:00Z",
        "updated_at": "2024-12-12T11:00:00Z",
    },
]


async def get_exceptions(
    user_id: str,
    period_id: Optional[str] = None,
    exc_status: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_EXCEPTIONS
    if period_id:
        results = [e for e in results if e["period_id"] == period_id]
    if exc_status:
        results = [e for e in results if e["status"] == exc_status]
    return results


async def update_exception(user_id: str, exception_id: str, data: dict) -> Optional[dict]:
    for e in SAMPLE_EXCEPTIONS:
        if e["id"] == exception_id:
            updated = {**e, **data, "updated_at": _utc_now()}
            log.info("Updated exception %s by user %s", exception_id, user_id)
            return updated
    return None


# ---------------------------------------------------------------------------
# Movements
# ---------------------------------------------------------------------------

SAMPLE_MOVEMENTS = [
    {
        "id": "mov-001",
        "bond_id": "BOND-004",
        "isin": "SG31A9000009",
        "period_id": "period-2024-12",
        "movement_type": "purchase",
        "trade_date": "2024-12-02",
        "settlement_date": "2024-12-04",
        "face_value": 5_000_000.00,
        "settlement_amount": 5_025_000.00,
        "currency": "SGD",
        "status": "approved",
        "classification_confidence": 0.98,
        "created_at": "2024-12-05T11:02:00Z",
        "updated_at": "2024-12-06T10:00:00Z",
    },
    {
        "id": "mov-002",
        "bond_id": "BOND-005",
        "isin": "SG3261000006",
        "period_id": "period-2024-12",
        "movement_type": "maturity",
        "trade_date": "2024-12-15",
        "settlement_date": "2024-12-15",
        "face_value": 8_000_000.00,
        "settlement_amount": 8_000_000.00,
        "currency": "SGD",
        "status": "pending",
        "classification_confidence": 0.95,
        "created_at": "2024-12-05T11:02:00Z",
        "updated_at": "2024-12-05T11:02:00Z",
    },
    {
        "id": "mov-003",
        "bond_id": "BOND-001",
        "isin": "SG7M18000000",
        "period_id": "period-2024-12",
        "movement_type": "coupon_receipt",
        "trade_date": "2024-12-15",
        "settlement_date": "2024-12-15",
        "face_value": 10_000_000.00,
        "settlement_amount": 162_500.00,
        "currency": "SGD",
        "status": "approved",
        "classification_confidence": 0.99,
        "created_at": "2024-12-05T11:02:00Z",
        "updated_at": "2024-12-06T10:00:00Z",
    },
]


async def analyze_movements(user_id: str, period_id: str) -> dict:
    log.info("Movement analysis for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "processing",
        "message": "Movement analysis has been queued",
        "started_at": _utc_now(),
    }


async def get_movements(
    user_id: str,
    period_id: Optional[str] = None,
    movement_type: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_MOVEMENTS
    if period_id:
        results = [m for m in results if m["period_id"] == period_id]
    if movement_type:
        results = [m for m in results if m["movement_type"] == movement_type]
    return results


async def update_movement(user_id: str, movement_id: str, data: dict) -> Optional[dict]:
    for m in SAMPLE_MOVEMENTS:
        if m["id"] == movement_id:
            updated = {**m, **data, "updated_at": _utc_now()}
            log.info("Updated movement %s by user %s", movement_id, user_id)
            return updated
    return None


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

SAMPLE_SCHEDULE = [
    {
        "id": "sched-001",
        "bond_id": "BOND-001",
        "isin": "SG7M18000000",
        "issuer": "Monetary Authority of Singapore",
        "description": "MAS Bill 3.25% 15-Jun-2025",
        "currency": "SGD",
        "face_value": 10_000_000.00,
        "amortised_cost_opening": 10_025_000.00,
        "amortised_cost_closing": 10_050_000.00,
        "fair_value": 10_125_000.00,
        "accrued_interest": 148_611.11,
        "unrealised_gain_loss": 75_000.00,
        "impairment": 0.00,
        "period_id": "period-2024-12",
        "created_at": "2024-12-12T08:00:00Z",
    },
    {
        "id": "sched-002",
        "bond_id": "BOND-002",
        "isin": "XS1234567890",
        "issuer": "Temasek Holdings",
        "description": "Temasek 2.75% 01-Mar-2029",
        "currency": "SGD",
        "face_value": 25_000_000.00,
        "amortised_cost_opening": 24_750_000.00,
        "amortised_cost_closing": 24_800_000.00,
        "fair_value": 24_375_000.00,
        "accrued_interest": 229_166.67,
        "unrealised_gain_loss": -425_000.00,
        "impairment": 0.00,
        "period_id": "period-2024-12",
        "created_at": "2024-12-12T08:00:00Z",
    },
]


async def generate_schedule(user_id: str, period_id: str) -> dict:
    log.info("Schedule generation for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "processing",
        "message": "Bond schedule generation has been queued",
        "started_at": _utc_now(),
    }


async def get_schedule(
    user_id: str,
    period_id: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_SCHEDULE
    if period_id:
        results = [s for s in results if s["period_id"] == period_id]
    return results


async def export_schedule(user_id: str, period_id: Optional[str] = None) -> dict:
    """Return metadata about the generated export file. Actual file generation is deferred."""
    log.info("Schedule export for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "status": "processing",
        "message": "Schedule export to Excel has been queued",
        "started_at": _utc_now(),
    }


async def validate_schedule(user_id: str, period_id: str) -> dict:
    log.info("Schedule validation for period %s by user %s", period_id, user_id)
    return {
        "period_id": period_id,
        "validation_status": "passed",
        "checks": [
            {"check": "face_value_total", "status": "passed", "message": "Total face value matches GL"},
            {"check": "amortised_cost_rollforward", "status": "passed", "message": "Opening + movements = closing"},
            {"check": "accrued_interest_calculation", "status": "passed", "message": "Accrued interest within tolerance"},
            {"check": "fair_value_source", "status": "warning", "message": "3 bonds using stale pricing (> 5 days old)"},
        ],
        "validated_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# Journals
# ---------------------------------------------------------------------------

SAMPLE_JOURNALS = [
    {
        "id": "jrnl-001",
        "period_id": "period-2024-12",
        "journal_type": "accrued_interest",
        "description": "Monthly accrued interest recognition - December 2024",
        "status": "approved",
        "total_debit": 502_777.78,
        "total_credit": 502_777.78,
        "currency": "SGD",
        "lines": [
            {
                "id": "jrnl-001-L1",
                "account_code": "1210",
                "account_name": "Accrued Interest Receivable",
                "debit": 502_777.78,
                "credit": 0.00,
                "description": "Accrued interest on bond portfolio",
            },
            {
                "id": "jrnl-001-L2",
                "account_code": "4110",
                "account_name": "Interest Income - Bonds",
                "debit": 0.00,
                "credit": 502_777.78,
                "description": "Interest income recognition",
            },
        ],
        "created_by": "system",
        "approved_by": "user-002",
        "created_at": "2024-12-12T09:00:00Z",
        "updated_at": "2024-12-13T10:00:00Z",
    },
    {
        "id": "jrnl-002",
        "period_id": "period-2024-12",
        "journal_type": "fair_value_adjustment",
        "description": "Fair value adjustment for FVOCI portfolio - December 2024",
        "status": "pending",
        "total_debit": 350_000.00,
        "total_credit": 350_000.00,
        "currency": "SGD",
        "lines": [
            {
                "id": "jrnl-002-L1",
                "account_code": "1110",
                "account_name": "Investment in Bonds - FVOCI",
                "debit": 350_000.00,
                "credit": 0.00,
                "description": "Fair value increase on FVOCI bonds",
            },
            {
                "id": "jrnl-002-L2",
                "account_code": "3210",
                "account_name": "Other Comprehensive Income - Fair Value Reserve",
                "debit": 0.00,
                "credit": 350_000.00,
                "description": "OCI fair value reserve movement",
            },
        ],
        "created_by": "system",
        "approved_by": None,
        "created_at": "2024-12-12T09:15:00Z",
        "updated_at": "2024-12-12T09:15:00Z",
    },
]


async def generate_journals(user_id: str, period_id: str) -> dict:
    log.info("Journal generation for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "processing",
        "message": "Draft journal generation has been queued",
        "started_at": _utc_now(),
    }


async def list_journals(
    user_id: str,
    period_id: Optional[str] = None,
    journal_status: Optional[str] = None,
) -> list[dict]:
    results = [{**j, "lines": None} for j in SAMPLE_JOURNALS]  # Summary without lines
    if period_id:
        results = [j for j in results if j["period_id"] == period_id]
    if journal_status:
        results = [j for j in results if j["status"] == journal_status]
    return results


async def get_journal(user_id: str, journal_id: str) -> Optional[dict]:
    for j in SAMPLE_JOURNALS:
        if j["id"] == journal_id:
            return j
    return None


async def update_journal(user_id: str, journal_id: str, data: dict) -> Optional[dict]:
    for j in SAMPLE_JOURNALS:
        if j["id"] == journal_id:
            updated = {**j, **data, "updated_at": _utc_now()}
            log.info("Updated journal %s by user %s", journal_id, user_id)
            return updated
    return None


async def approve_journal(user_id: str, journal_id: str) -> Optional[dict]:
    for j in SAMPLE_JOURNALS:
        if j["id"] == journal_id:
            approved = {
                **j,
                "status": "approved",
                "approved_by": user_id,
                "updated_at": _utc_now(),
            }
            log.info("Approved journal %s by user %s", journal_id, user_id)
            return approved
    return None


async def reject_journal(user_id: str, journal_id: str, reason: str) -> Optional[dict]:
    for j in SAMPLE_JOURNALS:
        if j["id"] == journal_id:
            rejected = {
                **j,
                "status": "rejected",
                "rejection_reason": reason,
                "rejected_by": user_id,
                "updated_at": _utc_now(),
            }
            log.info("Rejected journal %s by user %s: %s", journal_id, user_id, reason)
            return rejected
    return None


# ---------------------------------------------------------------------------
# Audit Schedule
# ---------------------------------------------------------------------------

SAMPLE_AUDIT_SCHEDULE = [
    {
        "id": "audit-001",
        "bond_id": "BOND-001",
        "isin": "SG7M18000000",
        "issuer": "Monetary Authority of Singapore",
        "description": "MAS Bill 3.25% 15-Jun-2025",
        "period_id": "period-2024-12",
        "face_value": 10_000_000.00,
        "amortised_cost": 10_050_000.00,
        "fair_value": 10_125_000.00,
        "classification": "FVOCI",
        "impairment_stage": "Stage 1",
        "ecl_provision": 5_000.00,
        "source_documents": ["doc-001", "doc-002"],
        "reconciliation_status": "matched",
        "last_audit_date": "2024-06-30",
    },
    {
        "id": "audit-002",
        "bond_id": "BOND-002",
        "isin": "XS1234567890",
        "issuer": "Temasek Holdings",
        "description": "Temasek 2.75% 01-Mar-2029",
        "period_id": "period-2024-12",
        "face_value": 25_000_000.00,
        "amortised_cost": 24_800_000.00,
        "fair_value": 24_375_000.00,
        "classification": "FVOCI",
        "impairment_stage": "Stage 1",
        "ecl_provision": 12_500.00,
        "source_documents": ["doc-001", "doc-002"],
        "reconciliation_status": "matched",
        "last_audit_date": "2024-06-30",
    },
]


async def generate_audit_schedule(user_id: str, period_id: str) -> dict:
    log.info("Audit schedule generation for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "status": "processing",
        "message": "Audit schedule generation has been queued",
        "started_at": _utc_now(),
    }


async def get_audit_schedule(
    user_id: str,
    period_id: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_AUDIT_SCHEDULE
    if period_id:
        results = [a for a in results if a["period_id"] == period_id]
    return results


async def export_audit_schedule(user_id: str, period_id: Optional[str] = None) -> dict:
    log.info("Audit schedule export for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "status": "processing",
        "message": "Audit schedule export to Excel has been queued",
        "started_at": _utc_now(),
    }


# ---------------------------------------------------------------------------
# Commentary
# ---------------------------------------------------------------------------

SAMPLE_COMMENTARY = [
    {
        "id": "comm-001",
        "period_id": "period-2024-12",
        "section": "portfolio_overview",
        "title": "Portfolio Overview",
        "content": (
            "The bond portfolio as at 31 December 2024 comprises 142 fixed income "
            "securities with a total face value of SGD 1.25 billion. The portfolio "
            "is predominantly denominated in SGD (92%) with selective USD exposure (8%). "
            "Average portfolio duration stands at 3.2 years, reflecting a conservative "
            "positioning in light of the current interest rate environment."
        ),
        "status": "approved",
        "generated_by": "ai",
        "approved_by": "user-002",
        "created_at": "2024-12-13T08:00:00Z",
        "updated_at": "2024-12-14T09:30:00Z",
    },
    {
        "id": "comm-002",
        "period_id": "period-2024-12",
        "section": "movement_analysis",
        "title": "Period Movements",
        "content": (
            "During December 2024, the portfolio saw net purchases of SGD 5.0 million "
            "(MAS Bills) and one maturity of SGD 8.0 million (LTA Bond 2.50% Dec-2024). "
            "Coupon receipts totalled SGD 3.2 million across 18 securities. "
            "No disposals were recorded during the period."
        ),
        "status": "draft",
        "generated_by": "ai",
        "approved_by": None,
        "created_at": "2024-12-13T08:15:00Z",
        "updated_at": "2024-12-13T08:15:00Z",
    },
]


async def generate_commentary(user_id: str, period_id: str, sections: Optional[list[str]] = None) -> dict:
    log.info("Commentary generation for period %s by user %s", period_id, user_id)
    return {
        "task_id": _new_id(),
        "period_id": period_id,
        "sections": sections or ["portfolio_overview", "movement_analysis", "reconciliation_summary", "risk_assessment"],
        "status": "processing",
        "message": "AI commentary generation has been queued",
        "started_at": _utc_now(),
    }


async def get_commentary(
    user_id: str,
    period_id: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_COMMENTARY
    if period_id:
        results = [c for c in results if c["period_id"] == period_id]
    return results


async def update_commentary(user_id: str, commentary_id: str, data: dict) -> Optional[dict]:
    for c in SAMPLE_COMMENTARY:
        if c["id"] == commentary_id:
            updated = {**c, **data, "updated_at": _utc_now()}
            log.info("Updated commentary %s by user %s", commentary_id, user_id)
            return updated
    return None


async def approve_commentary(user_id: str, commentary_id: str) -> Optional[dict]:
    for c in SAMPLE_COMMENTARY:
        if c["id"] == commentary_id:
            approved = {
                **c,
                "status": "approved",
                "approved_by": user_id,
                "updated_at": _utc_now(),
            }
            log.info("Approved commentary %s by user %s", commentary_id, user_id)
            return approved
    return None


# ---------------------------------------------------------------------------
# Review & Approval
# ---------------------------------------------------------------------------

SAMPLE_REVIEWS = [
    {
        "id": "rev-001",
        "output_type": "journal",
        "output_id": "jrnl-002",
        "period_id": "period-2024-12",
        "title": "Fair value adjustment journal - December 2024",
        "status": "pending",
        "submitted_by": "user-001",
        "submitted_at": "2024-12-13T10:00:00Z",
        "reviewed_by": None,
        "reviewed_at": None,
        "comments": None,
    },
    {
        "id": "rev-002",
        "output_type": "commentary",
        "output_id": "comm-002",
        "period_id": "period-2024-12",
        "title": "Period Movements commentary - December 2024",
        "status": "pending",
        "submitted_by": "user-001",
        "submitted_at": "2024-12-13T10:15:00Z",
        "reviewed_by": None,
        "reviewed_at": None,
        "comments": None,
    },
]


async def submit_for_review(user_id: str, data: dict) -> dict:
    review = {
        "id": _new_id(),
        **data,
        "status": "pending",
        "submitted_by": user_id,
        "submitted_at": _utc_now(),
        "reviewed_by": None,
        "reviewed_at": None,
        "comments": None,
    }
    log.info("Submitted %s %s for review by user %s", data.get("output_type"), data.get("output_id"), user_id)
    return review


async def approve_review(user_id: str, data: dict) -> dict:
    result = {
        "review_id": data.get("review_id"),
        "status": "approved",
        "reviewed_by": user_id,
        "reviewed_at": _utc_now(),
        "comments": data.get("comments"),
    }
    log.info("Approved review %s by user %s", data.get("review_id"), user_id)
    return result


async def reject_review(user_id: str, data: dict) -> dict:
    result = {
        "review_id": data.get("review_id"),
        "status": "rejected",
        "reviewed_by": user_id,
        "reviewed_at": _utc_now(),
        "comments": data.get("comments"),
        "reason": data.get("reason"),
    }
    log.info("Rejected review %s by user %s: %s", data.get("review_id"), user_id, data.get("reason"))
    return result


async def get_pending_reviews(user_id: str) -> list[dict]:
    return [r for r in SAMPLE_REVIEWS if r["status"] == "pending"]


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

SAMPLE_AUDIT_TRAIL = [
    {
        "id": "trail-001",
        "action": "document.upload",
        "entity_type": "document",
        "entity_id": "doc-001",
        "period_id": "period-2024-12",
        "user_id": "user-001",
        "user_name": "John Doe",
        "details": "Uploaded MAS_Bond_Statement_Dec2024.pdf",
        "timestamp": "2024-12-05T10:30:00Z",
    },
    {
        "id": "trail-002",
        "action": "document.process",
        "entity_type": "document",
        "entity_id": "doc-001",
        "period_id": "period-2024-12",
        "user_id": "system",
        "user_name": "System",
        "details": "Processed document, extracted 85 bond records",
        "timestamp": "2024-12-05T10:32:15Z",
    },
    {
        "id": "trail-003",
        "action": "reconciliation.run",
        "entity_type": "reconciliation",
        "entity_id": "period-2024-12",
        "period_id": "period-2024-12",
        "user_id": "user-001",
        "user_name": "John Doe",
        "details": "Executed reconciliation: 139 matched, 3 exceptions",
        "timestamp": "2024-12-10T14:30:00Z",
    },
    {
        "id": "trail-004",
        "action": "journal.approve",
        "entity_type": "journal",
        "entity_id": "jrnl-001",
        "period_id": "period-2024-12",
        "user_id": "user-002",
        "user_name": "Jane Smith",
        "details": "Approved accrued interest journal (SGD 502,777.78)",
        "timestamp": "2024-12-13T10:00:00Z",
    },
]


async def get_audit_trail(
    user_id: str,
    period_id: Optional[str] = None,
    action_filter: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict]:
    results = SAMPLE_AUDIT_TRAIL
    if period_id:
        results = [t for t in results if t["period_id"] == period_id]
    if action_filter:
        results = [t for t in results if action_filter in t["action"]]
    if entity_type:
        results = [t for t in results if t["entity_type"] == entity_type]
    # Date filtering would be implemented with proper date parsing in production
    return results


# ---------------------------------------------------------------------------
# Audit Trail Logging Helper
# ---------------------------------------------------------------------------

async def log_audit_trail(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    period_id: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """Record an audit trail entry. Stub: logs only. Production will persist to DB."""
    log.info(
        "AUDIT: user=%s action=%s entity=%s/%s period=%s details=%s",
        user_id, action, entity_type, entity_id, period_id, details,
    )
