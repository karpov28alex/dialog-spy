"""add user activity logs

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("object_type", sa.String(length=32), nullable=True),
        sa.Column("object_id", sa.String(length=128), nullable=True),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_activity_logs_user_id", "user_activity_logs", ["user_id"])
    op.create_index("ix_user_activity_logs_telegram_id", "user_activity_logs", ["telegram_id"])
    op.create_index("ix_user_activity_logs_object_id", "user_activity_logs", ["object_id"])
    op.create_index("ix_user_activity_logs_created_at", "user_activity_logs", ["created_at"])
    op.create_index("ix_user_activity_logs_user_created", "user_activity_logs", ["user_id", "created_at"])
    op.create_index("ix_user_activity_logs_category_created", "user_activity_logs", ["category", "created_at"])
    op.create_index("ix_user_activity_logs_event_created", "user_activity_logs", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_table("user_activity_logs")
