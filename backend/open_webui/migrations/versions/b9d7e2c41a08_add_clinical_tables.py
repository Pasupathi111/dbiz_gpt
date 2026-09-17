"""add clinical tables

Revision ID: b9d7e2c41a08
Revises: d4c1a8e37b62
Create Date: 2026-09-17
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b9d7e2c41a08'
down_revision: Union[str, None] = 'd4c1a8e37b62'
branch_labels = None
depends_on = None


def _index_exists(inspector, index_name, table_name):
    """Check if an index already exists on the given table (works for both SQLite and PostgreSQL)."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'patient' not in tables:
        op.create_table(
            'patient',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('code', sa.Text(), nullable=False, unique=True),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('age', sa.Integer(), nullable=True),
            sa.Column('sex', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    if 'clinical_case' not in tables:
        op.create_table(
            'clinical_case',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('patient_id', sa.Text(), nullable=False),
            sa.Column('created_by_email', sa.Text(), nullable=False),
            sa.Column('created_by_name', sa.Text(), nullable=False),
            sa.Column('department', sa.Text(), nullable=False),
            sa.Column('transcript', sa.JSON(), nullable=True),
            sa.Column('structured_note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    if 'clinical_assessment' not in tables:
        op.create_table(
            'clinical_assessment',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('case_id', sa.Text(), nullable=False),
            sa.Column('author_email', sa.Text(), nullable=False),
            sa.Column('author_name', sa.Text(), nullable=False),
            sa.Column('department', sa.Text(), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    if 'clinical_referral' not in tables:
        op.create_table(
            'clinical_referral',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('case_id', sa.Text(), nullable=False),
            sa.Column('from_email', sa.Text(), nullable=False),
            sa.Column('from_name', sa.Text(), nullable=False),
            sa.Column('from_department', sa.Text(), nullable=False),
            sa.Column('to_email', sa.Text(), nullable=False),
            sa.Column('to_name', sa.Text(), nullable=False),
            sa.Column('to_department', sa.Text(), nullable=False),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('read_at', sa.BigInteger(), nullable=True),
        )

    inspector.clear_cache()
    tables = inspector.get_table_names()

    if 'clinical_case' in tables and not _index_exists(inspector, 'ix_clinical_case_patient_id', 'clinical_case'):
        op.create_index('ix_clinical_case_patient_id', 'clinical_case', ['patient_id'])

    if 'clinical_case' in tables and not _index_exists(
        inspector, 'ix_clinical_case_created_by_email', 'clinical_case'
    ):
        op.create_index('ix_clinical_case_created_by_email', 'clinical_case', ['created_by_email'])

    if 'clinical_assessment' in tables and not _index_exists(
        inspector, 'ix_clinical_assessment_case_id', 'clinical_assessment'
    ):
        op.create_index('ix_clinical_assessment_case_id', 'clinical_assessment', ['case_id'])

    if 'clinical_referral' in tables and not _index_exists(
        inspector, 'ix_clinical_referral_case_id', 'clinical_referral'
    ):
        op.create_index('ix_clinical_referral_case_id', 'clinical_referral', ['case_id'])

    if 'clinical_referral' in tables and not _index_exists(
        inspector, 'ix_clinical_referral_to_email', 'clinical_referral'
    ):
        op.create_index('ix_clinical_referral_to_email', 'clinical_referral', ['to_email'])

    if 'clinical_referral' in tables and not _index_exists(
        inspector, 'ix_clinical_referral_from_email', 'clinical_referral'
    ):
        op.create_index('ix_clinical_referral_from_email', 'clinical_referral', ['from_email'])


def downgrade():
    op.drop_index('ix_clinical_referral_from_email', table_name='clinical_referral')
    op.drop_index('ix_clinical_referral_to_email', table_name='clinical_referral')
    op.drop_index('ix_clinical_referral_case_id', table_name='clinical_referral')
    op.drop_table('clinical_referral')

    op.drop_index('ix_clinical_assessment_case_id', table_name='clinical_assessment')
    op.drop_table('clinical_assessment')

    op.drop_index('ix_clinical_case_created_by_email', table_name='clinical_case')
    op.drop_index('ix_clinical_case_patient_id', table_name='clinical_case')
    op.drop_table('clinical_case')

    op.drop_table('patient')
