"""webhook logs table

Revision ID: 0007_webhook_logs
Revises: 0006_access_requests
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_webhook_logs"
down_revision = "0006_access_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("messenger_user_id", sa.String(length=100), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=True),
        sa.Column("response_status", sa.String(length=50), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("sent_status", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_webhook_logs_platform", "webhook_logs", ["platform"])
    op.create_index("ix_webhook_logs_messenger_user_id", "webhook_logs", ["messenger_user_id"])
    op.create_index("ix_webhook_logs_direction", "webhook_logs", ["direction"])
    op.create_index("ix_webhook_logs_event_type", "webhook_logs", ["event_type"])
    op.create_index("ix_webhook_logs_response_status", "webhook_logs", ["response_status"])


def downgrade() -> None:
    op.drop_index("ix_webhook_logs_response_status", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_event_type", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_direction", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_messenger_user_id", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_platform", table_name="webhook_logs")
    op.drop_table("webhook_logs")
