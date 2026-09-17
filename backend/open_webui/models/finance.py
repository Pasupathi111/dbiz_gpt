"""Bond Copilot finance domain models, forms, and database operations."""

from __future__ import annotations

import logging
import time
import uuid

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Float,
    Integer,
    String,
    Text,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> int:
    return int(time.time())


# ============================================================================
# 1. ReportingPeriod
# ============================================================================

class ReportingPeriod(Base):
    __tablename__ = "finance_reporting_period"

    id = Column(String, primary_key=True)
    name = Column(String)
    year = Column(Integer)
    month = Column(Integer)
    previous_period_id = Column(String, nullable=True)
    status = Column(String)  # DRAFT, IN_PROGRESS, REVIEW, FINALIZED
    created_by = Column(String)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class ReportingPeriodModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    year: int
    month: int
    previous_period_id: str | None = None
    status: str
    created_by: str
    created_at: int
    updated_at: int


class ReportingPeriodForm(BaseModel):
    name: str
    year: int
    month: int
    previous_period_id: str | None = None
    status: str = "DRAFT"


class ReportingPeriodsTable:
    async def insert(
        self, user_id: str, form_data: ReportingPeriodForm, db: AsyncSession | None = None
    ) -> ReportingPeriodModel | None:
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = ReportingPeriodModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_by": user_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = ReportingPeriod(**model.model_dump())
                db.add(result)
                await db.commit()
                return ReportingPeriodModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting reporting period: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> ReportingPeriodModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ReportingPeriod, id)
                return ReportingPeriodModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[ReportingPeriodModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ReportingPeriod).order_by(ReportingPeriod.created_at.desc())
            )
            return [ReportingPeriodModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> ReportingPeriodModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ReportingPeriod, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return ReportingPeriodModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating reporting period: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(ReportingPeriod).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False


ReportingPeriods = ReportingPeriodsTable()


# ============================================================================
# 2. FinanceDocument
# ============================================================================

class FinanceDocument(Base):
    __tablename__ = "finance_document"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    document_type = Column(String)  # UBS_EXCEL, LGI_PDF, PREVIOUS_SCHEDULE, TEMPLATE
    filename = Column(String)
    original_filename = Column(String)
    file_path = Column(Text)
    file_size = Column(BigInteger)
    file_hash = Column(String, nullable=True)
    mime_type = Column(String)
    status = Column(String, index=True)  # UPLOADED, QUEUED, PROCESSING, EXTRACTED, VALIDATED, FAILED
    validation_status = Column(String, nullable=True)  # VALID, WARNING, ERROR
    validation_messages = Column(JSON, nullable=True)
    uploaded_by = Column(String)
    processed_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class FinanceDocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    document_type: str
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    file_hash: str | None = None
    mime_type: str
    status: str
    validation_status: str | None = None
    validation_messages: list | dict | None = None
    uploaded_by: str
    processed_at: int | None = None
    created_at: int
    updated_at: int


class FinanceDocumentForm(BaseModel):
    reporting_period_id: str
    document_type: str
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    file_hash: str | None = None
    mime_type: str
    status: str = "UPLOADED"


class FinanceDocumentsTable:
    async def insert(
        self, user_id: str, form_data: FinanceDocumentForm, db: AsyncSession | None = None
    ) -> FinanceDocumentModel | None:
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = FinanceDocumentModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "uploaded_by": user_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = FinanceDocument(**model.model_dump())
                db.add(result)
                await db.commit()
                return FinanceDocumentModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting finance document: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> FinanceDocumentModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(FinanceDocument, id)
                return FinanceDocumentModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[FinanceDocumentModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceDocument)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(FinanceDocument.created_at.desc())
            )
            return [FinanceDocumentModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> FinanceDocumentModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(FinanceDocument, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return FinanceDocumentModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating finance document: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(FinanceDocument).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[FinanceDocumentModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceDocument).order_by(FinanceDocument.created_at.desc())
            )
            return [FinanceDocumentModel.model_validate(r) for r in result.scalars().all()]


FinanceDocuments = FinanceDocumentsTable()


# ============================================================================
# 3. ExtractionJob
# ============================================================================

class ExtractionJob(Base):
    __tablename__ = "finance_extraction_job"

    id = Column(String, primary_key=True)
    document_id = Column(String, index=True)
    status = Column(String, index=True)  # QUEUED, RUNNING, COMPLETED, FAILED
    extraction_type = Column(String)  # EXCEL, PDF
    records_extracted = Column(Integer, default=0)
    errors = Column(JSON, nullable=True)
    started_at = Column(BigInteger, nullable=True)
    completed_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)


class ExtractionJobModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    status: str
    extraction_type: str
    records_extracted: int = 0
    errors: list | dict | None = None
    started_at: int | None = None
    completed_at: int | None = None
    created_at: int


class ExtractionJobForm(BaseModel):
    document_id: str
    extraction_type: str
    status: str = "QUEUED"


class ExtractionJobsTable:
    async def insert(
        self, form_data: ExtractionJobForm, db: AsyncSession | None = None
    ) -> ExtractionJobModel | None:
        async with get_async_db_context(db) as db:
            try:
                model = ExtractionJobModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "records_extracted": 0,
                        "created_at": _now(),
                    }
                )
                result = ExtractionJob(**model.model_dump())
                db.add(result)
                await db.commit()
                return ExtractionJobModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting extraction job: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> ExtractionJobModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ExtractionJob, id)
                return ExtractionJobModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_document(
        self, document_id: str, db: AsyncSession | None = None
    ) -> list[ExtractionJobModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ExtractionJob)
                .filter_by(document_id=document_id)
                .order_by(ExtractionJob.created_at.desc())
            )
            return [ExtractionJobModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> ExtractionJobModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ExtractionJob, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                await db.commit()
                return ExtractionJobModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating extraction job: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(ExtractionJob).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[ExtractionJobModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ExtractionJob).order_by(ExtractionJob.created_at.desc())
            )
            return [ExtractionJobModel.model_validate(r) for r in result.scalars().all()]


ExtractionJobs = ExtractionJobsTable()


# ============================================================================
# 4. BondRecord
# ============================================================================

class BondRecord(Base):
    __tablename__ = "finance_bond_record"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    bond_id = Column(String, index=True)
    isin = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    issuer = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    face_value = Column(Float, nullable=True)
    book_value = Column(Float, nullable=True)
    market_value = Column(Float, nullable=True)
    coupon_rate = Column(Float, nullable=True)
    accrued_interest = Column(Float, nullable=True)
    maturity_date = Column(String, nullable=True)
    purchase_date = Column(String, nullable=True)
    settlement_date = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    status = Column(String, index=True)  # ACTIVE, MATURED, SOLD, TRANSFERRED
    source_document_id = Column(String, nullable=True)
    source_type = Column(String, nullable=True)  # UBS, LGI, SCHEDULE
    extraction_confidence = Column(Float, nullable=True)
    is_validated = Column(Boolean, default=False)
    validated_by = Column(String, nullable=True)
    validated_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class BondRecordModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    bond_id: str
    isin: str | None = None
    description: str | None = None
    issuer: str | None = None
    currency: str | None = None
    face_value: float | None = None
    book_value: float | None = None
    market_value: float | None = None
    coupon_rate: float | None = None
    accrued_interest: float | None = None
    maturity_date: str | None = None
    purchase_date: str | None = None
    settlement_date: str | None = None
    quantity: float | None = None
    status: str
    source_document_id: str | None = None
    source_type: str | None = None
    extraction_confidence: float | None = None
    is_validated: bool = False
    validated_by: str | None = None
    validated_at: int | None = None
    created_at: int
    updated_at: int


class BondRecordForm(BaseModel):
    reporting_period_id: str
    bond_id: str
    isin: str | None = None
    description: str | None = None
    issuer: str | None = None
    currency: str | None = None
    face_value: float | None = None
    book_value: float | None = None
    market_value: float | None = None
    coupon_rate: float | None = None
    accrued_interest: float | None = None
    maturity_date: str | None = None
    purchase_date: str | None = None
    settlement_date: str | None = None
    quantity: float | None = None
    status: str = "ACTIVE"
    source_document_id: str | None = None
    source_type: str | None = None
    extraction_confidence: float | None = None


class BondRecordsTable:
    async def insert(
        self, *args, db: AsyncSession | None = None
    ) -> BondRecordModel | None:
        """Flexible insert signature.

        Supported call conventions:
        * ``insert(form_data: BondRecordForm)`` — original 1-arg style
        * ``insert(user_id: str, form_data: BondRecordForm)`` — 2-arg style
          (``user_id`` is accepted for signature compatibility and currently
          unused; bonds don't have a ``created_by`` column.)
        """
        if len(args) == 1 and isinstance(args[0], BondRecordForm):
            form_data = args[0]
        elif (
            len(args) == 2
            and isinstance(args[0], str)
            and isinstance(args[1], BondRecordForm)
        ):
            _, form_data = args
        else:
            raise TypeError(
                f"BondRecords.insert() called with unsupported args: {[type(a).__name__ for a in args]!r}"
            )
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = BondRecordModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "is_validated": False,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = BondRecord(**model.model_dump())
                db.add(result)
                await db.commit()
                return BondRecordModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting bond record: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> BondRecordModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondRecord, id)
                return BondRecordModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[BondRecordModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondRecord)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(BondRecord.bond_id)
            )
            return [BondRecordModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_bond_id(
        self, bond_id: str, reporting_period_id: str | None = None, db: AsyncSession | None = None
    ) -> list[BondRecordModel]:
        async with get_async_db_context(db) as db:
            stmt = select(BondRecord).filter_by(bond_id=bond_id)
            if reporting_period_id:
                stmt = stmt.filter_by(reporting_period_id=reporting_period_id)
            result = await db.execute(stmt.order_by(BondRecord.created_at.desc()))
            return [BondRecordModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_isin(
        self, isin: str, reporting_period_id: str | None = None, db: AsyncSession | None = None
    ) -> list[BondRecordModel]:
        async with get_async_db_context(db) as db:
            stmt = select(BondRecord).filter_by(isin=isin)
            if reporting_period_id:
                stmt = stmt.filter_by(reporting_period_id=reporting_period_id)
            result = await db.execute(stmt.order_by(BondRecord.created_at.desc()))
            return [BondRecordModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> BondRecordModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondRecord, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return BondRecordModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating bond record: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(BondRecord).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def count_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(func.count(BondRecord.id)).filter_by(reporting_period_id=reporting_period_id)
            )
            return result.scalar() or 0

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[BondRecordModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondRecord).order_by(BondRecord.created_at.desc())
            )
            return [BondRecordModel.model_validate(r) for r in result.scalars().all()]


BondRecords = BondRecordsTable()


# ============================================================================
# 5. BondSourceRecord
# ============================================================================

class BondSourceRecord(Base):
    __tablename__ = "finance_bond_source_record"

    id = Column(String, primary_key=True)
    bond_record_id = Column(String, index=True)
    document_id = Column(String, index=True)
    source_type = Column(String)  # UBS, LGI, PREVIOUS_SCHEDULE
    raw_data = Column(JSON)
    sheet_name = Column(String, nullable=True)
    row_number = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    cell_references = Column(JSON, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    created_at = Column(BigInteger, index=True)


class BondSourceRecordModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bond_record_id: str
    document_id: str
    source_type: str
    raw_data: dict | list | None = None
    sheet_name: str | None = None
    row_number: int | None = None
    page_number: int | None = None
    cell_references: dict | list | None = None
    extraction_confidence: float | None = None
    created_at: int


class BondSourceRecordForm(BaseModel):
    bond_record_id: str
    document_id: str
    source_type: str
    raw_data: dict | list
    sheet_name: str | None = None
    row_number: int | None = None
    page_number: int | None = None
    cell_references: dict | list | None = None
    extraction_confidence: float | None = None


class BondSourceRecordsTable:
    async def insert(
        self, *args, db: AsyncSession | None = None
    ) -> BondSourceRecordModel | None:
        """Flexible insert signature (1-arg form, or 2-arg user_id,form)."""
        if len(args) == 1 and isinstance(args[0], BondSourceRecordForm):
            form_data = args[0]
        elif (
            len(args) == 2
            and isinstance(args[0], str)
            and isinstance(args[1], BondSourceRecordForm)
        ):
            _, form_data = args
        else:
            raise TypeError(
                f"BondSourceRecords.insert() called with unsupported args: {[type(a).__name__ for a in args]!r}"
            )
        async with get_async_db_context(db) as db:
            try:
                model = BondSourceRecordModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": _now(),
                    }
                )
                result = BondSourceRecord(**model.model_dump())
                db.add(result)
                await db.commit()
                return BondSourceRecordModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting bond source record: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> BondSourceRecordModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondSourceRecord, id)
                return BondSourceRecordModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_bond_record(
        self, bond_record_id: str, db: AsyncSession | None = None
    ) -> list[BondSourceRecordModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondSourceRecord)
                .filter_by(bond_record_id=bond_record_id)
                .order_by(BondSourceRecord.created_at.desc())
            )
            return [BondSourceRecordModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_document(
        self, document_id: str, db: AsyncSession | None = None
    ) -> list[BondSourceRecordModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondSourceRecord)
                .filter_by(document_id=document_id)
                .order_by(BondSourceRecord.created_at.desc())
            )
            return [BondSourceRecordModel.model_validate(r) for r in result.scalars().all()]

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(BondSourceRecord).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[BondSourceRecordModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondSourceRecord).order_by(BondSourceRecord.created_at.desc())
            )
            return [BondSourceRecordModel.model_validate(r) for r in result.scalars().all()]


BondSourceRecords = BondSourceRecordsTable()


# ============================================================================
# 6. ReconciliationRun
# ============================================================================

class ReconciliationRun(Base):
    __tablename__ = "finance_reconciliation_run"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    status = Column(String, index=True)  # RUNNING, COMPLETED, FAILED
    total_bonds = Column(Integer, default=0)
    matched = Column(Integer, default=0)
    variances = Column(Integer, default=0)
    missing = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    match_rate = Column(Float, nullable=True)
    run_by = Column(String)
    started_at = Column(BigInteger)
    completed_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)


class ReconciliationRunModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    status: str
    total_bonds: int = 0
    matched: int = 0
    variances: int = 0
    missing: int = 0
    duplicates: int = 0
    match_rate: float | None = None
    run_by: str
    started_at: int
    completed_at: int | None = None
    created_at: int


class ReconciliationRunForm(BaseModel):
    reporting_period_id: str
    status: str = "RUNNING"


class ReconciliationRunsTable:
    async def insert(
        self,
        user_id_or_form,
        form_data=None,
        db: AsyncSession | None = None,
    ) -> ReconciliationRunModel | None:
        if isinstance(user_id_or_form, ReconciliationRunForm):
            actual_form: ReconciliationRunForm = user_id_or_form
            actual_user_id: str = "system"
            actual_db = db
            if isinstance(form_data, AsyncSession) and db is None:
                actual_db = form_data
        else:
            actual_user_id = str(user_id_or_form)
            actual_form = form_data
            actual_db = db

        async with get_async_db_context(actual_db) as db:
            try:
                now = _now()
                model = ReconciliationRunModel(
                    **{
                        **actual_form.model_dump(),
                        "id": _uuid(),
                        "total_bonds": 0,
                        "matched": 0,
                        "variances": 0,
                        "missing": 0,
                        "duplicates": 0,
                        "run_by": actual_user_id,
                        "started_at": now,
                        "created_at": now,
                    }
                )
                result = ReconciliationRun(**model.model_dump())
                db.add(result)
                await db.commit()
                return ReconciliationRunModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting reconciliation run: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> ReconciliationRunModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ReconciliationRun, id)
                return ReconciliationRunModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[ReconciliationRunModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ReconciliationRun)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(ReconciliationRun.created_at.desc())
            )
            return [ReconciliationRunModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> ReconciliationRunModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ReconciliationRun, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                await db.commit()
                return ReconciliationRunModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating reconciliation run: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(ReconciliationRun).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def delete_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(
                    delete(ReconciliationRun).filter_by(reporting_period_id=reporting_period_id)
                )
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[ReconciliationRunModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ReconciliationRun).order_by(ReconciliationRun.created_at.desc())
            )
            return [ReconciliationRunModel.model_validate(r) for r in result.scalars().all()]


ReconciliationRuns = ReconciliationRunsTable()


# ============================================================================
# 7. ReconciliationItem
# ============================================================================

class ReconciliationItem(Base):
    __tablename__ = "finance_reconciliation_item"

    id = Column(String, primary_key=True)
    reconciliation_run_id = Column(String, index=True)
    bond_id = Column(String, index=True)
    isin = Column(String, nullable=True)
    status = Column(String, index=True)  # MATCHED, VARIANCE, MISSING, DUPLICATE, REVIEW_REQUIRED
    ubs_value = Column(Float, nullable=True)
    lgi_value = Column(Float, nullable=True)
    schedule_value = Column(Float, nullable=True)
    previous_value = Column(Float, nullable=True)
    variance_amount = Column(Float, nullable=True)
    variance_percentage = Column(Float, nullable=True)
    field_name = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)


class ReconciliationItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reconciliation_run_id: str
    bond_id: str
    isin: str | None = None
    status: str
    ubs_value: float | None = None
    lgi_value: float | None = None
    schedule_value: float | None = None
    previous_value: float | None = None
    variance_amount: float | None = None
    variance_percentage: float | None = None
    field_name: str | None = None
    reason: str | None = None
    ai_explanation: str | None = None
    resolution: str | None = None
    resolved_by: str | None = None
    resolved_at: int | None = None
    created_at: int


class ReconciliationItemForm(BaseModel):
    reconciliation_run_id: str
    bond_id: str
    isin: str | None = None
    status: str
    ubs_value: float | None = None
    lgi_value: float | None = None
    schedule_value: float | None = None
    previous_value: float | None = None
    variance_amount: float | None = None
    variance_percentage: float | None = None
    field_name: str | None = None
    reason: str | None = None
    ai_explanation: str | None = None


class ReconciliationItemsTable:
    async def insert(
        self, *args, db: AsyncSession | None = None
    ) -> ReconciliationItemModel | None:
        if len(args) == 1 and isinstance(args[0], ReconciliationItemForm):
            form_data = args[0]
        elif (
            len(args) == 2
            and isinstance(args[0], str)
            and isinstance(args[1], ReconciliationItemForm)
        ):
            _, form_data = args
        else:
            raise TypeError(
                f"ReconciliationItems.insert() called with unsupported args: {[type(a).__name__ for a in args]!r}"
            )
        async with get_async_db_context(db) as db:
            try:
                model = ReconciliationItemModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": _now(),
                    }
                )
                result = ReconciliationItem(**model.model_dump())
                db.add(result)
                await db.commit()
                return ReconciliationItemModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting reconciliation item: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> ReconciliationItemModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ReconciliationItem, id)
                return ReconciliationItemModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_run(
        self, reconciliation_run_id: str, db: AsyncSession | None = None
    ) -> list[ReconciliationItemModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ReconciliationItem)
                .filter_by(reconciliation_run_id=reconciliation_run_id)
                .order_by(ReconciliationItem.bond_id)
            )
            return [ReconciliationItemModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_status(
        self, reconciliation_run_id: str, status: str, db: AsyncSession | None = None
    ) -> list[ReconciliationItemModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ReconciliationItem)
                .filter_by(reconciliation_run_id=reconciliation_run_id, status=status)
                .order_by(ReconciliationItem.bond_id)
            )
            return [ReconciliationItemModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> ReconciliationItemModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(ReconciliationItem, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                await db.commit()
                return ReconciliationItemModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating reconciliation item: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(ReconciliationItem).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[ReconciliationItemModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ReconciliationItem).order_by(ReconciliationItem.created_at.desc())
            )
            return [ReconciliationItemModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_run_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[ReconciliationItemModel]:
        async with get_async_db_context(db) as db:
            stmt = (
                select(ReconciliationItem)
                .join(
                    ReconciliationRun,
                    ReconciliationRun.id == ReconciliationItem.reconciliation_run_id,
                )
                .filter(ReconciliationRun.reporting_period_id == reporting_period_id)
                .order_by(ReconciliationItem.bond_id)
            )
            result = await db.execute(stmt)
            return [ReconciliationItemModel.model_validate(r) for r in result.scalars().all()]

    async def delete_by_run(
        self, reconciliation_run_id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(
                    delete(ReconciliationItem).filter_by(reconciliation_run_id=reconciliation_run_id)
                )
                await db.commit()
                return True
            except Exception:
                return False


ReconciliationItems = ReconciliationItemsTable()


# ============================================================================
# 8. BondMovement
# ============================================================================

class BondMovement(Base):
    __tablename__ = "finance_bond_movement"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    bond_id = Column(String, index=True)
    isin = Column(String, nullable=True)
    movement_type = Column(String, index=True)  # NEW, SOLD, MATURED, TRANSFERRED, VALUE_CHANGE, COUPON_CHANGE, UNCHANGED, OTHER
    previous_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    variance = Column(Float, nullable=True)
    previous_status = Column(String, nullable=True)
    current_status = Column(String, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    explanation_confidence = Column(Float, nullable=True)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String, nullable=True)
    approved_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class BondMovementModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    bond_id: str
    isin: str | None = None
    movement_type: str
    previous_value: float | None = None
    current_value: float | None = None
    variance: float | None = None
    previous_status: str | None = None
    current_status: str | None = None
    ai_explanation: str | None = None
    explanation_confidence: float | None = None
    is_approved: bool = False
    approved_by: str | None = None
    approved_at: int | None = None
    created_at: int
    updated_at: int


class BondMovementForm(BaseModel):
    reporting_period_id: str
    bond_id: str
    isin: str | None = None
    movement_type: str
    previous_value: float | None = None
    current_value: float | None = None
    variance: float | None = None
    previous_status: str | None = None
    current_status: str | None = None
    ai_explanation: str | None = None
    explanation_confidence: float | None = None


class BondMovementsTable:
    async def insert(
        self, form_data: BondMovementForm, db: AsyncSession | None = None
    ) -> BondMovementModel | None:
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = BondMovementModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "is_approved": False,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = BondMovement(**model.model_dump())
                db.add(result)
                await db.commit()
                return BondMovementModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting bond movement: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> BondMovementModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondMovement, id)
                return BondMovementModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[BondMovementModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondMovement)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(BondMovement.bond_id)
            )
            return [BondMovementModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_bond_id(
        self, bond_id: str, reporting_period_id: str | None = None, db: AsyncSession | None = None
    ) -> list[BondMovementModel]:
        async with get_async_db_context(db) as db:
            stmt = select(BondMovement).filter_by(bond_id=bond_id)
            if reporting_period_id:
                stmt = stmt.filter_by(reporting_period_id=reporting_period_id)
            result = await db.execute(stmt.order_by(BondMovement.created_at.desc()))
            return [BondMovementModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> BondMovementModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondMovement, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return BondMovementModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating bond movement: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(BondMovement).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[BondMovementModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondMovement).order_by(BondMovement.created_at.desc())
            )
            return [BondMovementModel.model_validate(r) for r in result.scalars().all()]


BondMovements = BondMovementsTable()


# ============================================================================
# 9. BondScheduleLine
# ============================================================================

class BondScheduleLine(Base):
    __tablename__ = "finance_bond_schedule_line"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    bond_id = Column(String, index=True)
    isin = Column(String, nullable=True)
    issuer = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    face_value = Column(Float, nullable=True)
    book_value = Column(Float, nullable=True)
    market_value = Column(Float, nullable=True)
    coupon_rate = Column(Float, nullable=True)
    maturity_date = Column(String, nullable=True)
    accrued_interest = Column(Float, nullable=True)
    movement_type = Column(String, nullable=True)
    variance = Column(Float, nullable=True)
    source_document_id = Column(String, nullable=True)
    validation_status = Column(String, nullable=True)  # VALID, WARNING, ERROR
    validation_messages = Column(JSON, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class BondScheduleLineModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    bond_id: str
    isin: str | None = None
    issuer: str | None = None
    currency: str | None = None
    face_value: float | None = None
    book_value: float | None = None
    market_value: float | None = None
    coupon_rate: float | None = None
    maturity_date: str | None = None
    accrued_interest: float | None = None
    movement_type: str | None = None
    variance: float | None = None
    source_document_id: str | None = None
    validation_status: str | None = None
    validation_messages: list | dict | None = None
    created_at: int
    updated_at: int


class BondScheduleLineForm(BaseModel):
    reporting_period_id: str
    bond_id: str
    isin: str | None = None
    issuer: str | None = None
    currency: str | None = None
    face_value: float | None = None
    book_value: float | None = None
    market_value: float | None = None
    coupon_rate: float | None = None
    maturity_date: str | None = None
    accrued_interest: float | None = None
    movement_type: str | None = None
    variance: float | None = None
    source_document_id: str | None = None
    validation_status: str | None = None
    validation_messages: list | dict | None = None


class BondScheduleLinesTable:
    async def insert(
        self, *args, db: AsyncSession | None = None
    ) -> BondScheduleLineModel | None:
        if len(args) == 1 and isinstance(args[0], BondScheduleLineForm):
            form_data = args[0]
        elif (
            len(args) == 2
            and isinstance(args[0], str)
            and isinstance(args[1], BondScheduleLineForm)
        ):
            _, form_data = args
        else:
            raise TypeError(
                f"BondScheduleLines.insert() called with unsupported args: {[type(a).__name__ for a in args]!r}"
            )
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = BondScheduleLineModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = BondScheduleLine(**model.model_dump())
                db.add(result)
                await db.commit()
                return BondScheduleLineModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting bond schedule line: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> BondScheduleLineModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondScheduleLine, id)
                return BondScheduleLineModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[BondScheduleLineModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondScheduleLine)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(BondScheduleLine.bond_id)
            )
            return [BondScheduleLineModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> BondScheduleLineModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(BondScheduleLine, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return BondScheduleLineModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating bond schedule line: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(BondScheduleLine).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[BondScheduleLineModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(BondScheduleLine).order_by(BondScheduleLine.created_at.desc())
            )
            return [BondScheduleLineModel.model_validate(r) for r in result.scalars().all()]


BondScheduleLines = BondScheduleLinesTable()


# ============================================================================
# 10. Journal
# ============================================================================

class Journal(Base):
    __tablename__ = "finance_journal"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    journal_number = Column(String, index=True)
    description = Column(Text, nullable=True)
    total_debit = Column(Float, default=0)
    total_credit = Column(Float, default=0)
    is_balanced = Column(Boolean, default=False)
    status = Column(String, index=True)  # DRAFT, AI_GENERATED, PENDING_REVIEW, APPROVED, REJECTED, POSTED_EXTERNALLY
    ai_rationale = Column(Text, nullable=True)
    created_by = Column(String)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(BigInteger, nullable=True)
    review_comment = Column(Text, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class JournalModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    journal_number: str
    description: str | None = None
    total_debit: float = 0
    total_credit: float = 0
    is_balanced: bool = False
    status: str
    ai_rationale: str | None = None
    created_by: str
    reviewed_by: str | None = None
    reviewed_at: int | None = None
    review_comment: str | None = None
    created_at: int
    updated_at: int


class JournalForm(BaseModel):
    reporting_period_id: str
    journal_number: str
    description: str | None = None
    total_debit: float = 0
    total_credit: float = 0
    is_balanced: bool = False
    status: str = "DRAFT"
    ai_rationale: str | None = None


class JournalsTable:
    async def insert(
        self, user_id: str, form_data: JournalForm, db: AsyncSession | None = None
    ) -> JournalModel | None:
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = JournalModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_by": user_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = Journal(**model.model_dump())
                db.add(result)
                await db.commit()
                return JournalModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting journal: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> JournalModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(Journal, id)
                return JournalModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[JournalModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Journal)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(Journal.journal_number)
            )
            return [JournalModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_status(
        self, status: str, reporting_period_id: str | None = None, db: AsyncSession | None = None
    ) -> list[JournalModel]:
        async with get_async_db_context(db) as db:
            stmt = select(Journal).filter_by(status=status)
            if reporting_period_id:
                stmt = stmt.filter_by(reporting_period_id=reporting_period_id)
            result = await db.execute(stmt.order_by(Journal.created_at.desc()))
            return [JournalModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> JournalModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(Journal, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return JournalModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating journal: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(Journal).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[JournalModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Journal).order_by(Journal.created_at.desc())
            )
            return [JournalModel.model_validate(r) for r in result.scalars().all()]


Journals = JournalsTable()


# ============================================================================
# 11. JournalLine
# ============================================================================

class JournalLine(Base):
    __tablename__ = "finance_journal_line"

    id = Column(String, primary_key=True)
    journal_id = Column(String, index=True)
    line_number = Column(Integer)
    account_code = Column(String, index=True)
    account_description = Column(String, nullable=True)
    debit = Column(Float, default=0)
    credit = Column(Float, default=0)
    currency = Column(String, nullable=True)
    bond_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    source_reference = Column(Text, nullable=True)
    created_at = Column(BigInteger, index=True)


class JournalLineModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    journal_id: str
    line_number: int
    account_code: str
    account_description: str | None = None
    debit: float = 0
    credit: float = 0
    currency: str | None = None
    bond_id: str | None = None
    description: str | None = None
    source_reference: str | None = None
    created_at: int


class JournalLineForm(BaseModel):
    journal_id: str
    line_number: int
    account_code: str
    account_description: str | None = None
    debit: float = 0
    credit: float = 0
    currency: str | None = None
    bond_id: str | None = None
    description: str | None = None
    source_reference: str | None = None


class JournalLinesTable:
    async def insert(
        self, form_data: JournalLineForm, db: AsyncSession | None = None
    ) -> JournalLineModel | None:
        async with get_async_db_context(db) as db:
            try:
                model = JournalLineModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": _now(),
                    }
                )
                result = JournalLine(**model.model_dump())
                db.add(result)
                await db.commit()
                return JournalLineModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting journal line: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> JournalLineModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(JournalLine, id)
                return JournalLineModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_journal(
        self, journal_id: str, db: AsyncSession | None = None
    ) -> list[JournalLineModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(JournalLine)
                .filter_by(journal_id=journal_id)
                .order_by(JournalLine.line_number)
            )
            return [JournalLineModel.model_validate(r) for r in result.scalars().all()]

    async def delete_by_journal(
        self, journal_id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(JournalLine).filter_by(journal_id=journal_id))
                await db.commit()
                return True
            except Exception:
                return False

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(JournalLine).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[JournalLineModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(JournalLine).order_by(JournalLine.created_at.desc())
            )
            return [JournalLineModel.model_validate(r) for r in result.scalars().all()]


JournalLines = JournalLinesTable()


# ============================================================================
# 12. AuditScheduleEntry
# ============================================================================

class AuditScheduleEntry(Base):
    __tablename__ = "finance_audit_schedule_entry"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    bond_id = Column(String, index=True)
    opening_balance = Column(Float, nullable=True)
    purchases = Column(Float, nullable=True)
    sales = Column(Float, nullable=True)
    maturities = Column(Float, nullable=True)
    transfers = Column(Float, nullable=True)
    interest = Column(Float, nullable=True)
    fair_value_changes = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    source_references = Column(JSON, nullable=True)
    reconciliation_status = Column(String, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class AuditScheduleEntryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    bond_id: str
    opening_balance: float | None = None
    purchases: float | None = None
    sales: float | None = None
    maturities: float | None = None
    transfers: float | None = None
    interest: float | None = None
    fair_value_changes: float | None = None
    closing_balance: float | None = None
    source_references: dict | list | None = None
    reconciliation_status: str | None = None
    created_at: int
    updated_at: int


class AuditScheduleEntryForm(BaseModel):
    reporting_period_id: str
    bond_id: str
    opening_balance: float | None = None
    purchases: float | None = None
    sales: float | None = None
    maturities: float | None = None
    transfers: float | None = None
    interest: float | None = None
    fair_value_changes: float | None = None
    closing_balance: float | None = None
    source_references: dict | list | None = None
    reconciliation_status: str | None = None


class AuditScheduleEntriesTable:
    async def insert(
        self, form_data: AuditScheduleEntryForm, db: AsyncSession | None = None
    ) -> AuditScheduleEntryModel | None:
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = AuditScheduleEntryModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = AuditScheduleEntry(**model.model_dump())
                db.add(result)
                await db.commit()
                return AuditScheduleEntryModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting audit schedule entry: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> AuditScheduleEntryModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(AuditScheduleEntry, id)
                return AuditScheduleEntryModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[AuditScheduleEntryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AuditScheduleEntry)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(AuditScheduleEntry.bond_id)
            )
            return [AuditScheduleEntryModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> AuditScheduleEntryModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(AuditScheduleEntry, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return AuditScheduleEntryModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating audit schedule entry: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(AuditScheduleEntry).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def delete_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(
                    delete(AuditScheduleEntry).filter_by(reporting_period_id=reporting_period_id)
                )
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[AuditScheduleEntryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(AuditScheduleEntry).order_by(AuditScheduleEntry.created_at.desc())
            )
            return [AuditScheduleEntryModel.model_validate(r) for r in result.scalars().all()]


AuditScheduleEntries = AuditScheduleEntriesTable()


# ============================================================================
# 13. Commentary
# ============================================================================

class Commentary(Base):
    __tablename__ = "finance_commentary"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    content = Column(Text)
    content_type = Column(String, index=True)  # SUMMARY, MOVEMENTS, VARIANCES, EXCEPTIONS, OBSERVATIONS
    status = Column(String, index=True)  # AI_GENERATED, EDITED, APPROVED
    generated_by_ai = Column(Boolean, default=True)
    edited_by = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class CommentaryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    content: str
    content_type: str
    status: str
    generated_by_ai: bool = True
    edited_by: str | None = None
    approved_by: str | None = None
    approved_at: int | None = None
    created_at: int
    updated_at: int


class CommentaryForm(BaseModel):
    reporting_period_id: str
    content: str
    content_type: str
    status: str = "AI_GENERATED"
    generated_by_ai: bool = True


class CommentariesTable:
    async def insert(
        self,
        user_id_or_form,
        form_data=None,
        db: AsyncSession | None = None,
    ) -> CommentaryModel | None:
        if isinstance(user_id_or_form, CommentaryForm):
            actual_form: CommentaryForm = user_id_or_form
            actual_db = db
            if isinstance(form_data, AsyncSession) and db is None:
                actual_db = form_data
        else:
            actual_form = form_data
            actual_db = db

        async with get_async_db_context(actual_db) as db:
            try:
                now = _now()
                model = CommentaryModel(
                    **{
                        **actual_form.model_dump(),
                        "id": _uuid(),
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = Commentary(**model.model_dump())
                db.add(result)
                await db.commit()
                return CommentaryModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting commentary: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> CommentaryModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(Commentary, id)
                return CommentaryModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[CommentaryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Commentary)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(Commentary.content_type)
            )
            return [CommentaryModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_type(
        self, reporting_period_id: str, content_type: str, db: AsyncSession | None = None
    ) -> list[CommentaryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Commentary)
                .filter_by(reporting_period_id=reporting_period_id, content_type=content_type)
                .order_by(Commentary.created_at.desc())
            )
            return [CommentaryModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> CommentaryModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(Commentary, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return CommentaryModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating commentary: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(Commentary).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[CommentaryModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Commentary).order_by(Commentary.created_at.desc())
            )
            return [CommentaryModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_period_and_type(
        self,
        reporting_period_id: str,
        content_type: str,
        db: AsyncSession | None = None,
    ) -> CommentaryModel | None:
        async with get_async_db_context(db) as db:
            stmt = (
                select(Commentary)
                .filter_by(
                    reporting_period_id=reporting_period_id,
                    content_type=content_type,
                )
                .order_by(Commentary.created_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            row = result.scalars().first()
            return CommentaryModel.model_validate(row) if row else None


Commentaries = CommentariesTable()


# ============================================================================
# 14. FinanceApproval
# ============================================================================

class FinanceApproval(Base):
    __tablename__ = "finance_approval"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    object_type = Column(String, index=True)  # SCHEDULE, JOURNAL, AUDIT_SCHEDULE, COMMENTARY, PERIOD
    object_id = Column(String, index=True)
    action = Column(String)  # SUBMITTED, APPROVED, REJECTED, CHANGES_REQUESTED
    previous_status = Column(String, nullable=True)
    new_status = Column(String)
    user_id = Column(String, index=True)
    user_role = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(BigInteger, index=True)


class FinanceApprovalModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    object_type: str
    object_id: str
    action: str
    previous_status: str | None = None
    new_status: str
    user_id: str
    user_role: str | None = None
    comment: str | None = None
    created_at: int


class FinanceApprovalForm(BaseModel):
    reporting_period_id: str
    object_type: str
    object_id: str
    action: str
    previous_status: str | None = None
    new_status: str
    user_role: str | None = None
    comment: str | None = None


class FinanceApprovalsTable:
    async def insert(
        self,
        user_id_or_form,
        form_data=None,
        db: AsyncSession | None = None,
    ) -> FinanceApprovalModel | None:
        if isinstance(user_id_or_form, FinanceApprovalForm):
            actual_form: FinanceApprovalForm = user_id_or_form
            actual_user_id: str = actual_form.model_dump().get("user_id") or getattr(
                actual_form, "user_id", None) or "system"
            actual_db = db if db is None else db
            if isinstance(form_data, AsyncSession) and db is None:
                actual_db = form_data
        else:
            actual_user_id = str(user_id_or_form)
            actual_form = form_data
            actual_db = db

        async with get_async_db_context(actual_db) as db:
            try:
                model = FinanceApprovalModel(
                    **{
                        **actual_form.model_dump(),
                        "id": _uuid(),
                        "user_id": actual_user_id,
                        "created_at": _now(),
                    }
                )
                result = FinanceApproval(**model.model_dump())
                db.add(result)
                await db.commit()
                return FinanceApprovalModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting finance approval: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> FinanceApprovalModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(FinanceApproval, id)
                return FinanceApprovalModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_object(
        self, object_type: str, object_id: str, db: AsyncSession | None = None
    ) -> list[FinanceApprovalModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceApproval)
                .filter_by(object_type=object_type, object_id=object_id)
                .order_by(FinanceApproval.created_at.desc())
            )
            return [FinanceApprovalModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[FinanceApprovalModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceApproval)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(FinanceApproval.created_at.desc())
            )
            return [FinanceApprovalModel.model_validate(r) for r in result.scalars().all()]

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(FinanceApproval).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[FinanceApprovalModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceApproval).order_by(FinanceApproval.created_at.desc())
            )
            return [FinanceApprovalModel.model_validate(r) for r in result.scalars().all()]


FinanceApprovals = FinanceApprovalsTable()


# ============================================================================
# 15. FinanceException
# ============================================================================

class FinanceException(Base):
    __tablename__ = "finance_exception"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, index=True)
    category = Column(String, index=True)  # DATA_MISSING, DATA_MISMATCH, EXTRACTION_ERROR, RECONCILIATION_DIFF, DUPLICATE, INVALID_VALUE, MOVEMENT_UNCLEAR, LOW_CONFIDENCE
    severity = Column(String, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    bond_id = Column(String, nullable=True, index=True)
    description = Column(Text)
    ai_recommendation = Column(Text, nullable=True)
    status = Column(String, index=True)  # OPEN, IN_REVIEW, RESOLVED, WAIVED
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(BigInteger, nullable=True)
    source_reference = Column(Text, nullable=True)
    created_at = Column(BigInteger, index=True)
    updated_at = Column(BigInteger)


class FinanceExceptionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str
    category: str
    severity: str
    bond_id: str | None = None
    description: str
    ai_recommendation: str | None = None
    status: str
    resolution: str | None = None
    resolved_by: str | None = None
    resolved_at: int | None = None
    source_reference: str | None = None
    created_at: int
    updated_at: int


class FinanceExceptionForm(BaseModel):
    reporting_period_id: str
    category: str
    severity: str
    bond_id: str | None = None
    description: str
    ai_recommendation: str | None = None
    status: str = "OPEN"
    source_reference: str | None = None


class FinanceExceptionsTable:
    async def insert(
        self, form_data: FinanceExceptionForm, db: AsyncSession | None = None
    ) -> FinanceExceptionModel | None:
        async with get_async_db_context(db) as db:
            try:
                now = _now()
                model = FinanceExceptionModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                result = FinanceException(**model.model_dump())
                db.add(result)
                await db.commit()
                return FinanceExceptionModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting finance exception: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> FinanceExceptionModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(FinanceException, id)
                return FinanceExceptionModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[FinanceExceptionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceException)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(FinanceException.severity.desc(), FinanceException.created_at.desc())
            )
            return [FinanceExceptionModel.model_validate(r) for r in result.scalars().all()]

    async def get_open_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> list[FinanceExceptionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceException)
                .filter_by(reporting_period_id=reporting_period_id, status="OPEN")
                .order_by(FinanceException.severity.desc(), FinanceException.created_at.desc())
            )
            return [FinanceExceptionModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_severity(
        self, reporting_period_id: str, severity: str, db: AsyncSession | None = None
    ) -> list[FinanceExceptionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceException)
                .filter_by(reporting_period_id=reporting_period_id, severity=severity)
                .order_by(FinanceException.created_at.desc())
            )
            return [FinanceExceptionModel.model_validate(r) for r in result.scalars().all()]

    async def update_by_id(
        self, id: str, form_data: dict, db: AsyncSession | None = None
    ) -> FinanceExceptionModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(FinanceException, id)
                if not row:
                    return None
                for k, v in form_data.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
                row.updated_at = _now()
                await db.commit()
                return FinanceExceptionModel.model_validate(row)
            except Exception as e:
                log.exception(f"Error updating finance exception: {e}")
                return None

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(FinanceException).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def count_by_period(
        self, reporting_period_id: str, db: AsyncSession | None = None
    ) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(func.count(FinanceException.id)).filter_by(reporting_period_id=reporting_period_id)
            )
            return result.scalar() or 0

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[FinanceExceptionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceException).order_by(FinanceException.created_at.desc())
            )
            return [FinanceExceptionModel.model_validate(r) for r in result.scalars().all()]


FinanceExceptions = FinanceExceptionsTable()


# ============================================================================
# 16. FinanceAuditLog
# ============================================================================

class FinanceAuditLog(Base):
    __tablename__ = "finance_audit_log"

    id = Column(String, primary_key=True)
    reporting_period_id = Column(String, nullable=True, index=True)
    user_id = Column(String, index=True)
    action = Column(String, index=True)  # DOCUMENT_UPLOADED, DOCUMENT_PROCESSED, DATA_EXTRACTED, DATA_EDITED, RECONCILIATION_EXECUTED, etc.
    object_type = Column(String, nullable=True)
    object_id = Column(String, nullable=True)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    source = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(BigInteger, index=True)


class FinanceAuditLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reporting_period_id: str | None = None
    user_id: str
    action: str
    object_type: str | None = None
    object_id: str | None = None
    previous_value: dict | list | None = None
    new_value: dict | list | None = None
    source: str | None = None
    ip_address: str | None = None
    details: str | None = None
    created_at: int


class FinanceAuditLogForm(BaseModel):
    reporting_period_id: str | None = None
    user_id: str | None = None
    action: str
    object_type: str | None = None
    object_id: str | None = None
    previous_value: dict | list | None = None
    new_value: dict | list | None = None
    source: str | None = None
    ip_address: str | None = None
    details: str | None = None


class FinanceAuditLogsTable:
    async def insert(
        self,
        user_id_or_form,
        form_data=None,
        db: AsyncSession | None = None,
    ) -> FinanceAuditLogModel | None:
        if isinstance(user_id_or_form, FinanceAuditLogForm):
            actual_form: FinanceAuditLogForm = user_id_or_form
            dumped = actual_form.model_dump()
            actual_user_id: str = dumped.get("user_id") or "system"
            actual_db = db if db is None else db
            if isinstance(form_data, AsyncSession) and db is None:
                actual_db = form_data
        else:
            actual_user_id = str(user_id_or_form)
            actual_form = form_data
            actual_db = db

        async with get_async_db_context(actual_db) as db:
            try:
                model = FinanceAuditLogModel(
                    **{
                        **actual_form.model_dump(),
                        "id": _uuid(),
                        "user_id": actual_user_id,
                        "created_at": _now(),
                    }
                )
                result = FinanceAuditLog(**model.model_dump())
                db.add(result)
                await db.commit()
                return FinanceAuditLogModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting finance audit log: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> FinanceAuditLogModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(FinanceAuditLog, id)
                return FinanceAuditLogModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_period(
        self, reporting_period_id: str, skip: int = 0, limit: int = 100, db: AsyncSession | None = None
    ) -> list[FinanceAuditLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceAuditLog)
                .filter_by(reporting_period_id=reporting_period_id)
                .order_by(FinanceAuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return [FinanceAuditLogModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_user(
        self, user_id: str, skip: int = 0, limit: int = 100, db: AsyncSession | None = None
    ) -> list[FinanceAuditLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceAuditLog)
                .filter_by(user_id=user_id)
                .order_by(FinanceAuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return [FinanceAuditLogModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_object(
        self, object_type: str, object_id: str, db: AsyncSession | None = None
    ) -> list[FinanceAuditLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceAuditLog)
                .filter_by(object_type=object_type, object_id=object_id)
                .order_by(FinanceAuditLog.created_at.desc())
            )
            return [FinanceAuditLogModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_action(
        self, action: str, reporting_period_id: str | None = None,
        skip: int = 0, limit: int = 100, db: AsyncSession | None = None
    ) -> list[FinanceAuditLogModel]:
        async with get_async_db_context(db) as db:
            stmt = select(FinanceAuditLog).filter_by(action=action)
            if reporting_period_id:
                stmt = stmt.filter_by(reporting_period_id=reporting_period_id)
            result = await db.execute(
                stmt.order_by(FinanceAuditLog.created_at.desc()).offset(skip).limit(limit)
            )
            return [FinanceAuditLogModel.model_validate(r) for r in result.scalars().all()]

    async def get_all(
        self, skip: int = 0, limit: int = 1000, db: AsyncSession | None = None
    ) -> list[FinanceAuditLogModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(FinanceAuditLog)
                .order_by(FinanceAuditLog.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return [FinanceAuditLogModel.model_validate(r) for r in result.scalars().all()]


FinanceAuditLogs = FinanceAuditLogsTable()


# ============================================================================
# 17. SourceReference
# ============================================================================

class SourceReference(Base):
    __tablename__ = "finance_source_reference"

    id = Column(String, primary_key=True)
    bond_record_id = Column(String, nullable=True, index=True)
    document_id = Column(String, nullable=True, index=True)
    field_name = Column(String)
    value = Column(Text, nullable=True)
    source_type = Column(String)  # UBS_EXCEL, LGI_PDF, PREVIOUS_SCHEDULE
    sheet_name = Column(String, nullable=True)
    row_number = Column(Integer, nullable=True)
    column_name = Column(String, nullable=True)
    page_number = Column(Integer, nullable=True)
    cell_reference = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(BigInteger, index=True)


class SourceReferenceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bond_record_id: str | None = None
    document_id: str | None = None
    field_name: str
    value: str | None = None
    source_type: str
    sheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    page_number: int | None = None
    cell_reference: str | None = None
    confidence: float | None = None
    created_at: int


class SourceReferenceForm(BaseModel):
    bond_record_id: str | None = None
    document_id: str | None = None
    field_name: str
    value: str | None = None
    source_type: str
    sheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    page_number: int | None = None
    cell_reference: str | None = None
    confidence: float | None = None


class SourceReferencesTable:
    async def insert(
        self, form_data: SourceReferenceForm, db: AsyncSession | None = None
    ) -> SourceReferenceModel | None:
        async with get_async_db_context(db) as db:
            try:
                model = SourceReferenceModel(
                    **{
                        **form_data.model_dump(),
                        "id": _uuid(),
                        "created_at": _now(),
                    }
                )
                result = SourceReference(**model.model_dump())
                db.add(result)
                await db.commit()
                return SourceReferenceModel.model_validate(result)
            except Exception as e:
                log.exception(f"Error inserting source reference: {e}")
                return None

    async def get_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> SourceReferenceModel | None:
        async with get_async_db_context(db) as db:
            try:
                row = await db.get(SourceReference, id)
                return SourceReferenceModel.model_validate(row) if row else None
            except Exception:
                return None

    async def get_by_bond_record(
        self, bond_record_id: str, db: AsyncSession | None = None
    ) -> list[SourceReferenceModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(SourceReference)
                .filter_by(bond_record_id=bond_record_id)
                .order_by(SourceReference.field_name)
            )
            return [SourceReferenceModel.model_validate(r) for r in result.scalars().all()]

    async def get_by_document(
        self, document_id: str, db: AsyncSession | None = None
    ) -> list[SourceReferenceModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(SourceReference)
                .filter_by(document_id=document_id)
                .order_by(SourceReference.created_at.desc())
            )
            return [SourceReferenceModel.model_validate(r) for r in result.scalars().all()]

    async def delete_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(SourceReference).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False

    async def delete_by_bond_record(
        self, bond_record_id: str, db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(SourceReference).filter_by(bond_record_id=bond_record_id))
                await db.commit()
                return True
            except Exception:
                return False

    async def get_all(
        self, db: AsyncSession | None = None
    ) -> list[SourceReferenceModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(SourceReference).order_by(SourceReference.created_at.desc())
            )
            return [SourceReferenceModel.model_validate(r) for r in result.scalars().all()]


SourceReferences = SourceReferencesTable()
