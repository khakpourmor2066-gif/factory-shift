"""user access schema

Revision ID: 0003_user_access
Revises: 0002_shift_engine
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_user_access"
down_revision = "0002_shift_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("messenger_user_id", sa.String(length=100), nullable=True))
    op.create_index("ix_users_messenger_user_id", "users", ["messenger_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_messenger_user_id", table_name="users")
    op.drop_column("users", "messenger_user_id")
