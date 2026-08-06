from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, func, or_, select

from app.api.routes.admin import AdminAuth, Session
from app.db.models import Payment, Subscription, SubscriptionStatus, User

router = APIRouter(prefix="/api/admin/finance", tags=["admin-finance"])


class BonusRequest(BaseModel):
    user_id: int
    days: int = Field(ge=1, le=3650)
    reason: str = Field(min_length=3, max_length=500)


class RefundRequest(BaseModel):
    payment_id: int
    amount_rub: int = Field(ge=1, le=100000)
    reason: str = Field(min_length=3, max_length=500)


def _payload(payment: Payment) -> dict:
    return payment.payload if isinstance(payment.payload, dict) else {}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _user_label(user: User | None) -> str:
    if not user:
        return "Удалённый пользователь"
    return " ".join(filter(None, [user.first_name, user.last_name])) or user.username or str(user.telegram_id)


def _serialize(payment: Payment, user: User | None) -> dict:
    payload = _payload(payment)
    return {
        "id": payment.id,
        "provider": payment.provider,
        "external_id": payment.external_id,
        "user_id": payment.user_id,
        "telegram_id": user.telegram_id if user else None,
        "username": user.username if user else None,
        "name": _user_label(user),
        "amount": float(payment.amount or 0),
        "currency": payment.currency,
        "status": payment.status,
        "kind": str(payload.get("kind") or "payment"),
        "reason": payload.get("reason"),
        "performed_by": payload.get("performed_by") or payload.get("confirmed_by") or payload.get("prepared_by"),
        "source_payment_id": payload.get("source_payment_id"),
        "access_days": payload.get("access_days"),
        "created_at": _iso(payment.created_at),
        "paid_at": _iso(payment.paid_at),
        "refunded_at": _iso(payment.refunded_at),
    }


@router.get("/operations")
async def operations(
    _: AdminAuth,
    session: Session,
    q: str = Query("", max_length=160),
    kind: str = Query("all", max_length=40),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    conditions = [Payment.provider.in_(["impaya", "admin"])]
    term = q.strip()
    if term:
        like = f"%{term}%"
        conditions.append(
            or_(
                Payment.external_id.ilike(like),
                User.username.ilike(like),
                cast(User.telegram_id, String).ilike(like),
            )
        )
    query = select(Payment, User).join(User, User.id == Payment.user_id).where(*conditions)
    rows = list((await session.execute(query.order_by(Payment.id.desc()).offset(offset).limit(limit))).all())
    items = [_serialize(payment, user) for payment, user in rows]
    if kind != "all":
        items = [item for item in items if item["kind"] == kind]
    total = int(
        await session.scalar(
            select(func.count(Payment.id)).join(User, User.id == Payment.user_id).where(*conditions)
        )
        or 0
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/users/{user_id}/summary")
async def user_summary(user_id: int, _: AdminAuth, session: Session) -> dict:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    rows = list(
        (
            await session.scalars(
                select(Payment).where(Payment.user_id == user_id).order_by(Payment.id.desc()).limit(200)
            )
        ).all()
    )
    paid = [row for row in rows if row.provider == "impaya" and row.status == "paid"]
    refund_requests = [row for row in rows if _payload(row).get("kind") == "refund_request"]
    bonuses = [row for row in rows if _payload(row).get("kind") == "bonus"]
    return {
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "name": _user_label(user),
            "vip_ends_at": _iso(user.vip_ends_at),
        },
        "metrics": {
            "paid_total": round(sum(float(row.amount or 0) for row in paid), 2),
            "payments": len(paid),
            "refund_requests": len(refund_requests),
            "bonus_operations": len(bonuses),
        },
        "operations": [_serialize(row, user) for row in rows[:50]],
    }


@router.post("/bonus")
async def grant_bonus(body: BonusRequest, admin: AdminAuth, session: Session) -> dict:
    user = await session.scalar(select(User).where(User.id == body.user_id).with_for_update())
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    now = datetime.now(UTC)
    base = user.vip_ends_at if user.vip_ends_at and user.vip_ends_at > now else now
    user.vip_ends_at = base + timedelta(days=body.days)
    user.subscription_status = SubscriptionStatus.vip
    user.is_access_disabled = False
    operation = Payment(
        user_id=user.id,
        provider="admin",
        external_id=f"admin_bonus_{user.id}_{secrets.token_hex(8)}",
        amount=Decimal("0"),
        currency="RUB",
        status="paid",
        recurring=False,
        paid_at=now,
        payload={
            "kind": "bonus",
            "access_days": body.days,
            "reason": body.reason,
            "performed_by": admin,
            "performed_at": now.isoformat(),
            "new_vip_ends_at": user.vip_ends_at.isoformat(),
        },
    )
    session.add(operation)
    session.add(
        Subscription(
            user_id=user.id,
            status="active",
            source="admin_bonus",
            starts_at=now,
            ends_at=user.vip_ends_at,
        )
    )
    await session.commit()
    await session.refresh(operation)
    return {
        "ok": True,
        "operation_id": operation.id,
        "user_id": user.id,
        "days": body.days,
        "vip_ends_at": user.vip_ends_at.isoformat(),
    }


@router.post("/refund-requests")
async def create_refund_request(body: RefundRequest, admin: AdminAuth, session: Session) -> dict:
    payment = await session.scalar(select(Payment).where(Payment.id == body.payment_id).with_for_update())
    if not payment or payment.provider != "impaya":
        raise HTTPException(status_code=404, detail="Платёж Impaya не найден")
    if payment.status != "paid":
        raise HTTPException(status_code=409, detail="Возврат доступен только для оплаченного платежа")
    if Decimal(body.amount_rub) > payment.amount:
        raise HTTPException(status_code=422, detail="Сумма возврата превышает сумму платежа")
    duplicate = await session.scalar(
        select(Payment.id).where(
            Payment.provider == "admin",
            Payment.user_id == payment.user_id,
            Payment.status.in_(["pending", "processing"]),
        )
    )
    if duplicate:
        pending = await session.get(Payment, duplicate)
        if pending and _payload(pending).get("kind") == "refund_request" and _payload(pending).get("source_payment_id") == payment.id:
            raise HTTPException(status_code=409, detail="По этому платежу уже есть заявка на возврат")
    now = datetime.now(UTC)
    request = Payment(
        user_id=payment.user_id,
        provider="admin",
        external_id=f"admin_refund_{payment.id}_{secrets.token_hex(8)}",
        amount=Decimal(body.amount_rub),
        currency=payment.currency,
        status="pending",
        recurring=False,
        payload={
            "kind": "refund_request",
            "source_payment_id": payment.id,
            "source_external_id": payment.external_id,
            "reason": body.reason,
            "performed_by": admin,
            "performed_at": now.isoformat(),
            "provider_execution_required": True,
        },
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return {
        "ok": True,
        "request_id": request.id,
        "status": "pending",
        "amount_rub": body.amount_rub,
        "message": "Заявка создана. Деньги ещё не возвращены: требуется выполнение через provider API.",
    }
