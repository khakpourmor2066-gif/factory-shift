"""add schedule generation jobs

Revision ID: 0011_schedule_generation
Revises: 0010_pending_access_index
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_schedule_generation"
down_revision = "0010_pending_access_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_schedules_employee_date",
        "schedules",
        ["employee_id", "date"],
    )
    op.create_table(
        "schedule_generation_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("pattern_id", sa.Integer(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("preview_payload", sa.Text(), nullable=False),
        sa.Column("total_days", sa.Integer(), nullable=False),
        sa.Column("missing_days", sa.Integer(), nullable=False),
        sa.Column("created_schedules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["employee_shift_assignments.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["pattern_id"], ["shift_patterns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_generation_jobs_employee_id",
        "schedule_generation_jobs",
        ["employee_id"],
    )
    op.create_index(
        "ix_schedule_generation_jobs_status",
        "schedule_generation_jobs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_generation_jobs_status", table_name="schedule_generation_jobs")
    op.drop_index("ix_schedule_generation_jobs_employee_id", table_name="schedule_generation_jobs")
    op.drop_table("schedule_generation_jobs")
    op.drop_constraint("uq_schedules_employee_date", "schedules", type_="unique")
