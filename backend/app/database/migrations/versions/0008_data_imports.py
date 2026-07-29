"""managed data imports

Revision ID: 0008_data_imports
Revises: 0007_webhook_logs
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_data_imports"
down_revision = "0007_webhook_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("shift_name", sa.String(length=100), nullable=True))
    op.add_column("schedules", sa.Column("shift_code", sa.String(length=50), nullable=True))
    op.add_column("schedules", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("schedules", sa.Column("end_time", sa.Time(), nullable=True))
    op.add_column("schedules", sa.Column("location", sa.String(length=150), nullable=True))
    op.add_column("schedules", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("schedules", sa.Column("source", sa.String(length=100), nullable=True))
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_type", sa.String(length=30), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("snapshot_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_import_jobs_import_type", "import_jobs", ["import_type"])
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"])
    op.create_table(
        "import_errors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("import_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_data_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_import_errors_job_id", "import_errors", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_import_errors_job_id", table_name="import_errors")
    op.drop_table("import_errors")
    op.drop_index("ix_import_jobs_status", table_name="import_jobs")
    op.drop_index("ix_import_jobs_import_type", table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_column("schedules", "source")
    op.drop_column("schedules", "note")
    op.drop_column("schedules", "location")
    op.drop_column("schedules", "end_time")
    op.drop_column("schedules", "start_time")
    op.drop_column("schedules", "shift_code")
    op.drop_column("schedules", "shift_name")
