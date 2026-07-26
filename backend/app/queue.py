import json
from datetime import datetime, timezone
from redis.asyncio import Redis
from .config import get_settings

settings=get_settings()
QUEUE_KEY="dialogspy:jobs"

def utcnow(): return datetime.now(timezone.utc)

async def enqueue(kind:str,payload:dict):
    redis=Redis.from_url(settings.redis_url,decode_responses=True)
    try:
        await redis.rpush(QUEUE_KEY,json.dumps({"kind":kind,"payload":payload},ensure_ascii=False))
    finally:
        await redis.aclose()
