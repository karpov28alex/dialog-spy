import asyncio
import json
from datetime import UTC, datetime, timedelta

import structlog
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from redis.asyncio import Redis
from sqlalchemy import select, update

from app.bot.setup import bot
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models import Job, User
from app.db.session import SessionLocal
from app.services.queue import QUEUE_KEY
from app.worker.handlers import WorkerHandlers

settings = get_settings()
logger = structlog.get_logger()
handlers = WorkerHandlers(bot, settings)
QUEUE_MARKER_PREFIX = "dialog_spy:job_enqueued:"
STALE_RUNNING_SECONDS = 300


async def handle_job(job: Job) -> None:
    await handlers.handle(job)


async def process_job(job_id: int, redis: Redis) -> None:
    async with SessionLocal() as session, session.begin():
        job = await session.scalar(
            select(Job).where(Job.id == job_id).with_for_update(skip_locked=True)
        )
        if not job or job.status in {"done", "dead", "running"}:
            await redis.delete(f"{QUEUE_MARKER_PREFIX}{job_id}")
            return
        if job.available_at > datetime.now(UTC):
            await redis.delete(f"{QUEUE_MARKER_PREFIX}{job_id}")
            return
        job.status = "running"
        job.locked_at = datetime.now(UTC)
        job.attempts += 1

    try:
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job:
                await handle_job(job)
        async with SessionLocal() as session, session.begin():
            job = await session.get(Job, job_id, with_for_update=True)
            if job:
                job.status = "done"
                job.last_error = None
                job.locked_at = None
    except TelegramRetryAfter as exc:
        await reschedule(job_id, str(exc), max(int(exc.retry_after), 1))
    except TelegramForbiddenError as exc:
        await mark_forbidden(job_id, str(exc))
    except TelegramBadRequest as exc:
        await reschedule(job_id, str(exc))
    except Exception as exc:
        logger.exception("job_failed", job_id=job_id, kind=getattr(job, "kind", None))
        await reschedule(job_id, str(exc))
    finally:
        await redis.delete(f"{QUEUE_MARKER_PREFIX}{job_id}")


async def mark_forbidden(job_id: int, error: str) -> None:
    async with SessionLocal() as session, session.begin():
        job = await session.get(Job, job_id, with_for_update=True)
        if not job:
            return
        job.status = "dead"
        job.last_error = error
        job.locked_at = None
        telegram_id = job.payload.get("telegram_id")
        if telegram_id:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user:
                user.blocked_bot_at = datetime.now(UTC)


async def reschedule(job_id: int, error: str, delay: int | None = None) -> None:
    async with SessionLocal() as session, session.begin():
        job = await session.get(Job, job_id, with_for_update=True)
        if not job:
            return
        job.locked_at = None
        if job.attempts >= job.max_attempts:
            job.status = "dead"
        else:
            retry_delay = delay or min(2**job.attempts, 300)
            job.status = "queued"
            job.available_at = datetime.now(UTC) + timedelta(seconds=retry_delay)
        job.last_error = error


async def recover_stale_running_jobs() -> int:
    threshold = datetime.now(UTC) - timedelta(seconds=STALE_RUNNING_SECONDS)
    async with SessionLocal() as session, session.begin():
        result = await session.execute(
            update(Job)
            .where(Job.status == "running", Job.locked_at < threshold)
            .values(
                status="queued",
                locked_at=None,
                available_at=datetime.now(UTC),
            )
        )
        return int(result.rowcount or 0)


async def recover_queued_jobs(redis: Redis) -> int:
    async with SessionLocal() as session:
        ids = list(
            (
                await session.scalars(
                    select(Job.id)
                    .where(
                        Job.status == "queued",
                        Job.available_at <= datetime.now(UTC),
                    )
                    .order_by(Job.id)
                    .limit(100)
                )
            ).all()
        )
    queued = 0
    for job_id in ids:
        marker = f"{QUEUE_MARKER_PREFIX}{job_id}"
        if await redis.set(marker, "1", ex=60, nx=True):
            await redis.lpush(QUEUE_KEY, json.dumps({"job_id": job_id}))
            queued += 1
    return queued


async def main() -> None:
    configure_logging()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("worker_started", version=settings.app_version, git_sha=settings.git_sha)
    while True:
        try:
            stale = await recover_stale_running_jobs()
            if stale:
                logger.warning("stale_jobs_recovered", count=stale)
            await recover_queued_jobs(redis)
            item = await redis.brpop(QUEUE_KEY, timeout=2)
            if item:
                payload = json.loads(item[1])
                await process_job(int(payload["job_id"]), redis)
        except Exception:
            logger.exception("worker_loop_error")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
