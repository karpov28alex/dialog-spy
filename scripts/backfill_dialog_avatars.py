from __future__ import annotations

import argparse
import asyncio
from collections import Counter

from sqlalchemy import select, text

from app.bot.setup import bot
from app.core.config import get_settings
from app.db.models import Dialog
from app.db.session import SessionLocal
from app.services.dialog_avatars import refresh_avatar


async def run(limit: int, delay: float, force: bool) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        statement = (
            select(Dialog)
            .where(Dialog.peer_telegram_id.is_not(None))
            .order_by(Dialog.last_message_at.desc().nullslast(), Dialog.id.desc())
            .limit(limit)
        )
        dialogs = list((await session.scalars(statement)).all())

    counts: Counter[str] = Counter()
    for index, dialog in enumerate(dialogs, 1):
        async with SessionLocal() as session, session.begin():
            if not force:
                existing = await session.scalar(
                    text(
                        """
                        SELECT status
                        FROM dialog_avatars
                        WHERE dialog_id = :dialog_id
                          AND status IN ('available', 'no_photo', 'unavailable')
                        """
                    ),
                    {"dialog_id": dialog.id},
                )
                if existing:
                    counts[f"skipped_{existing}"] += 1
                    print(f"[{index}/{len(dialogs)}] dialog={dialog.id} skipped status={existing}")
                    continue

            status = await refresh_avatar(
                session,
                bot,
                settings,
                dialog_id=dialog.id,
                peer_id=int(dialog.peer_telegram_id),
            )
            counts[status] += 1
            print(
                f"[{index}/{len(dialogs)}] dialog={dialog.id} "
                f"peer={dialog.peer_telegram_id} status={status}"
            )
        if delay > 0:
            await asyncio.sleep(delay)

    print("\nSummary:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    await bot.session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Warm persistent dialog avatar cache")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(max(1, args.limit), max(0.0, args.delay), args.force))


if __name__ == "__main__":
    main()
