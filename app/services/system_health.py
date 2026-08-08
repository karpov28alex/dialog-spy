from __future__ import annotations

from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.db.models import BusinessConnection, FailedUpdate, Job, User
from app.db.session import SessionLocal

settings = get_settings()


async def health_snapshot() -> dict[str, object]:
    db_ok = False
    redis_ok = False
    redis_latency_ms: int | None = None
    started = datetime.now(UTC)
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
            queued = int(await session.scalar(select(func.count(Job.id)).where(Job.status == "queued")) or 0)
            dead = int(await session.scalar(select(func.count(Job.id)).where(Job.status == "dead")) or 0)
            failures = int(await session.scalar(select(func.count(FailedUpdate.id)).where(FailedUpdate.resolved.is_(False))) or 0)
            active_users = int(await session.scalar(select(func.count(User.id)).where(User.last_seen_at >= datetime.now(UTC) - timedelta(hours=24))) or 0)
            connections = int(await session.scalar(select(func.count(BusinessConnection.id)).where(BusinessConnection.is_active.is_(True))) or 0)
    except Exception:
        queued = dead = failures = active_users = connections = -1
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        before = datetime.now(UTC)
        redis_ok = bool(await redis.ping())
        redis_latency_ms = max(0, int((datetime.now(UTC) - before).total_seconds() * 1000))
    except Exception:
        redis_ok = False
    finally:
        await redis.aclose()
    return {"db": db_ok, "redis": redis_ok, "redis_latency_ms": redis_latency_ms, "queued": queued, "dead": dead, "failures": failures, "active_users_24h": active_users, "connections": connections, "checked_ms": int((datetime.now(UTC) - started).total_seconds() * 1000)}


def format_health(data: dict[str, object]) -> str:
    mark = lambda ok: "🟢" if ok else "🔴"
    return (
        "<b>🖥 Phantom Health</b>\n\n"
        f"{mark(bool(data['db']))} PostgreSQL\n"
        f"{mark(bool(data['redis']))} Redis · {data.get('redis_latency_ms') if data.get('redis_latency_ms') is not None else '—'} ms\n"
        f"⚙️ Очередь: <b>{data['queued']}</b> · dead: <b>{data['dead']}</b>\n"
        f"⚠️ Необработанных ошибок: <b>{data['failures']}</b>\n"
        f"👥 Активных за 24ч: <b>{data['active_users_24h']}</b>\n"
        f"🔗 Business подключений: <b>{data['connections']}</b>\n\n"
        f"Версия: <b>{settings.app_version}</b> · <code>{settings.git_sha}</code>"
    )
