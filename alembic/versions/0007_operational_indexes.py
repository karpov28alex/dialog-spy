"""Add operational indexes for queue and archive hot paths.

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


INDEXES = (
    (
        "ix_jobs_queue_ready",
        "jobs",
        "status, available_at, id",
        "WHERE status = 'queued'",
    ),
    (
        "ix_jobs_running_locked",
        "jobs",
        "locked_at, id",
        "WHERE status = 'running'",
    ),
    (
        "ix_dialogs_owner_last_message",
        "dialogs",
        "owner_user_id, last_message_at DESC, id DESC",
        "",
    ),
    (
        "ix_messages_dialog_sent",
        "messages",
        "dialog_id, sent_at DESC, id DESC",
        "",
    ),
    (
        "ix_message_versions_message_version",
        "message_versions",
        "message_id, version_number, id",
        "",
    ),
    (
        "ix_media_message_id",
        "media",
        "message_id, id",
        "",
    ),
)


def upgrade() -> None:
    for name, table, columns, predicate in INDEXES:
        suffix = f" {predicate}" if predicate else ""
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns}){suffix}"
        )


def downgrade() -> None:
    for name, _, _, _ in reversed(INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
