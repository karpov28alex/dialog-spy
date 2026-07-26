import asyncio

from sqlalchemy import select, text

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import Admin
from .security import hash_password, verify_password


async def merge_duplicate_dialogs(connection) -> None:
    """Merge legacy rows split by Business connection into one Telegram chat."""
    await connection.execute(text("LOCK TABLE dialogs IN SHARE ROW EXCLUSIVE MODE"))

    await connection.execute(text("""
        WITH ranked AS (
            SELECT id, FIRST_VALUE(id) OVER (
                PARTITION BY owner_id, telegram_chat_id ORDER BY id
            ) AS canonical_id
            FROM dialogs
        )
        UPDATE messages AS m
        SET dialog_id = ranked.canonical_id
        FROM ranked
        WHERE m.dialog_id = ranked.id
          AND ranked.id <> ranked.canonical_id
    """))

    await connection.execute(text("""
        WITH ranked AS (
            SELECT id, FIRST_VALUE(id) OVER (
                PARTITION BY owner_id, telegram_chat_id ORDER BY id
            ) AS canonical_id
            FROM dialogs
        )
        UPDATE events AS e
        SET dialog_id = ranked.canonical_id
        FROM ranked
        WHERE e.dialog_id = ranked.id
          AND ranked.id <> ranked.canonical_id
    """))

    await connection.execute(text("""
        WITH grouped AS (
            SELECT
                owner_id, telegram_chat_id, MIN(id) AS canonical_id,
                BOOL_OR(is_muted) AS is_muted,
                BOOL_AND(is_excluded) AS is_excluded,
                MAX(last_event_at) AS last_event_at
            FROM dialogs
            GROUP BY owner_id, telegram_chat_id
        )
        UPDATE dialogs AS d
        SET is_muted = grouped.is_muted,
            is_excluded = grouped.is_excluded,
            last_event_at = grouped.last_event_at
        FROM grouped
        WHERE d.id = grouped.canonical_id
    """))

    await connection.execute(text("""
        DELETE FROM dialogs AS d
        USING dialogs AS keep
        WHERE d.owner_id = keep.owner_id
          AND d.telegram_chat_id = keep.telegram_chat_id
          AND d.id > keep.id
    """))

    constraints = (await connection.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'dialogs'::regclass
          AND contype = 'u'
          AND pg_get_constraintdef(oid) ILIKE '%owner_id%'
          AND pg_get_constraintdef(oid) ILIKE '%connection_id%'
          AND pg_get_constraintdef(oid) ILIKE '%telegram_chat_id%'
    """))).scalars().all()
    for name in constraints:
        safe_name = name.replace('\"', '\"\"')
        await connection.execute(text(f'ALTER TABLE dialogs DROP CONSTRAINT IF EXISTS "{safe_name}"'))

    exists = await connection.scalar(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'dialogs'::regclass
              AND conname = 'uq_dialog_owner_chat'
        )
    """))
    if not exists:
        await connection.execute(text("""
            ALTER TABLE dialogs
            ADD CONSTRAINT uq_dialog_owner_chat
            UNIQUE (owner_id, telegram_chat_id)
        """))


async def bootstrap() -> None:
    """Create missing schema objects and synchronize the configured administrator."""
    settings = get_settings()
    async with engine.begin() as connection:
        # Prevent two API starts from running bootstrap concurrently.
        await connection.execute(text("SELECT pg_advisory_xact_lock(62001)"))
        await connection.run_sync(Base.metadata.create_all)
        # Add columns introduced after the initial release. SQLAlchemy create_all
        # intentionally does not alter existing tables.
        await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_link_id INTEGER"))
        await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_joined_at TIMESTAMPTZ"))
        await connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS bot_blocked_at TIMESTAMPTZ"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_referral_link_id ON users (referral_link_id)"))
        await connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_bot_blocked_at ON users (bot_blocked_at)"))
        await merge_duplicate_dialogs(connection)

    async with SessionLocal() as db:
        admin = await db.scalar(select(Admin).where(Admin.email == settings.admin_email))
        if admin is None:
            admin = Admin(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                is_active=True,
            )
            db.add(admin)
            action = "created"
        else:
            if not verify_password(settings.admin_password, admin.password_hash):
                admin.password_hash = hash_password(settings.admin_password)
            admin.is_active = True
            action = "synchronized"
        await db.commit()
        print(f"Admin {action}: {settings.admin_email}", flush=True)


async def main() -> None:
    await bootstrap()


if __name__ == "__main__":
    asyncio.run(main())
