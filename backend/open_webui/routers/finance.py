import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.services import finance_service
from open_webui.utils.auth import get_verified_user
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Pydantic Models
############################


# -- Reporting Periods --

class PeriodCreateForm(BaseModel):
    name: str
    start_date: str
    end_date: str


class PeriodUpdateForm(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None


# -- Bonds --

class BondUpdateForm(BaseModel):
    face_value: Optional[float] = None
    market_value: Optional[float] = None
    accrued_interest: Optional[float] = None
    amortised_cost: Optional[float] = None
    fair_value: Optional[float] = None
    status: Optional[str] = None


# -- Reconciliation --

class ReconciliationRunForm(BaseModel):
    period_id: str


class ExceptionUpdateForm(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None
    assigned_to: Optional[str] = None


# -- Movements --

class MovementAnalyzeForm(BaseModel):
    period_id: str


class MovementUpdateForm(BaseModel):
    movement_type: Optional[str] = None
    status: Optional[str] = None
    classification_confidence: Optional[float] = None


# -- Schedule --

class ScheduleGenerateForm(BaseModel):
    period_id: str


class ScheduleValidateForm(BaseModel):
    period_id: str


# -- Journals --

class JournalGenerateForm(BaseModel):
    period_id: str


class JournalUpdateForm(BaseModel):
    description: Optional[str] = None
    lines: Optional[list[dict]] = None
    status: Optional[str] = None


class JournalRejectForm(BaseModel):
    reason: str


# -- Audit Schedule --

class AuditScheduleGenerateForm(BaseModel):
    period_id: str


# -- Commentary --

class CommentaryGenerateForm(BaseModel):
    period_id: str
    sections: Optional[list[str]] = None


class CommentaryUpdateForm(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


# -- Review --

class ReviewSubmitForm(BaseModel):
    output_type: str
    output_id: str
    period_id: str
    title: Optional[str] = None


class ReviewApproveForm(BaseModel):
    review_id: str
    comments: Optional[str] = None


class ReviewRejectForm(BaseModel):
    review_id: str
    reason: str
    comments: Optional[str] = None


############################
# Dashboard
############################


@router.get('/dashboard')
async def get_dashboard(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.get_dashboard(user.id, period_id)
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving dashboard data'),
        )


############################
# Reporting Periods
############################


@router.get('/periods')
async def list_periods(
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.list_periods(user.id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error listing reporting periods'),
        )


@router.post('/periods')
async def create_period(
    form_data: PeriodCreateForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.create_period(user.id, form_data.model_dump())
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='period.create',
            entity_type='period',
            entity_id=result['id'],
            details=f'Created reporting period: {form_data.name}',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error creating reporting period'),
        )


@router.get('/periods/{period_id}')
async def get_period(
    period_id: str,
    user=Depends(get_verified_user),
):
    result = await finance_service.get_period(user.id, period_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return result


@router.put('/periods/{period_id}')
async def update_period(
    period_id: str,
    form_data: PeriodUpdateForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.update_period(
        user.id, period_id, form_data.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='period.update',
        entity_type='period',
        entity_id=period_id,
        details=f'Updated reporting period',
    )
    return result


############################
# Documents
############################


@router.post('/documents/upload')
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    reporting_period_id: str = Form(...),
    user=Depends(get_verified_user),
):
    try:
        contents = await file.read()
        file_size = len(contents)

        result = await finance_service.upload_document(
            user_id=user.id,
            filename=file.filename or 'unknown',
            content_type=file.content_type or 'application/octet-stream',
            file_size=file_size,
            document_type=document_type,
            reporting_period_id=reporting_period_id,
        )
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='document.upload',
            entity_type='document',
            entity_id=result['id'],
            period_id=reporting_period_id,
            details=f'Uploaded {file.filename}',
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error uploading document'),
        )


@router.get('/documents')
async def list_documents(
    period_id: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    doc_status: Optional[str] = Query(None, alias='status'),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.list_documents(
            user.id, period_id, document_type, doc_status,
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error listing documents'),
        )


@router.get('/documents/{doc_id}')
async def get_document(
    doc_id: str,
    user=Depends(get_verified_user),
):
    result = await finance_service.get_document(user.id, doc_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return result


@router.post('/documents/{doc_id}/process')
async def process_document(
    doc_id: str,
    user=Depends(get_verified_user),
):
    doc = await finance_service.get_document(user.id, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    result = await finance_service.process_document(user.id, doc_id)
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='document.process',
        entity_type='document',
        entity_id=doc_id,
        period_id=doc.get('reporting_period_id'),
        details=f'Triggered processing for {doc.get("filename")}',
    )
    return result


@router.delete('/documents/{doc_id}')
async def delete_document(
    doc_id: str,
    user=Depends(get_verified_user),
):
    doc = await finance_service.get_document(user.id, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    result = await finance_service.delete_document(user.id, doc_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error deleting document'),
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='document.delete',
        entity_type='document',
        entity_id=doc_id,
        period_id=doc.get('reporting_period_id'),
        details=f'Deleted {doc.get("filename")}',
    )
    return {'message': 'Document deleted successfully'}


############################
# Bond Records
############################


@router.get('/bonds')
async def list_bonds(
    period_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    bond_status: Optional[str] = Query(None, alias='status'),
    search: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.list_bonds(
            user.id, period_id, source, bond_status, search,
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error listing bonds'),
        )


@router.get('/bonds/{bond_id}')
async def get_bond(
    bond_id: str,
    user=Depends(get_verified_user),
):
    result = await finance_service.get_bond(user.id, bond_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # Include source records in detail view
    sources = await finance_service.get_bond_sources(user.id, bond_id)
    return {**result, 'sources': sources}


@router.put('/bonds/{bond_id}')
async def update_bond(
    bond_id: str,
    form_data: BondUpdateForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.update_bond(
        user.id, bond_id, form_data.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='bond.update',
        entity_type='bond',
        entity_id=bond_id,
        period_id=result.get('reporting_period_id'),
        details=f'Updated bond {bond_id}',
    )
    return result


@router.get('/bonds/{bond_id}/sources')
async def get_bond_sources(
    bond_id: str,
    user=Depends(get_verified_user),
):
    bond = await finance_service.get_bond(user.id, bond_id)
    if not bond:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return await finance_service.get_bond_sources(user.id, bond_id)


############################
# Reconciliation
############################


@router.post('/reconciliation/run')
async def run_reconciliation(
    form_data: ReconciliationRunForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.run_reconciliation(user.id, form_data.period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='reconciliation.run',
            entity_type='reconciliation',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Triggered reconciliation run',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error running reconciliation'),
        )


@router.get('/reconciliation')
async def get_reconciliation(
    period_id: Optional[str] = Query(None),
    recon_status: Optional[str] = Query(None, alias='status'),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_reconciliation_results(
            user.id, period_id, recon_status,
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving reconciliation results'),
        )


@router.get('/reconciliation/summary')
async def get_reconciliation_summary(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_reconciliation_summary(user.id, period_id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving reconciliation summary'),
        )


@router.get('/reconciliation/exceptions')
async def get_exceptions(
    period_id: Optional[str] = Query(None),
    exc_status: Optional[str] = Query(None, alias='status'),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_exceptions(user.id, period_id, exc_status)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving exceptions'),
        )


@router.put('/reconciliation/exceptions/{exception_id}')
async def update_exception(
    exception_id: str,
    form_data: ExceptionUpdateForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.update_exception(
        user.id, exception_id, form_data.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='exception.update',
        entity_type='exception',
        entity_id=exception_id,
        period_id=result.get('period_id'),
        details=f'Updated exception {exception_id}: status={form_data.status}',
    )
    return result


############################
# Movements
############################


@router.post('/movements/analyze')
async def analyze_movements(
    form_data: MovementAnalyzeForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.analyze_movements(user.id, form_data.period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='movements.analyze',
            entity_type='movement',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Triggered movement analysis',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error running movement analysis'),
        )


@router.get('/movements')
async def get_movements(
    period_id: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None, alias='type'),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_movements(user.id, period_id, movement_type)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving movements'),
        )


@router.put('/movements/{movement_id}')
async def update_movement(
    movement_id: str,
    form_data: MovementUpdateForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.update_movement(
        user.id, movement_id, form_data.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='movement.update',
        entity_type='movement',
        entity_id=movement_id,
        period_id=result.get('period_id'),
        details=f'Updated movement {movement_id}',
    )
    return result


############################
# Schedule
############################


@router.post('/schedule/generate')
async def generate_schedule(
    form_data: ScheduleGenerateForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.generate_schedule(user.id, form_data.period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='schedule.generate',
            entity_type='schedule',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Triggered bond schedule generation',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error generating schedule'),
        )


@router.get('/schedule')
async def get_schedule(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_schedule(user.id, period_id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving schedule'),
        )


@router.get('/schedule/export')
async def export_schedule(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.export_schedule(user.id, period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='schedule.export',
            entity_type='schedule',
            entity_id=period_id or 'all',
            period_id=period_id,
            details='Triggered schedule export to Excel',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error exporting schedule'),
        )


@router.post('/schedule/validate')
async def validate_schedule(
    form_data: ScheduleValidateForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.validate_schedule(user.id, form_data.period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='schedule.validate',
            entity_type='schedule',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Ran schedule validation',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error validating schedule'),
        )


############################
# Journals
############################


@router.post('/journals/generate')
async def generate_journals(
    form_data: JournalGenerateForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.generate_journals(user.id, form_data.period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='journals.generate',
            entity_type='journal',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Triggered draft journal generation',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error generating journals'),
        )


@router.get('/journals')
async def list_journals(
    period_id: Optional[str] = Query(None),
    journal_status: Optional[str] = Query(None, alias='status'),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.list_journals(user.id, period_id, journal_status)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error listing journals'),
        )


@router.get('/journals/{journal_id}')
async def get_journal(
    journal_id: str,
    user=Depends(get_verified_user),
):
    result = await finance_service.get_journal(user.id, journal_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return result


@router.put('/journals/{journal_id}')
async def update_journal(
    journal_id: str,
    form_data: JournalUpdateForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.update_journal(
        user.id, journal_id, form_data.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='journal.update',
        entity_type='journal',
        entity_id=journal_id,
        period_id=result.get('period_id'),
        details=f'Updated journal {journal_id}',
    )
    return result


@router.post('/journals/{journal_id}/approve')
async def approve_journal(
    journal_id: str,
    user=Depends(get_verified_user),
):
    result = await finance_service.approve_journal(user.id, journal_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='journal.approve',
        entity_type='journal',
        entity_id=journal_id,
        period_id=result.get('period_id'),
        details=f'Approved journal {journal_id}',
    )
    return result


@router.post('/journals/{journal_id}/reject')
async def reject_journal(
    journal_id: str,
    form_data: JournalRejectForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.reject_journal(user.id, journal_id, form_data.reason)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='journal.reject',
        entity_type='journal',
        entity_id=journal_id,
        period_id=result.get('period_id'),
        details=f'Rejected journal {journal_id}: {form_data.reason}',
    )
    return result


############################
# Audit Schedule
############################


@router.post('/audit-schedule/generate')
async def generate_audit_schedule(
    form_data: AuditScheduleGenerateForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.generate_audit_schedule(user.id, form_data.period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='audit_schedule.generate',
            entity_type='audit_schedule',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Triggered audit schedule generation',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error generating audit schedule'),
        )


@router.get('/audit-schedule')
async def get_audit_schedule(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_audit_schedule(user.id, period_id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving audit schedule'),
        )


@router.get('/audit-schedule/export')
async def export_audit_schedule(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.export_audit_schedule(user.id, period_id)
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='audit_schedule.export',
            entity_type='audit_schedule',
            entity_id=period_id or 'all',
            period_id=period_id,
            details='Triggered audit schedule export to Excel',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error exporting audit schedule'),
        )


############################
# Commentary
############################


@router.post('/commentary/generate')
async def generate_commentary(
    form_data: CommentaryGenerateForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.generate_commentary(
            user.id, form_data.period_id, form_data.sections,
        )
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='commentary.generate',
            entity_type='commentary',
            entity_id=form_data.period_id,
            period_id=form_data.period_id,
            details='Triggered AI commentary generation',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error generating commentary'),
        )


@router.get('/commentary')
async def get_commentary(
    period_id: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_commentary(user.id, period_id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving commentary'),
        )


@router.put('/commentary/{commentary_id}')
async def update_commentary(
    commentary_id: str,
    form_data: CommentaryUpdateForm,
    user=Depends(get_verified_user),
):
    result = await finance_service.update_commentary(
        user.id, commentary_id, form_data.model_dump(exclude_none=True),
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='commentary.update',
        entity_type='commentary',
        entity_id=commentary_id,
        period_id=result.get('period_id'),
        details=f'Updated commentary {commentary_id}',
    )
    return result


@router.post('/commentary/{commentary_id}/approve')
async def approve_commentary(
    commentary_id: str,
    user=Depends(get_verified_user),
):
    result = await finance_service.approve_commentary(user.id, commentary_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    await finance_service.log_audit_trail(
        user_id=user.id,
        action='commentary.approve',
        entity_type='commentary',
        entity_id=commentary_id,
        period_id=result.get('period_id'),
        details=f'Approved commentary {commentary_id}',
    )
    return result


############################
# Review & Approval
############################


@router.post('/review/submit')
async def submit_for_review(
    form_data: ReviewSubmitForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.submit_for_review(user.id, form_data.model_dump())
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='review.submit',
            entity_type='review',
            entity_id=result['id'],
            period_id=form_data.period_id,
            details=f'Submitted {form_data.output_type} {form_data.output_id} for review',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error submitting for review'),
        )


@router.post('/review/approve')
async def approve_review(
    form_data: ReviewApproveForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.approve_review(user.id, form_data.model_dump())
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='review.approve',
            entity_type='review',
            entity_id=form_data.review_id,
            details=f'Approved review {form_data.review_id}',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error approving review'),
        )


@router.post('/review/reject')
async def reject_review(
    form_data: ReviewRejectForm,
    user=Depends(get_verified_user),
):
    try:
        result = await finance_service.reject_review(user.id, form_data.model_dump())
        await finance_service.log_audit_trail(
            user_id=user.id,
            action='review.reject',
            entity_type='review',
            entity_id=form_data.review_id,
            details=f'Rejected review {form_data.review_id}: {form_data.reason}',
        )
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error rejecting review'),
        )


@router.get('/review/pending')
async def get_pending_reviews(
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_pending_reviews(user.id)
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving pending reviews'),
        )


############################
# Audit Trail
############################


@router.get('/audit-trail')
async def get_audit_trail(
    period_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user=Depends(get_verified_user),
):
    try:
        return await finance_service.get_audit_trail(
            user.id,
            period_id=period_id,
            action_filter=action,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT('Error retrieving audit trail'),
        )
