"""add finance tables (all 17 Bond Copilot domain tables)

Revision ID: aa99cc88bb77
Revises: d4c1a8e37b62
Create Date: 2026-09-16 17:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from open_webui.migrations.util import get_existing_tables

revision: str = "aa99cc88bb77"
down_revision: Union[str, None] = "d4c1a8e37b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(inspector, index_name, table_name):
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    existing_tables = set(get_existing_tables())
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "finance_reporting_period" not in existing_tables:
        op.create_table(
            "finance_reporting_period",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("month", sa.Integer(), nullable=True),
            sa.Column("previous_period_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_reporting_period_created_at",
            "finance_reporting_period",
            ["created_at"],
            unique=False,
        )

    if "finance_document" not in existing_tables:
        op.create_table(
            "finance_document",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("document_type", sa.String(), nullable=True),
            sa.Column("filename", sa.String(), nullable=True),
            sa.Column("original_filename", sa.String(), nullable=True),
            sa.Column("file_path", sa.Text(), nullable=True),
            sa.Column("file_size", sa.BigInteger(), nullable=True),
            sa.Column("file_hash", sa.String(), nullable=True),
            sa.Column("mime_type", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("validation_status", sa.String(), nullable=True),
            sa.Column("validation_messages", sa.JSON(), nullable=True),
            sa.Column("uploaded_by", sa.String(), nullable=True),
            sa.Column("processed_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_document_period_id",
            "finance_document",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_document_status", "finance_document", ["status"], unique=False
        )
        op.create_index(
            "ix_finance_document_created_at",
            "finance_document",
            ["created_at"],
            unique=False,
        )

    if "finance_extraction_job" not in existing_tables:
        op.create_table(
            "finance_extraction_job",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("extraction_type", sa.String(), nullable=True),
            sa.Column("records_extracted", sa.Integer(), nullable=True),
            sa.Column("errors", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.BigInteger(), nullable=True),
            sa.Column("completed_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_extraction_job_document_id",
            "finance_extraction_job",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_extraction_job_status",
            "finance_extraction_job",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_finance_extraction_job_created_at",
            "finance_extraction_job",
            ["created_at"],
            unique=False,
        )

    if "finance_bond_record" not in existing_tables:
        op.create_table(
            "finance_bond_record",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("isin", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("issuer", sa.String(), nullable=True),
            sa.Column("currency", sa.String(), nullable=True),
            sa.Column("face_value", sa.Float(), nullable=True),
            sa.Column("book_value", sa.Float(), nullable=True),
            sa.Column("market_value", sa.Float(), nullable=True),
            sa.Column("coupon_rate", sa.Float(), nullable=True),
            sa.Column("accrued_interest", sa.Float(), nullable=True),
            sa.Column("maturity_date", sa.String(), nullable=True),
            sa.Column("purchase_date", sa.String(), nullable=True),
            sa.Column("settlement_date", sa.String(), nullable=True),
            sa.Column("quantity", sa.Float(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("source_document_id", sa.String(), nullable=True),
            sa.Column("source_type", sa.String(), nullable=True),
            sa.Column("extraction_confidence", sa.Float(), nullable=True),
            sa.Column("is_validated", sa.Boolean(), nullable=True),
            sa.Column("validated_by", sa.String(), nullable=True),
            sa.Column("validated_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_bond_record_period_id",
            "finance_bond_record",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_record_bond_id",
            "finance_bond_record",
            ["bond_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_record_isin",
            "finance_bond_record",
            ["isin"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_record_status",
            "finance_bond_record",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_record_created_at",
            "finance_bond_record",
            ["created_at"],
            unique=False,
        )

    if "finance_bond_source_record" not in existing_tables:
        op.create_table(
            "finance_bond_source_record",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("bond_record_id", sa.String(), nullable=True),
            sa.Column("document_id", sa.String(), nullable=True),
            sa.Column("source_type", sa.String(), nullable=True),
            sa.Column("raw_data", sa.JSON(), nullable=True),
            sa.Column("sheet_name", sa.String(), nullable=True),
            sa.Column("row_number", sa.Integer(), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("cell_references", sa.JSON(), nullable=True),
            sa.Column("extraction_confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["bond_record_id"],
                ["finance_bond_record.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_finance_bond_source_record_bond_record_id",
            "finance_bond_source_record",
            ["bond_record_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_source_record_document_id",
            "finance_bond_source_record",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_source_record_created_at",
            "finance_bond_source_record",
            ["created_at"],
            unique=False,
        )

    if "finance_reconciliation_run" not in existing_tables:
        op.create_table(
            "finance_reconciliation_run",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("total_bonds", sa.Integer(), nullable=True),
            sa.Column("matched", sa.Integer(), nullable=True),
            sa.Column("variances", sa.Integer(), nullable=True),
            sa.Column("missing", sa.Integer(), nullable=True),
            sa.Column("duplicates", sa.Integer(), nullable=True),
            sa.Column("match_rate", sa.Float(), nullable=True),
            sa.Column("run_by", sa.String(), nullable=True),
            sa.Column("started_at", sa.BigInteger(), nullable=False),
            sa.Column("completed_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_reconciliation_run_period_id",
            "finance_reconciliation_run",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_reconciliation_run_status",
            "finance_reconciliation_run",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_finance_reconciliation_run_created_at",
            "finance_reconciliation_run",
            ["created_at"],
            unique=False,
        )

    if "finance_reconciliation_item" not in existing_tables:
        op.create_table(
            "finance_reconciliation_item",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reconciliation_run_id", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("isin", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("ubs_value", sa.Float(), nullable=True),
            sa.Column("lgi_value", sa.Float(), nullable=True),
            sa.Column("schedule_value", sa.Float(), nullable=True),
            sa.Column("previous_value", sa.Float(), nullable=True),
            sa.Column("variance_amount", sa.Float(), nullable=True),
            sa.Column("variance_percentage", sa.Float(), nullable=True),
            sa.Column("field_name", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("ai_explanation", sa.Text(), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("resolved_by", sa.String(), nullable=True),
            sa.Column("resolved_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["reconciliation_run_id"],
                ["finance_reconciliation_run.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_finance_reconciliation_item_run_id",
            "finance_reconciliation_item",
            ["reconciliation_run_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_reconciliation_item_bond_id",
            "finance_reconciliation_item",
            ["bond_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_reconciliation_item_status",
            "finance_reconciliation_item",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_finance_reconciliation_item_created_at",
            "finance_reconciliation_item",
            ["created_at"],
            unique=False,
        )

    if "finance_bond_movement" not in existing_tables:
        op.create_table(
            "finance_bond_movement",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("isin", sa.String(), nullable=True),
            sa.Column("movement_type", sa.String(), nullable=True),
            sa.Column("previous_value", sa.Float(), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("variance", sa.Float(), nullable=True),
            sa.Column("previous_status", sa.String(), nullable=True),
            sa.Column("current_status", sa.String(), nullable=True),
            sa.Column("ai_explanation", sa.Text(), nullable=True),
            sa.Column("explanation_confidence", sa.Float(), nullable=True),
            sa.Column("is_approved", sa.Boolean(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("approved_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_bond_movement_period_id",
            "finance_bond_movement",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_movement_bond_id",
            "finance_bond_movement",
            ["bond_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_movement_type",
            "finance_bond_movement",
            ["movement_type"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_movement_created_at",
            "finance_bond_movement",
            ["created_at"],
            unique=False,
        )

    if "finance_bond_schedule_line" not in existing_tables:
        op.create_table(
            "finance_bond_schedule_line",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("isin", sa.String(), nullable=True),
            sa.Column("issuer", sa.String(), nullable=True),
            sa.Column("currency", sa.String(), nullable=True),
            sa.Column("face_value", sa.Float(), nullable=True),
            sa.Column("book_value", sa.Float(), nullable=True),
            sa.Column("market_value", sa.Float(), nullable=True),
            sa.Column("coupon_rate", sa.Float(), nullable=True),
            sa.Column("maturity_date", sa.String(), nullable=True),
            sa.Column("accrued_interest", sa.Float(), nullable=True),
            sa.Column("movement_type", sa.String(), nullable=True),
            sa.Column("variance", sa.Float(), nullable=True),
            sa.Column("source_document_id", sa.String(), nullable=True),
            sa.Column("validation_status", sa.String(), nullable=True),
            sa.Column("validation_messages", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_bond_schedule_line_period_id",
            "finance_bond_schedule_line",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_schedule_line_bond_id",
            "finance_bond_schedule_line",
            ["bond_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_bond_schedule_line_created_at",
            "finance_bond_schedule_line",
            ["created_at"],
            unique=False,
        )

    if "finance_journal" not in existing_tables:
        op.create_table(
            "finance_journal",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("journal_number", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("total_debit", sa.Float(), nullable=True),
            sa.Column("total_credit", sa.Float(), nullable=True),
            sa.Column("is_balanced", sa.Boolean(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("ai_rationale", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("reviewed_by", sa.String(), nullable=True),
            sa.Column("reviewed_at", sa.BigInteger(), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_journal_period_id",
            "finance_journal",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_journal_number",
            "finance_journal",
            ["journal_number"],
            unique=False,
        )
        op.create_index(
            "ix_finance_journal_status", "finance_journal", ["status"], unique=False
        )
        op.create_index(
            "ix_finance_journal_created_at",
            "finance_journal",
            ["created_at"],
            unique=False,
        )

    if "finance_journal_line" not in existing_tables:
        op.create_table(
            "finance_journal_line",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("journal_id", sa.String(), nullable=True),
            sa.Column("line_number", sa.Integer(), nullable=True),
            sa.Column("account_code", sa.String(), nullable=True),
            sa.Column("account_description", sa.String(), nullable=True),
            sa.Column("debit", sa.Float(), nullable=True),
            sa.Column("credit", sa.Float(), nullable=True),
            sa.Column("currency", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_reference", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["journal_id"], ["finance_journal.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_finance_journal_line_journal_id",
            "finance_journal_line",
            ["journal_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_journal_line_account_code",
            "finance_journal_line",
            ["account_code"],
            unique=False,
        )
        op.create_index(
            "ix_finance_journal_line_created_at",
            "finance_journal_line",
            ["created_at"],
            unique=False,
        )

    if "finance_audit_schedule_entry" not in existing_tables:
        op.create_table(
            "finance_audit_schedule_entry",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("opening_balance", sa.Float(), nullable=True),
            sa.Column("purchases", sa.Float(), nullable=True),
            sa.Column("sales", sa.Float(), nullable=True),
            sa.Column("maturities", sa.Float(), nullable=True),
            sa.Column("transfers", sa.Float(), nullable=True),
            sa.Column("interest", sa.Float(), nullable=True),
            sa.Column("fair_value_changes", sa.Float(), nullable=True),
            sa.Column("closing_balance", sa.Float(), nullable=True),
            sa.Column("source_references", sa.JSON(), nullable=True),
            sa.Column("reconciliation_status", sa.String(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_audit_schedule_entry_period_id",
            "finance_audit_schedule_entry",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_audit_schedule_entry_bond_id",
            "finance_audit_schedule_entry",
            ["bond_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_audit_schedule_entry_created_at",
            "finance_audit_schedule_entry",
            ["created_at"],
            unique=False,
        )

    if "finance_commentary" not in existing_tables:
        op.create_table(
            "finance_commentary",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("generated_by_ai", sa.Boolean(), nullable=True),
            sa.Column("edited_by", sa.String(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("approved_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_commentary_period_id",
            "finance_commentary",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_commentary_content_type",
            "finance_commentary",
            ["content_type"],
            unique=False,
        )
        op.create_index(
            "ix_finance_commentary_status",
            "finance_commentary",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_finance_commentary_created_at",
            "finance_commentary",
            ["created_at"],
            unique=False,
        )

    if "finance_approval" not in existing_tables:
        op.create_table(
            "finance_approval",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("object_type", sa.String(), nullable=True),
            sa.Column("object_id", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=True),
            sa.Column("previous_status", sa.String(), nullable=True),
            sa.Column("new_status", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("user_role", sa.String(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_approval_period_id",
            "finance_approval",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_approval_object",
            "finance_approval",
            ["object_type", "object_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_approval_user_id",
            "finance_approval",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_approval_created_at",
            "finance_approval",
            ["created_at"],
            unique=False,
        )

    if "finance_exception" not in existing_tables:
        op.create_table(
            "finance_exception",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("severity", sa.String(), nullable=True),
            sa.Column("bond_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("ai_recommendation", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("resolved_by", sa.String(), nullable=True),
            sa.Column("resolved_at", sa.BigInteger(), nullable=True),
            sa.Column("source_reference", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_exception_period_id",
            "finance_exception",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_exception_category",
            "finance_exception",
            ["category"],
            unique=False,
        )
        op.create_index(
            "ix_finance_exception_severity",
            "finance_exception",
            ["severity"],
            unique=False,
        )
        op.create_index(
            "ix_finance_exception_bond_id",
            "finance_exception",
            ["bond_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_exception_status",
            "finance_exception",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_finance_exception_created_at",
            "finance_exception",
            ["created_at"],
            unique=False,
        )

    if "finance_audit_log" not in existing_tables:
        op.create_table(
            "finance_audit_log",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("reporting_period_id", sa.String(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=True),
            sa.Column("object_type", sa.String(), nullable=True),
            sa.Column("object_id", sa.String(), nullable=True),
            sa.Column("previous_value", sa.JSON(), nullable=True),
            sa.Column("new_value", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_audit_log_period_id",
            "finance_audit_log",
            ["reporting_period_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_audit_log_user_id",
            "finance_audit_log",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_audit_log_action",
            "finance_audit_log",
            ["action"],
            unique=False,
        )
        op.create_index(
            "ix_finance_audit_log_created_at",
            "finance_audit_log",
            ["created_at"],
            unique=False,
        )

    if "finance_source_reference" not in existing_tables:
        op.create_table(
            "finance_source_reference",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("bond_record_id", sa.String(), nullable=True),
            sa.Column("document_id", sa.String(), nullable=True),
            sa.Column("field_name", sa.String(), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("source_type", sa.String(), nullable=True),
            sa.Column("sheet_name", sa.String(), nullable=True),
            sa.Column("row_number", sa.Integer(), nullable=True),
            sa.Column("column_name", sa.String(), nullable=True),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("cell_reference", sa.String(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_finance_source_reference_bond_record_id",
            "finance_source_reference",
            ["bond_record_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_source_reference_document_id",
            "finance_source_reference",
            ["document_id"],
            unique=False,
        )
        op.create_index(
            "ix_finance_source_reference_created_at",
            "finance_source_reference",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_finance_source_reference_created_at", table_name="finance_source_reference")
    op.drop_index("ix_finance_source_reference_document_id", table_name="finance_source_reference")
    op.drop_index("ix_finance_source_reference_bond_record_id", table_name="finance_source_reference")
    op.drop_table("finance_source_reference")

    op.drop_index("ix_finance_audit_log_created_at", table_name="finance_audit_log")
    op.drop_index("ix_finance_audit_log_action", table_name="finance_audit_log")
    op.drop_index("ix_finance_audit_log_user_id", table_name="finance_audit_log")
    op.drop_index("ix_finance_audit_log_period_id", table_name="finance_audit_log")
    op.drop_table("finance_audit_log")

    op.drop_index("ix_finance_exception_created_at", table_name="finance_exception")
    op.drop_index("ix_finance_exception_status", table_name="finance_exception")
    op.drop_index("ix_finance_exception_bond_id", table_name="finance_exception")
    op.drop_index("ix_finance_exception_severity", table_name="finance_exception")
    op.drop_index("ix_finance_exception_category", table_name="finance_exception")
    op.drop_index("ix_finance_exception_period_id", table_name="finance_exception")
    op.drop_table("finance_exception")

    op.drop_index("ix_finance_approval_created_at", table_name="finance_approval")
    op.drop_index("ix_finance_approval_user_id", table_name="finance_approval")
    op.drop_index("ix_finance_approval_object", table_name="finance_approval")
    op.drop_index("ix_finance_approval_period_id", table_name="finance_approval")
    op.drop_table("finance_approval")

    op.drop_index("ix_finance_commentary_created_at", table_name="finance_commentary")
    op.drop_index("ix_finance_commentary_status", table_name="finance_commentary")
    op.drop_index("ix_finance_commentary_content_type", table_name="finance_commentary")
    op.drop_index("ix_finance_commentary_period_id", table_name="finance_commentary")
    op.drop_table("finance_commentary")

    op.drop_index("ix_finance_audit_schedule_entry_created_at", table_name="finance_audit_schedule_entry")
    op.drop_index("ix_finance_audit_schedule_entry_bond_id", table_name="finance_audit_schedule_entry")
    op.drop_index("ix_finance_audit_schedule_entry_period_id", table_name="finance_audit_schedule_entry")
    op.drop_table("finance_audit_schedule_entry")

    op.drop_index("ix_finance_journal_line_created_at", table_name="finance_journal_line")
    op.drop_index("ix_finance_journal_line_account_code", table_name="finance_journal_line")
    op.drop_index("ix_finance_journal_line_journal_id", table_name="finance_journal_line")
    op.drop_table("finance_journal_line")

    op.drop_index("ix_finance_journal_created_at", table_name="finance_journal")
    op.drop_index("ix_finance_journal_status", table_name="finance_journal")
    op.drop_index("ix_finance_journal_number", table_name="finance_journal")
    op.drop_index("ix_finance_journal_period_id", table_name="finance_journal")
    op.drop_table("finance_journal")

    op.drop_index("ix_finance_bond_schedule_line_created_at", table_name="finance_bond_schedule_line")
    op.drop_index("ix_finance_bond_schedule_line_bond_id", table_name="finance_bond_schedule_line")
    op.drop_index("ix_finance_bond_schedule_line_period_id", table_name="finance_bond_schedule_line")
    op.drop_table("finance_bond_schedule_line")

    op.drop_index("ix_finance_bond_movement_created_at", table_name="finance_bond_movement")
    op.drop_index("ix_finance_bond_movement_type", table_name="finance_bond_movement")
    op.drop_index("ix_finance_bond_movement_bond_id", table_name="finance_bond_movement")
    op.drop_index("ix_finance_bond_movement_period_id", table_name="finance_bond_movement")
    op.drop_table("finance_bond_movement")

    op.drop_index("ix_finance_reconciliation_item_created_at", table_name="finance_reconciliation_item")
    op.drop_index("ix_finance_reconciliation_item_status", table_name="finance_reconciliation_item")
    op.drop_index("ix_finance_reconciliation_item_bond_id", table_name="finance_reconciliation_item")
    op.drop_index("ix_finance_reconciliation_item_run_id", table_name="finance_reconciliation_item")
    op.drop_table("finance_reconciliation_item")

    op.drop_index("ix_finance_reconciliation_run_created_at", table_name="finance_reconciliation_run")
    op.drop_index("ix_finance_reconciliation_run_status", table_name="finance_reconciliation_run")
    op.drop_index("ix_finance_reconciliation_run_period_id", table_name="finance_reconciliation_run")
    op.drop_table("finance_reconciliation_run")

    op.drop_index("ix_finance_bond_source_record_created_at", table_name="finance_bond_source_record")
    op.drop_index("ix_finance_bond_source_record_document_id", table_name="finance_bond_source_record")
    op.drop_index("ix_finance_bond_source_record_bond_record_id", table_name="finance_bond_source_record")
    op.drop_table("finance_bond_source_record")

    op.drop_index("ix_finance_bond_record_created_at", table_name="finance_bond_record")
    op.drop_index("ix_finance_bond_record_status", table_name="finance_bond_record")
    op.drop_index("ix_finance_bond_record_isin", table_name="finance_bond_record")
    op.drop_index("ix_finance_bond_record_bond_id", table_name="finance_bond_record")
    op.drop_index("ix_finance_bond_record_period_id", table_name="finance_bond_record")
    op.drop_table("finance_bond_record")

    op.drop_index("ix_finance_extraction_job_created_at", table_name="finance_extraction_job")
    op.drop_index("ix_finance_extraction_job_status", table_name="finance_extraction_job")
    op.drop_index("ix_finance_extraction_job_document_id", table_name="finance_extraction_job")
    op.drop_table("finance_extraction_job")

    op.drop_index("ix_finance_document_created_at", table_name="finance_document")
    op.drop_index("ix_finance_document_status", table_name="finance_document")
    op.drop_index("ix_finance_document_period_id", table_name="finance_document")
    op.drop_table("finance_document")

    op.drop_index("ix_finance_reporting_period_created_at", table_name="finance_reporting_period")
    op.drop_table("finance_reporting_period")
