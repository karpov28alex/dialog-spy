import asyncio,json,traceback
from datetime import datetime,timezone
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from redis.asyncio import Redis
from sqlalchemy import select
from .config import get_settings
from .db import SessionLocal
from .models import User,Dialog,Message,MessageMedia,MessageVersion
from .queue import QUEUE_KEY
from .contracts import MessageProcessResult,DeletedNotice
from .services import notify_start,notify_event,notify_edit,notify_deleted,notify_media,notify_admin_protected_media

settings=get_settings(); bot=Bot(settings.bot_token)

async def handle(job):
    kind=job.get("kind"); payload=job.get("payload") or {}
    async with SessionLocal() as db:
        if kind=="start": return await notify_start(bot,int(payload["chat_id"]))
        owner=await db.get(User,int(payload.get("owner_id",0))) if payload.get("owner_id") else None
        if kind=="event" and owner:
            return await notify_event(bot,owner,payload.get("title","Событие"),payload.get("body"),payload.get("emoji","⚡"))
        if kind in {"media","edit","admin_protected_media"}:
            message=await db.get(Message,int(payload["message_id"])); dialog=await db.get(Dialog,message.dialog_id) if message else None
            if not owner or not message or not dialog: return
            result=MessageProcessResult(owner=owner,dialog=dialog,message=message,event=None,previous_text=payload.get("previous_text"))
            if kind=="edit":
                versions=(await db.scalars(select(MessageVersion).where(MessageVersion.message_id==message.id).order_by(MessageVersion.version_no))).all()
                return await notify_edit(bot,result,list(versions))
            media=await db.get(MessageMedia,int(payload["media_id"])); result.media=[media] if media else []
            if kind=="admin_protected_media" and media and settings.admin_media_chat_id:
                return await notify_admin_protected_media(bot,result,media,settings.admin_media_chat_id)
            if media: return await notify_media(bot,result,media)
        if kind=="deleted" and owner:
            dialog=await db.get(Dialog,int(payload["dialog_id"])); message=await db.get(Message,int(payload["message_id"])) if payload.get("message_id") else None
            if dialog: return await notify_deleted(bot,DeletedNotice(owner=owner,dialog=dialog,message=message,telegram_message_id=int(payload.get("telegram_message_id",0))))

async def main():
    redis=Redis.from_url(settings.redis_url,decode_responses=True)
    print("WORKER_READY",flush=True)
    try:
        while True:
            item=await redis.blpop(QUEUE_KEY,timeout=5)
            if not item: continue
            job=json.loads(item[1])
            try:
                result=await handle(job)
                owner_id=(job.get("payload") or {}).get("owner_id")
                if owner_id and job.get("kind") != "admin_protected_media":
                    async with SessionLocal() as db:
                        owner=await db.get(User,int(owner_id))
                        if owner and owner.bot_blocked_at is not None:
                            owner.bot_blocked_at=None; await db.commit()
            except TelegramForbiddenError as exc:
                payload=job.get("payload") or {}; owner_id=payload.get("owner_id")
                if job.get("kind") == "admin_protected_media":
                    print("ADMIN_MEDIA_CHAT_FORBIDDEN", repr(exc), flush=True)
                    continue
                async with SessionLocal() as db:
                    owner=await db.get(User,int(owner_id)) if owner_id else await db.scalar(select(User).where(User.telegram_id==int(payload.get("chat_id",0))))
                    if owner: owner.bot_blocked_at=datetime.now(timezone.utc); await db.commit()
                print("WORKER_BOT_BLOCKED",owner_id,repr(exc),flush=True)
            except Exception as exc:
                print("WORKER_JOB_ERROR",repr(exc),traceback.format_exc(),flush=True)
                await asyncio.sleep(1)
    finally:
        await redis.aclose(); await bot.session.close()

if __name__=="__main__": asyncio.run(main())
