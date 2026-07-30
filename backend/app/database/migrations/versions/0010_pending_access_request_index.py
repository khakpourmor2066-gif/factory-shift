"""allow repeated reviewed access requests

Revision ID: 0010_pending_access_index
Revises: 0009_api_tokens
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_pending_access_index"
down_revision = "0009_api_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_access_requests_pending_platform_messenger_user",
        "access_requests",
        type_="unique",
    )
    op.create_index(
        "uq_access_requests_pending_platform_messenger_user",
        "access_requests",
        ["platform", "messenger_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_access_requests_pending_platform_messenger_user",
        table_name="access_requests",
    )
    op.create_unique_constraint(
        "uq_access_requests_pending_platform_messenger_user",
        "access_requests",
        ["platform", "messenger_user_id", "status"],
    )
