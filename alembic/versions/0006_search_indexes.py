"""Add PostgreSQL indexes for ranked archive search.

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
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
        "to_tsvector('simple', concat_ws(' ', coalesce(peer_name, ''), coalesce(peer_username, '')))",
    ),
    (
        "ix_messages_search_fts",
        "messages",
        "to_tsvector('simple', concat_ws(' ', coalesce(text, ''), coalesce(caption, '')))",
    ),
    (
        "ix_message_versions_search_fts",
        "message_versions",
        "to_tsvector('simple', concat_ws(' ', coalesce(text, ''), coalesce(caption, '')))",
    ),
    (
        "ix_media_search_fts",
        "media",
        "to_tsvector('simple', concat_ws(' ', coalesce(filename, ''), coalesce(mime_type, ''), coalesce(media_type, '')))",
    ),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, column in TRIGRAM_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gin ({column} gin_trgm_ops)"
        )
    for name, table, expression in FTS_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING gin (({expression}))"
        )


def downgrade() -> None:
    for name, _, _ in reversed(FTS_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
    for name, _, _ in reversed(TRIGRAM_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
