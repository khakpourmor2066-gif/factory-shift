"""add one-time web login tickets

Revision ID: 0012_web_login_tickets
Revises: 0011_schedule_generation
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_web_login_tickets"
down_revision = "0011_schedule_generation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_login_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_web_login_tickets_user_id", "web_login_tickets", ["user_id"])
    op.create_index("ix_web_login_tickets_token_hash", "web_login_tickets", ["token_hash"])
    op.create_index("ix_web_login_tickets_expires_at", "web_login_tickets", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_web_login_tickets_expires_at", table_name="web_login_tickets")
    op.drop_index("ix_web_login_tickets_token_hash", table_name="web_login_tickets")
    op.drop_index("ix_web_login_tickets_user_id", table_name="web_login_tickets")
    op.drop_table("web_login_tickets")
