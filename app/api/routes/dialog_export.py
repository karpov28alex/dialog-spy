from __future__ import annotations

import html
from datetime import UTC

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.db.models import Dialog, Message

router = APIRouter(tags=["dialog-export"])


def _content(message: Message) -> str:
    value = (message.text or message.caption or "").strip()
    if not value:
        value = f"[{message.raw_metadata.get('media_type', 'медиа')}]"
    return html.escape(value).replace("\n", "<br>")


def _document(dialog: Dialog, messages: list[Message]) -> str:
    title = html.escape(dialog.peer_name or dialog.peer_username or str(dialog.telegram_chat_id))
    bubbles: list[str] = []
    previous_day = None
    for item in messages:
        stamp = item.sent_at.astimezone(UTC)
        day = stamp.strftime("%d.%m.%Y")
        if day != previous_day:
            bubbles.append(f'<div class="day"><span>{day}</span></div>')
            previous_day = day
        classes = ["message", "out" if item.direction == "outgoing" else "in"]
        if item.is_deleted:
            classes.append("deleted")
        state = ""
        if item.is_deleted:
            state = '<div class="state">🗑 Сообщение удалено</div>'
        elif item.edited_at:
            state = '<div class="state">✏️ Изменено</div>'
        bubbles.append(
            f'<article class="{" ".join(classes)}">'
            f'<div class="body">{_content(item)}</div>{state}'
            f'<time>{stamp.strftime("%H:%M")}</time></article>'
        )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phantom · {title}</title><style>
:root{{--bg:#0b0712;--panel:#171020;--incoming:#21172b;--outgoing:#522289;--accent:#a845ff;--muted:#a99eb2}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 50% 0,#271044,#08050d 42%);color:#fff;font:15px/1.42 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
header{{position:sticky;top:0;z-index:2;padding:18px 20px;background:#0b0712e8;backdrop-filter:blur(18px);border-bottom:1px solid #472365}}
.brand{{color:#b75cff;font-weight:900;letter-spacing:.08em;font-size:12px}}h1{{margin:5px 0 2px;font-size:22px}}.meta{{color:var(--muted);font-size:13px}}
.chat{{width:min(760px,100%);margin:auto;padding:24px 14px 70px;display:flex;flex-direction:column;gap:7px}}
.day{{text-align:center;margin:15px 0 9px}}.day span{{padding:6px 11px;border-radius:15px;background:#251631cc;color:#d6cadf;font-size:12px}}
.message{{position:relative;max-width:76%;min-width:92px;padding:10px 54px 8px 13px;border-radius:18px;box-shadow:0 5px 18px #0003;white-space:normal;overflow-wrap:anywhere}}
.message.in{{align-self:flex-start;background:var(--incoming);border-bottom-left-radius:5px}}.message.out{{align-self:flex-end;background:linear-gradient(145deg,#6d2db1,#43206f);border-bottom-right-radius:5px}}
.message time{{position:absolute;right:10px;bottom:7px;color:#d9cce1b8;font-size:11px}}.message.deleted{{opacity:.72;border:1px dashed #f0708d}}.state{{margin-top:5px;color:#ff9bb1;font-size:11px}}
footer{{position:fixed;bottom:0;left:0;right:0;text-align:center;padding:10px;background:#09050ee8;color:#84778c;font-size:11px;backdrop-filter:blur(12px)}}
@media print{{body{{background:white;color:#111}}header{{position:static;background:#fff;color:#111}}.message.in{{background:#eee}}.message.out{{background:#dcc4f1;color:#111}}footer{{display:none}}}}
</style></head><body><header><div class="brand">PHANTOM ARCHIVE</div><h1>{title}</h1><div class="meta">{len(messages)} сообщений · экспорт Telegram-переписки</div></header><main class="chat">{"".join(bubbles) or '<div class="day"><span>Диалог пуст</span></div>'}</main><footer>Приватный экспорт Phantom · файл можно открыть в любом браузере</footer></body></html>"""


@router.get("/export/dialogs/{dialog_id}.html")
async def export_dialog_html(
    dialog_id: int,
    current_user: CurrentUser,
    session: SessionDep,
) -> HTMLResponse:
    dialog = await session.scalar(
        select(Dialog).where(Dialog.id == dialog_id, Dialog.owner_user_id == current_user.id)
    )
    if dialog is None:
        raise HTTPException(status_code=404, detail="Dialog not found")
    messages = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.dialog_id == dialog.id)
                .order_by(Message.sent_at, Message.id)
                .limit(20_000)
            )
        ).all()
    )
    safe_name = "".join(ch for ch in (dialog.peer_name or "dialog") if ch.isalnum() or ch in "-_ ").strip() or "dialog"
    return HTMLResponse(
        _document(dialog, messages),
        headers={
            "Content-Disposition": f'attachment; filename="phantom-{safe_name[:48]}.html"',
            "Cache-Control": "private, no-store",
        },
    )
