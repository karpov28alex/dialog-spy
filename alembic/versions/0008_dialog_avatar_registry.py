"""Add persistent dialog avatar registry.

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dialog_avatars",
        sa.Column("dialog_id", sa.Integer(), nullable=False),
        sa.Column("peer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="retry"),
        sa.Column("telegram_file_id", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dialog_id"], ["dialogs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("dialog_id"),
    )
    op.create_index(
        "ix_dialog_avatars_backfill",
        "dialog_avatars",
        ["status", "next_retry_at", "dialog_id"],
    )
    op.execute(
        """
        INSERT INTO dialog_avatars (dialog_id, peer_telegram_id, status)
        SELECT id, peer_telegram_id, 'retry'
        FROM dialogs
        WHERE peer_telegram_id IS NOT NULL
        ON CONFLICT (dialog_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_dialog_avatars_backfill", table_name="dialog_avatars")
    op.drop_table("dialog_avatars")
