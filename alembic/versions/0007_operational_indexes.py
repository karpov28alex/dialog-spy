"""Reconcile revision 0006 and add operational indexes.

Revision ID: 0007
Revises: 0006

Two historical migrations were accidentally published with revision ID 0006.
This migration deliberately repeats both idempotent effects so databases that
applied either variant converge before advancing to revision 0007.
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


TRIGRAM_INDEXES = (
    ("ix_dialogs_peer_name_trgm", "dialogs", "peer_name"),
    ("ix_dialogs_peer_username_trgm", "dialogs", "peer_username"),
    ("ix_messages_text_trgm", "messages", "text"),
    ("ix_messages_caption_trgm", "messages", "caption"),
    ("ix_message_versions_text_trgm", "message_versions", "text"),
    ("ix_message_versions_caption_trgm", "message_versions", "caption"),
    ("ix_media_filename_trgm", "media", "filename"),
    ("ix_media_mime_type_trgm", "media", "mime_type"),
    ("ix_media_media_type_trgm", "media", "media_type"),
)

FTS_INDEXES = (
    (
        "ix_dialogs_search_fts",
        "dialogs",
        "to_tsvector('simple', coalesce(peer_name, '') || ' ' || coalesce(peer_username, ''))",
    ),
    (
        "ix_messages_search_fts",
        "messages",
        "to_tsvector('simple', coalesce(text, '') || ' ' || coalesce(caption, ''))",
    ),
    (
        "ix_message_versions_search_fts",
        "message_versions",
        "to_tsvector('simple', coalesce(text, '') || ' ' || coalesce(caption, ''))",
    ),
    (
        "ix_media_search_fts",
        "media",
        "to_tsvector('simple', coalesce(filename, '') || ' ' || coalesce(mime_type, '') || ' ' || coalesce(media_type, ''))",
    ),
)

OPERATIONAL_INDEXES = (
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


def _reconcile_search_indexes() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, column in TRIGRAM_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} "
            f"ON {table} USING gin ({column} gin_trgm_ops)"
        )
    for name, table, expression in FTS_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} "
            f"ON {table} USING gin (({expression}))"
        )


def _reconcile_user_settings() -> None:
    op.execute(
        """
        INSERT INTO user_settings (
            user_id,
            notifications_enabled,
            save_protected_media,
            notify_edits,
            notify_deletions,
            notify_protected_media,
            notify_connection,
            hide_preview,
            notify_emoji,
            theme,
            language,
            timezone,
            created_at,
            updated_at
        )
        SELECT
            u.id,
            TRUE,
            TRUE,
            TRUE,
            TRUE,
            TRUE,
            TRUE,
            FALSE,
            TRUE,
            'dark',
            COALESCE(NULLIF(u.language_code, ''), 'ru'),
            'UTC',
            NOW(),
            NOW()
        FROM users AS u
        LEFT JOIN user_settings AS s ON s.user_id = u.id
        WHERE s.user_id IS NULL
        ON CONFLICT (user_id) DO NOTHING
        """
    )


def upgrade() -> None:
    _reconcile_search_indexes()
    _reconcile_user_settings()
    for name, table, columns, predicate in OPERATIONAL_INDEXES:
        suffix = f" {predicate}" if predicate else ""
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns}){suffix}"
        )


def downgrade() -> None:
    for name, _, _, _ in reversed(OPERATIONAL_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
