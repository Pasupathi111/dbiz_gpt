import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from open_webui.internal.db import get_async_session
from open_webui.models.clinical import (
    AssessmentForm,
    AssessmentModel,
    CaseDetailModel,
    CaseForm,
    CaseModel,
    ClinicalAssessments,
    ClinicalCases,
    ClinicalReferrals,
    NoteForm,
    PatientForm,
    PatientModel,
    Patients,
    ReferralForm,
    ReferralModel,
    TranscriptForm,
    get_clinical_identity,
)
from open_webui.utils.auth import get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Patients
############################


@router.post('/patients', response_model=PatientModel)
async def create_patient(
    form_data: PatientForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    existing = await Patients.get_patient_by_code(form_data.code, db=db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Patient code {form_data.code} already exists',
        )

    patient = await Patients.insert_new_patient(form_data, db=db)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Error creating patient',
        )
    return patient


@router.get('/patients', response_model=list[PatientModel])
async def search_patients(
    q: Optional[str] = Query(None),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await Patients.search_patients(q, db=db)


@router.get('/patients/{id}', response_model=PatientModel)
async def get_patient_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    patient = await Patients.get_patient_by_id(id, db=db)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Patient not found')
    return patient


############################
# Cases
############################


@router.post('/cases', response_model=CaseModel)
async def create_case(
    form_data: CaseForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    patient = await Patients.get_patient_by_id(form_data.patient_id, db=db)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Patient not found')

    identity = get_clinical_identity(user.email, user.name)
    case = await ClinicalCases.insert_new_case(
        patient_id=form_data.patient_id,
        created_by_email=identity.email,
        created_by_name=identity.name,
        department=identity.department,
        db=db,
    )
    if not case:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Error creating case')
    return case


@router.get('/cases', response_model=list[CaseModel])
async def get_cases(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Cases the current user created, plus every case referred to them."""
    identity = get_clinical_identity(user.email, user.name)
    return await ClinicalCases.get_cases_for_email(identity.email, db=db)


@router.get('/cases/{id}', response_model=CaseDetailModel)
async def get_case_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    case = await ClinicalCases.get_case_by_id(id, db=db)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Case not found')

    assessments = await ClinicalAssessments.get_assessments_by_case_id(id, db=db)
    referrals = await ClinicalReferrals.get_referrals_by_case_id(id, db=db)

    return CaseDetailModel(
        **case.model_dump(),
        assessments=assessments,
        referrals=referrals,
    )


@router.put('/cases/{id}/transcript', response_model=CaseModel)
async def update_case_transcript(
    id: str,
    form_data: TranscriptForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    case = await ClinicalCases.update_transcript_by_id(id, form_data.transcript, db=db)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Case not found')
    return case


@router.put('/cases/{id}/note', response_model=CaseModel)
async def update_case_note(
    id: str,
    form_data: NoteForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    case = await ClinicalCases.update_note_by_id(id, form_data.structured_note, db=db)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Case not found')
    return case


############################
# Assessments (append-only)
#
# There is deliberately no update and no delete endpoint: no doctor may alter
# another doctor's findings.
############################


@router.post('/cases/{id}/assessments', response_model=AssessmentModel)
async def create_assessment(
    id: str,
    form_data: AssessmentForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    case = await ClinicalCases.get_case_by_id(id, db=db)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Case not found')

    identity = get_clinical_identity(user.email, user.name)
    assessment = await ClinicalAssessments.insert_new_assessment(
        case_id=id,
        author_email=identity.email,
        author_name=identity.name,
        department=identity.department,
        body=form_data.body,
        db=db,
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Error creating assessment')

    await ClinicalCases.touch_case_by_id(id, db=db)
    return assessment


############################
# Referrals
############################


@router.post('/referrals', response_model=ReferralModel)
async def create_referral(
    form_data: ReferralForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    case = await ClinicalCases.get_case_by_id(form_data.case_id, db=db)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Case not found')

    sender = get_clinical_identity(user.email, user.name)
    recipient = get_clinical_identity(form_data.to_email)

    referral = await ClinicalReferrals.insert_new_referral(
        case_id=form_data.case_id,
        from_email=sender.email,
        from_name=sender.name,
        from_department=sender.department,
        to_email=recipient.email,
        to_name=recipient.name,
        to_department=recipient.department,
        note=form_data.note,
        db=db,
    )
    if not referral:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Error creating referral')

    await ClinicalCases.touch_case_by_id(form_data.case_id, db=db)

    referral.patient_code = case.patient_code
    referral.patient_name = case.patient_name
    return referral


@router.get('/referrals/inbox', response_model=list[ReferralModel])
async def get_referrals_inbox(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    identity = get_clinical_identity(user.email, user.name)
    return await ClinicalReferrals.get_inbox_referrals(identity.email, db=db)


@router.get('/referrals/sent', response_model=list[ReferralModel])
async def get_referrals_sent(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    identity = get_clinical_identity(user.email, user.name)
    return await ClinicalReferrals.get_sent_referrals(identity.email, db=db)


@router.post('/referrals/{id}/read', response_model=ReferralModel)
async def mark_referral_read(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    referral = await ClinicalReferrals.mark_referral_read_by_id(id, db=db)
    if not referral:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Referral not found')

    case = await ClinicalCases.get_case_by_id(referral.case_id, db=db)
    if case:
        referral.patient_code = case.patient_code
        referral.patient_name = case.patient_name
    return referral
