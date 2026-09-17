import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Integer, Text, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


####################
# Clinical Referral DB Schema
#
# A patient is interviewed once, by one doctor. The conversation and every
# assessment written on top of it travel with the case as it is referred
# between departments, so the patient never has to repeat themselves.
####################


####################
# Demo identity map
####################

CLINICAL_DEPARTMENT_UNKNOWN = 'Unknown'

CLINICAL_IDENTITIES: dict[str, dict[str, str]] = {
    'cardiology@dbiz.local': {'name': 'Dr. Chandru', 'department': 'Cardiology'},
    'neurology@dbiz.local': {'name': 'Dr. Naveen', 'department': 'Neurology'},
    'surgery@dbiz.local': {'name': 'Dr. Pasupathi', 'department': 'General Surgery'},
}


class ClinicalIdentity(BaseModel):
    email: str
    name: str
    department: str


def get_clinical_identity(email: Optional[str], fallback_name: Optional[str] = None) -> ClinicalIdentity:
    """Resolve a demo doctor identity from an email address.

    Emails outside the hardcoded map fall back to the caller-supplied name and
    an ``Unknown`` department -- never an error, this is a demo.
    """
    normalized_email = (email or '').strip().lower()
    identity = CLINICAL_IDENTITIES.get(normalized_email)
    if identity:
        return ClinicalIdentity(
            email=normalized_email,
            name=identity['name'],
            department=identity['department'],
        )
    return ClinicalIdentity(
        email=normalized_email,
        name=(fallback_name or normalized_email or CLINICAL_DEPARTMENT_UNKNOWN),
        department=CLINICAL_DEPARTMENT_UNKNOWN,
    )


####################
# Tables
####################


class Patient(Base):
    __tablename__ = 'patient'
    id = Column(Text, primary_key=True, unique=True)
    code = Column(Text, unique=True)
    name = Column(Text)
    age = Column(Integer, nullable=True)
    sex = Column(Text, nullable=True)
    created_at = Column(BigInteger)


class ClinicalCase(Base):
    __tablename__ = 'clinical_case'
    id = Column(Text, primary_key=True, unique=True)
    patient_id = Column(Text)
    created_by_email = Column(Text)
    created_by_name = Column(Text)
    department = Column(Text)
    transcript = Column(JSON, nullable=True)
    structured_note = Column(Text, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ClinicalAssessment(Base):
    __tablename__ = 'clinical_assessment'
    id = Column(Text, primary_key=True, unique=True)
    case_id = Column(Text)
    author_email = Column(Text)
    author_name = Column(Text)
    department = Column(Text)
    body = Column(Text)
    created_at = Column(BigInteger)


class ClinicalReferral(Base):
    __tablename__ = 'clinical_referral'
    id = Column(Text, primary_key=True, unique=True)
    case_id = Column(Text)
    from_email = Column(Text)
    from_name = Column(Text)
    from_department = Column(Text)
    to_email = Column(Text)
    to_name = Column(Text)
    to_department = Column(Text)
    note = Column(Text)
    created_at = Column(BigInteger)
    read_at = Column(BigInteger, nullable=True)


####################
# Pydantic models
####################


class TranscriptEntry(BaseModel):
    speaker: str
    text: str
    at: Optional[int | str] = None

    model_config = ConfigDict(extra='allow')


class PatientModel(BaseModel):
    id: str
    code: str
    name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class CaseModel(BaseModel):
    id: str
    patient_id: str
    created_by_email: str
    created_by_name: str
    department: str
    transcript: list[TranscriptEntry] = []
    structured_note: Optional[str] = None
    created_at: int
    updated_at: int

    # Joined from the patient table -- the UI pins these at the top of every
    # view and must never have to make a second call.
    patient_code: Optional[str] = None
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentModel(BaseModel):
    id: str
    case_id: str
    author_email: str
    author_name: str
    department: str
    body: str
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class ReferralModel(BaseModel):
    id: str
    case_id: str
    from_email: str
    from_name: str
    from_department: str
    to_email: str
    to_name: str
    to_department: str
    note: Optional[str] = None
    created_at: int
    read_at: Optional[int] = None

    # Joined from the case + patient tables (inbox / sent listings).
    patient_code: Optional[str] = None
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CaseDetailModel(CaseModel):
    assessments: list[AssessmentModel] = []
    referrals: list[ReferralModel] = []


####################
# Forms
####################


class PatientForm(BaseModel):
    code: str
    name: str
    age: Optional[int] = None
    sex: Optional[str] = None


class CaseForm(BaseModel):
    patient_id: str


class TranscriptForm(BaseModel):
    transcript: list[TranscriptEntry] = []


class NoteForm(BaseModel):
    structured_note: str


class AssessmentForm(BaseModel):
    body: str


class ReferralForm(BaseModel):
    case_id: str
    to_email: str
    note: Optional[str] = None


####################
# Helpers
####################


def _transcript_to_json(transcript: Optional[list[TranscriptEntry]]) -> list[dict]:
    return [entry.model_dump() for entry in (transcript or [])]


def _case_model(case: ClinicalCase, patient: Optional[Patient] = None) -> CaseModel:
    model = CaseModel.model_validate(case)
    if patient is not None:
        model.patient_code = patient.code
        model.patient_name = patient.name
    return model


def _referral_model(referral: ClinicalReferral, patient: Optional[Patient] = None) -> ReferralModel:
    model = ReferralModel.model_validate(referral)
    if patient is not None:
        model.patient_code = patient.code
        model.patient_name = patient.name
    return model


####################
# Table operations
####################


class PatientTable:
    async def insert_new_patient(
        self, form_data: PatientForm, db: Optional[AsyncSession] = None
    ) -> Optional[PatientModel]:
        async with get_async_db_context(db) as db:
            patient = PatientModel(
                **{
                    'id': str(uuid.uuid4()),
                    **form_data.model_dump(),
                    'created_at': int(time.time()),
                }
            )
            try:
                result = Patient(**patient.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return PatientModel.model_validate(result)
            except Exception as e:
                log.exception(f'Error inserting a new patient: {e}')
                return None

    async def get_patient_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[PatientModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Patient).filter_by(id=id))
            patient = result.scalars().first()
            if not patient:
                return None
            return PatientModel.model_validate(patient)

    async def get_patient_by_code(self, code: str, db: Optional[AsyncSession] = None) -> Optional[PatientModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Patient).filter_by(code=code))
            patient = result.scalars().first()
            if not patient:
                return None
            return PatientModel.model_validate(patient)

    async def search_patients(
        self, query: Optional[str] = None, db: Optional[AsyncSession] = None
    ) -> list[PatientModel]:
        async with get_async_db_context(db) as db:
            statement = select(Patient)
            query = (query or '').strip()
            if query:
                pattern = f'%{query}%'
                statement = statement.filter(or_(Patient.code.ilike(pattern), Patient.name.ilike(pattern)))
            statement = statement.order_by(Patient.created_at.desc())
            result = await db.execute(statement)
            return [PatientModel.model_validate(patient) for patient in result.scalars().all()]


class ClinicalCaseTable:
    async def insert_new_case(
        self,
        patient_id: str,
        created_by_email: str,
        created_by_name: str,
        department: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[CaseModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            try:
                result = ClinicalCase(
                    id=str(uuid.uuid4()),
                    patient_id=patient_id,
                    created_by_email=created_by_email,
                    created_by_name=created_by_name,
                    department=department,
                    transcript=[],
                    structured_note=None,
                    created_at=now,
                    updated_at=now,
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return await self.get_case_by_id(result.id, db=db)
            except Exception as e:
                log.exception(f'Error inserting a new clinical case: {e}')
                return None

    async def get_case_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[CaseModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ClinicalCase, Patient)
                .outerjoin(Patient, Patient.id == ClinicalCase.patient_id)
                .filter(ClinicalCase.id == id)
            )
            row = result.first()
            if not row:
                return None
            case, patient = row
            return _case_model(case, patient)

    async def get_cases_for_email(self, email: str, db: Optional[AsyncSession] = None) -> list[CaseModel]:
        """Cases the user created, plus every case that has been referred to them."""
        async with get_async_db_context(db) as db:
            referred_case_ids = select(ClinicalReferral.case_id).filter(ClinicalReferral.to_email == email)
            result = await db.execute(
                select(ClinicalCase, Patient)
                .outerjoin(Patient, Patient.id == ClinicalCase.patient_id)
                .filter(
                    or_(
                        ClinicalCase.created_by_email == email,
                        ClinicalCase.id.in_(referred_case_ids),
                    )
                )
                .order_by(ClinicalCase.updated_at.desc())
            )
            return [_case_model(case, patient) for case, patient in result.all()]

    async def update_transcript_by_id(
        self, id: str, transcript: list[TranscriptEntry], db: Optional[AsyncSession] = None
    ) -> Optional[CaseModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ClinicalCase).filter_by(id=id))
            case = result.scalars().first()
            if not case:
                return None

            case.transcript = _transcript_to_json(transcript)
            case.updated_at = int(time.time())
            await db.commit()
            return await self.get_case_by_id(id, db=db)

    async def update_note_by_id(
        self, id: str, structured_note: str, db: Optional[AsyncSession] = None
    ) -> Optional[CaseModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ClinicalCase).filter_by(id=id))
            case = result.scalars().first()
            if not case:
                return None

            case.structured_note = structured_note
            case.updated_at = int(time.time())
            await db.commit()
            return await self.get_case_by_id(id, db=db)

    async def touch_case_by_id(self, id: str, db: Optional[AsyncSession] = None) -> None:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ClinicalCase).filter_by(id=id))
            case = result.scalars().first()
            if not case:
                return
            case.updated_at = int(time.time())
            await db.commit()


class ClinicalAssessmentTable:
    """Append-only.

    There is deliberately no update and no delete: no doctor may alter another
    doctor's findings.
    """

    async def insert_new_assessment(
        self,
        case_id: str,
        author_email: str,
        author_name: str,
        department: str,
        body: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[AssessmentModel]:
        async with get_async_db_context(db) as db:
            try:
                result = ClinicalAssessment(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    author_email=author_email,
                    author_name=author_name,
                    department=department,
                    body=body,
                    created_at=int(time.time()),
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return AssessmentModel.model_validate(result)
            except Exception as e:
                log.exception(f'Error inserting a new clinical assessment: {e}')
                return None

    async def get_assessments_by_case_id(
        self, case_id: str, db: Optional[AsyncSession] = None
    ) -> list[AssessmentModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ClinicalAssessment)
                .filter(ClinicalAssessment.case_id == case_id)
                .order_by(ClinicalAssessment.created_at.asc())
            )
            return [AssessmentModel.model_validate(assessment) for assessment in result.scalars().all()]


class ClinicalReferralTable:
    async def insert_new_referral(
        self,
        case_id: str,
        from_email: str,
        from_name: str,
        from_department: str,
        to_email: str,
        to_name: str,
        to_department: str,
        note: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ReferralModel]:
        async with get_async_db_context(db) as db:
            try:
                result = ClinicalReferral(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    from_email=from_email,
                    from_name=from_name,
                    from_department=from_department,
                    to_email=to_email,
                    to_name=to_name,
                    to_department=to_department,
                    note=note,
                    created_at=int(time.time()),
                    read_at=None,
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return ReferralModel.model_validate(result)
            except Exception as e:
                log.exception(f'Error inserting a new clinical referral: {e}')
                return None

    async def get_referrals_by_case_id(self, case_id: str, db: Optional[AsyncSession] = None) -> list[ReferralModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ClinicalReferral)
                .filter(ClinicalReferral.case_id == case_id)
                .order_by(ClinicalReferral.created_at.asc())
            )
            return [ReferralModel.model_validate(referral) for referral in result.scalars().all()]

    async def _get_enriched_referrals(self, statement, db: Optional[AsyncSession] = None) -> list[ReferralModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                statement.outerjoin(ClinicalCase, ClinicalCase.id == ClinicalReferral.case_id)
                .outerjoin(Patient, Patient.id == ClinicalCase.patient_id)
                .order_by(ClinicalReferral.created_at.desc())
            )
            return [_referral_model(referral, patient) for referral, patient in result.all()]

    async def get_inbox_referrals(self, email: str, db: Optional[AsyncSession] = None) -> list[ReferralModel]:
        statement = select(ClinicalReferral, Patient).filter(ClinicalReferral.to_email == email)
        return await self._get_enriched_referrals(statement, db=db)

    async def get_sent_referrals(self, email: str, db: Optional[AsyncSession] = None) -> list[ReferralModel]:
        statement = select(ClinicalReferral, Patient).filter(ClinicalReferral.from_email == email)
        return await self._get_enriched_referrals(statement, db=db)

    async def get_referral_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ReferralModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ClinicalReferral).filter_by(id=id))
            referral = result.scalars().first()
            if not referral:
                return None
            return ReferralModel.model_validate(referral)

    async def mark_referral_read_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ReferralModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ClinicalReferral).filter_by(id=id))
            referral = result.scalars().first()
            if not referral:
                return None

            if not referral.read_at:
                referral.read_at = int(time.time())
                await db.commit()
                await db.refresh(referral)
            return ReferralModel.model_validate(referral)


Patients = PatientTable()
ClinicalCases = ClinicalCaseTable()
ClinicalAssessments = ClinicalAssessmentTable()
ClinicalReferrals = ClinicalReferralTable()
