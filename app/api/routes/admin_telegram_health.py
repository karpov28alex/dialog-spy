from __future__ import annotations

import shutil
from collections import Counter
from datetime import UTC, datetime, timedelta
from time import perf_counter

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import func, select

from app.api.routes.admin import AdminAuth, Session
from app.bot.setup import bot
from app.core.config import Settings, get_settings
from app.db.models import BusinessConnection, Dialog, FailedUpdate, Job, Media, Message, ProcessedUpdate, User

router = APIRouter(prefix="/api/admin/telegram", tags=["admin-telegram"])


def _iso(value):
    return value.isoformat() if value else None


async def _webhook_snapshot() -> dict:
    started = perf_counter()
    try:
        webhook = await bot.get_webhook_info()
        return {
            "ok": True,
            "latency_ms": round((perf_counter() - started) * 1000, 1),
            "url": webhook.url,
            "pending_update_count": webhook.pending_update_count,
            "allowed_updates": list(webhook.allowed_updates or []),
            "last_error_date": _iso(webhook.last_error_date),
            "last_error_message": webhook.last_error_message,
            "max_connections": webhook.max_connections,
        }
    except Exception as exc:
        return {
            "ok": False,
            "latency_ms": round((perf_counter() - started) * 1000, 1),
            "error": f"{type(exc).__name__}: {exc}",
            "allowed_updates": [],
            "pending_update_count": None,
        }


async def _redis_snapshot(settings: Settings) -> dict:
    started = perf_counter()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        ok = bool(await client.ping())
        info = await client.info(section="memory")
        return {
            "ok": ok,
            "latency_ms": round((perf_counter() - started) * 1000, 1),
            "used_memory": int(info.get("used_memory", 0) or 0),
            "used_memory_human": info.get("used_memory_human"),
            "maxmemory": int(info.get("maxmemory", 0) or 0),
        }
    except Exception as exc:
        return {"ok": False, "latency_ms": round((perf_counter() - started) * 1000, 1), "error": str(exc)}
    finally:
        await client.aclose()


@router.get("/coverage")
async def telegram_coverage(
    _: AdminAuth,
    session: Session,
    settings: Settings = Depends(get_settings),
) -> dict:
    now = datetime.now(UTC).replace(tzinfo=None)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    webhook = await _webhook_snapshot()
    redis = await _redis_snapshot(settings)

    processed_rows = list((await session.execute(
        select(ProcessedUpdate.update_type, func.count(ProcessedUpdate.update_id))
        .group_by(ProcessedUpdate.update_type)
    )).all())
    processed = {str(kind): int(count or 0) for kind, count in processed_rows}

    failed_rows = list((await session.execute(
        select(FailedUpdate.update_type, func.count(FailedUpdate.id))
        .where(FailedUpdate.resolved.is_(False))
        .group_by(FailedUpdate.update_type)
    )).all())
    failed = {str(kind): int(count or 0) for kind, count in failed_rows}

    connections = list((await session.scalars(
        select(BusinessConnection).order_by(BusinessConnection.last_activity_at.desc(), BusinessConnection.id.desc())
    )).all())
    rights_counter: Counter[str] = Counter()
    connection_items = []
    for connection in connections:
        rights = dict(connection.rights or {})
        for key, value in rights.items():
            if value is True:
                rights_counter[key] += 1
        connection_items.append({
            "id": connection.id,
            "owner_user_id": connection.owner_user_id,
            "telegram_connection_id": connection.telegram_connection_id,
            "kind": "group" if str(connection.telegram_connection_id).startswith("group:") else "assistant",
            "active": connection.is_active,
            "connected_at": _iso(connection.connected_at),
            "last_activity_at": _iso(connection.last_activity_at),
        })

    media_rows = list((await session.execute(
        select(Media.download_status, func.count(Media.id)).group_by(Media.download_status)
    )).all())
    media_statuses = {str(status or "unknown"): int(count or 0) for status, count in media_rows}

    job_rows = list((await session.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )).all())
    jobs = {str(status or "unknown"): int(count or 0) for status, count in job_rows}
    oldest_queued = await session.scalar(
        select(func.min(Job.available_at)).where(Job.status == "queued")
    )

    recent_failures = list((await session.scalars(
        select(FailedUpdate)
        .where(FailedUpdate.resolved.is_(False))
        .order_by(FailedUpdate.created_at.desc())
        .limit(20)
    )).all())

    disk = shutil.disk_usage(settings.media_root)
    groups_total = sum(1 for item in connections if str(item.telegram_connection_id).startswith("group:"))
    groups_active = sum(1 for item in connections if item.is_active and str(item.telegram_connection_id).startswith("group:"))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "webhook": webhook,
        "required_updates": [
            "message", "edited_message", "callback_query",
            "business_connection", "business_message",
            "edited_business_message", "deleted_business_messages",
        ],
        "processed_updates": processed,
        "unresolved_failed_updates": failed,
        "connections": {
            "total": len(connections),
            "active": sum(1 for item in connections if item.is_active),
            "groups_total": groups_total,
            "groups_active": groups_active,
            "granted_rights": dict(rights_counter),
            "items": connection_items[:100],
        },
        "users": {
            "total": int(await session.scalar(select(func.count(User.id))) or 0),
            "active_24h": int(await session.scalar(select(func.count(User.id)).where(User.last_seen_at >= day_ago)) or 0),
            "active_7d": int(await session.scalar(select(func.count(User.id)).where(User.last_seen_at >= week_ago)) or 0),
        },
        "archive": {
            "dialogs": int(await session.scalar(select(func.count(Dialog.id))) or 0),
            "messages": int(await session.scalar(select(func.count(Message.id))) or 0),
            "messages_24h": int(await session.scalar(select(func.count(Message.id)).where(Message.created_at >= day_ago)) or 0),
            "edited": int(await session.scalar(select(func.count(Message.id)).where(Message.edited_at.is_not(None))) or 0),
            "deleted": int(await session.scalar(select(func.count(Message.id)).where(Message.is_deleted.is_(True))) or 0),
            "media": int(await session.scalar(select(func.count(Media.id))) or 0),
            "media_statuses": media_statuses,
        },
        "jobs": {
            "statuses": jobs,
            "oldest_queued_at": _iso(oldest_queued),
        },
        "redis": redis,
        "storage": {
            "root": str(settings.media_root),
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "used_percent": round((disk.used / disk.total) * 100, 1) if disk.total else 0,
        },
        "recent_failures": [{
            "id": row.id,
            "update_id": row.update_id,
            "type": row.update_type,
            "error": row.error,
            "attempts": row.attempts,
            "created_at": _iso(row.created_at),
            "correlation_id": row.correlation_id,
        } for row in recent_failures],
    }
