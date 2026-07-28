"""access request table

Revision ID: 0006_access_requests
Revises: 0005_attendance_reports
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_access_requests"
down_revision = "0005_attendance_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("messenger_user_id", sa.String(length=100), nullable=False),
        sa.Column("latest_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_access_requests_platform", "access_requests", ["platform"])
    op.create_index("ix_access_requests_messenger_user_id", "access_requests", ["messenger_user_id"])
    op.create_index("ix_access_requests_status", "access_requests", ["status"])
    op.create_unique_constraint(
        "uq_access_requests_pending_platform_messenger_user",
        "access_requests",
        ["platform", "messenger_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_access_requests_pending_platform_messenger_user", "access_requests", type_="unique")
    op.drop_index("ix_access_requests_status", table_name="access_requests")
    op.drop_index("ix_access_requests_messenger_user_id", table_name="access_requests")
    op.drop_index("ix_access_requests_platform", table_name="access_requests")
    op.drop_table("access_requests")
