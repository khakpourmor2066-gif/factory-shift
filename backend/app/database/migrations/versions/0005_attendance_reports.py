"""attendance and reports tables

Revision ID: 0005_attendance_reports
Revises: 0004_change_management
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_attendance_reports"
down_revision = "0004_change_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("record_date", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("check_in", sa.String(length=20), nullable=True),
        sa.Column("check_out", sa.String(length=20), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("imported", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("attendance_records")
