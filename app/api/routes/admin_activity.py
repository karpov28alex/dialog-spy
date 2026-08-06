from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_, select

from app.api.routes.admin import AdminAuth, Session, serialize_user
from app.db.activity_models import UserActivityLog
from app.db.models import User

router = APIRouter(tags=["admin-activity"])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _serialize(row: UserActivityLog) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "telegram_id": row.telegram_id,
        "event_type": row.event_type,
        "category": row.category,
        "title": row.title,
        "description": row.description,
        "object_type": row.object_type,
        "object_id": row.object_id,
        "old_value": row.old_value,
        "new_value": row.new_value,
        "metadata": row.metadata_json or {},
        "created_at": _iso(row.created_at),
    }


@router.get("/api/admin/activity")
async def activity_feed(
    _: AdminAuth,
    session: Session,
    user_id: int | None = None,
    q: str = Query("", max_length=160),
    category: str = Query("", max_length=32),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    stmt = select(UserActivityLog)
    if user_id:
        stmt = stmt.where(UserActivityLog.user_id == user_id)
    if category:
        stmt = stmt.where(UserActivityLog.category == category)
    term = q.strip()
    if term:
        like = f"%{term}%"
        conditions = [
            UserActivityLog.title.ilike(like),
            UserActivityLog.description.ilike(like),
            UserActivityLog.event_type.ilike(like),
            UserActivityLog.object_id.ilike(like),
        ]
        if term.isdigit():
            conditions.append(UserActivityLog.telegram_id == int(term))
        stmt = stmt.where(or_(*conditions))
    rows = list((await session.scalars(stmt.order_by(UserActivityLog.created_at.desc()).offset(offset).limit(limit))).all())
    return {"items": [_serialize(row) for row in rows], "limit": limit, "offset": offset}


@router.get("/api/admin/activity/users/{user_id}")
async def user_activity_summary(user_id: int, _: AdminAuth, session: Session) -> dict:
    user = await session.get(User, user_id)
    if user is None:
        return {"user": None, "summary": {}, "items": []}
    grouped = (
        await session.execute(
            select(UserActivityLog.category, func.count(UserActivityLog.id))
            .where(UserActivityLog.user_id == user_id)
            .group_by(UserActivityLog.category)
        )
    ).all()
    rows = list((await session.scalars(select(UserActivityLog).where(UserActivityLog.user_id == user_id).order_by(UserActivityLog.created_at.desc()).limit(250))).all())
    return {
        "user": serialize_user(user),
        "summary": {category: count for category, count in grouped},
        "items": [_serialize(row) for row in rows],
    }


@router.get("/admin/activity-log", include_in_schema=False)
async def activity_page() -> HTMLResponse:
    return HTMLResponse(_PAGE, headers={"Cache-Control": "no-store"})


_PAGE = r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="color-scheme" content="dark"><title>История действий</title><style>:root{--bg:#08060d;--panel:#130f1c;--line:#352644;--text:#faf8ff;--muted:#aa9eb8;--accent:#a84cff;--green:#42d392;--red:#ff6c82}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui;padding:18px 14px 80px}.wrap{max-width:980px;margin:auto}.eyebrow{color:#ca91ff;font-size:11px;letter-spacing:.14em;font-weight:900}.toolbar{display:grid;grid-template-columns:1fr 180px auto;gap:8px;margin:14px 0}.input,.btn{min-height:46px;border:1px solid var(--line);border-radius:13px;background:#0d0a13;color:#fff;padding:11px 13px;font:inherit}.btn{border:0;background:linear-gradient(135deg,#7924d0,#b850ff);font-weight:800}.card{border:1px solid var(--line);background:linear-gradient(145deg,#15101f,#0e0b15);border-radius:18px;padding:14px;margin:12px 0}.event{display:grid;grid-template-columns:12px 1fr;gap:12px;padding:13px 0;border-bottom:1px solid var(--line)}.event:last-child{border-bottom:0}.dot{width:10px;height:10px;border-radius:50%;margin-top:6px;background:var(--accent);box-shadow:0 0 16px var(--accent)}.meta{color:var(--muted);font-size:13px}.chips{display:flex;gap:7px;overflow:auto;padding:4px 0}.chip{white-space:nowrap;border:1px solid var(--line);border-radius:999px;padding:8px 11px;background:#0d0a13;color:#fff}.chip.active{background:#57208a}.empty{text-align:center;color:var(--muted);padding:30px}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.metric{border:1px solid var(--line);border-radius:13px;padding:11px;background:#0c0911}.metric b{font-size:22px;display:block}@media(max-width:700px){.toolbar{grid-template-columns:1fr}.summary{grid-template-columns:1fr 1fr}}</style></head><body><main class="wrap"><div class="eyebrow">PHANTOM CONTROL CENTER</div><h1>История действий</h1><div class="toolbar"><input class="input" id="query" placeholder="@username, Telegram ID или событие"><select class="input" id="category"><option value="">Все категории</option><option value="connection">Подключения</option><option value="permissions">Права</option><option value="dialogs">Диалоги</option><option value="subscription">Подписка</option><option value="payments">Финансы</option><option value="miniapp">Mini App</option></select><button class="btn" id="search">Найти</button></div><div id="user"></div><div id="summary"></div><section class="card" id="events"><div class="empty">Введите пользователя или откройте страницу из User360</div></section></main><script>const token=()=>sessionStorage.getItem('adminToken')||localStorage.getItem('adminToken');const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const dt=v=>v?new Date(v).toLocaleString('ru-RU'):'—';async function api(url){const r=await fetch(url,{headers:{Authorization:'Bearer '+token()},cache:'no-store'});const d=await r.json().catch(()=>({}));if(r.status===401){location.href='/admin';throw Error('Требуется вход')}if(!r.ok)throw Error(d.detail||'Ошибка API');return d}const E={q:document.getElementById('query'),cat:document.getElementById('category'),events:document.getElementById('events'),user:document.getElementById('user'),summary:document.getElementById('summary')};function renderItems(items){E.events.innerHTML=items.length?items.map(x=>`<article class="event"><span class="dot"></span><div><b>${esc(x.title)}</b>${x.description?`<div>${esc(x.description)}</div>`:''}<div class="meta">${dt(x.created_at)} · ${esc(x.category)} · ${esc(x.event_type)}</div>${x.object_id?`<div class="meta">Объект: ${esc(x.object_type||'—')} ${esc(x.object_id)}</div>`:''}</div></article>`).join(''):'<div class="empty">Событий нет</div>'}async function loadUser(id){const d=await api('/api/admin/activity/users/'+id);E.user.innerHTML=d.user?`<section class="card"><h2>${esc(d.user.name||d.user.username||d.user.telegram_id)}</h2><div class="meta">${esc(d.user.username?'@'+d.user.username:'без username')} · Telegram ${esc(d.user.telegram_id)}</div><a style="color:#d5a8ff" href="/admin/user360-mobile.html?user_id=${d.user.id}">Открыть User360</a></section>`:'';const s=d.summary||{};E.summary.innerHTML=`<section class="summary"><div class="metric"><b>${s.connection||0}</b>подключения</div><div class="metric"><b>${s.permissions||0}</b>права</div><div class="metric"><b>${s.dialogs||0}</b>диалоги</div><div class="metric"><b>${d.items.length}</b>события</div></section>`;renderItems(d.items||[])}async function search(){const term=E.q.value.trim();if(!term){renderItems((await api('/api/admin/activity?category='+encodeURIComponent(E.cat.value))).items||[]);return}const users=await api('/api/admin/user360/search?q='+encodeURIComponent(term)+'&limit=10');if(users.items?.length){await loadUser(users.items[0].id);return}renderItems((await api('/api/admin/activity?q='+encodeURIComponent(term)+'&category='+encodeURIComponent(E.cat.value))).items||[])}document.getElementById('search').onclick=search;E.q.onkeydown=e=>{if(e.key==='Enter')search()};E.cat.onchange=search;const p=new URLSearchParams(location.search),id=p.get('user_id');if(id)loadUser(Number(id));</script></body></html>'''
