from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BusinessConnection,
    Dialog,
    FailedUpdate,
    Media,
    Message,
    Payment,
    SubscriptionStatus,
    User,
)
from app.modules.admin.schemas import (
    AdminDashboardResponse,
    AdminMetricSummary,
    EventTimelinePoint,
    RecentUser,
    TimelinePoint,
)


def database_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def serialize_user(user: User) -> RecentUser:
    return RecentUser(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        name=" ".join(part for part in (user.first_name, user.last_name) if part),
        registered_at=user.registered_at.isoformat(),
        last_seen_at=user.last_seen_at.isoformat(),
        trial_ends_at=user.trial_ends_at.isoformat(),
        vip_ends_at=user.vip_ends_at.isoformat() if user.vip_ends_at else None,
        subscription_status=user.subscription_status.value,
        blocked=user.blocked_bot_at is not None,
    )


class AdminDashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count(self, model, *conditions) -> int:
        statement = select(func.count()).select_from(model).where(*conditions)
        return int(await self._session.scalar(statement) or 0)

    async def dashboard(self) -> AdminDashboardResponse:
        now = database_now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month = today.replace(day=1)
        revenue_today = await self._session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "paid",
                Payment.paid_at >= today,
            )
        )
        revenue_month = await self._session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "paid",
                Payment.paid_at >= month,
            )
        )
        revenue_total = await self._session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == "paid"
            )
        )
        metrics = AdminMetricSummary(
            users_total=await self.count(User),
            users_today=await self.count(User, User.registered_at >= today),
            users_month=await self.count(User, User.registered_at >= month),
            active_business=await self.count(
                BusinessConnection,
                BusinessConnection.is_active.is_(True),
            ),
            active_trial=await self.count(
                User,
                User.trial_ends_at > now,
                User.subscription_status == SubscriptionStatus.trial,
            ),
            active_vip=await self.count(
                User,
                User.vip_ends_at.is_not(None),
                User.vip_ends_at > now,
            ),
            dialogs=await self.count(Dialog),
            messages=await self.count(Message),
            edited_messages=await self.count(Message, Message.edited_at.is_not(None)),
            deleted_messages=await self.count(Message, Message.is_deleted.is_(True)),
            protected_media=await self.count(Media, Media.is_protected.is_(True)),
            failed_updates=await self.count(FailedUpdate, FailedUpdate.resolved.is_(False)),
            revenue_today=float(revenue_today or 0),
            revenue_month=float(revenue_month or 0),
            revenue_total=float(revenue_total or 0),
        )
        start_day = today - timedelta(days=13)
        registration_rows = (
            await self._session.execute(
                select(
                    func.date(User.registered_at).label("day"),
                    func.count(User.id),
                )
                .where(User.registered_at >= start_day)
                .group_by(func.date(User.registered_at))
                .order_by(func.date(User.registered_at))
            )
        ).all()
        event_rows = (
            await self._session.execute(
                select(
                    func.date(Message.created_at).label("day"),
                    func.count(Message.id),
                    func.count(Message.id).filter(Message.edited_at.is_not(None)),
                    func.count(Message.id).filter(Message.is_deleted.is_(True)),
                )
                .where(Message.created_at >= start_day)
                .group_by(func.date(Message.created_at))
                .order_by(func.date(Message.created_at))
            )
        ).all()
        recent_users = list(
            (
                await self._session.scalars(
                    select(User).order_by(desc(User.registered_at)).limit(8)
                )
            ).all()
        )
        return AdminDashboardResponse(
            metrics=metrics,
            registrations=[
                TimelinePoint(date=str(day), count=count)
                for day, count in registration_rows
            ],
            events=[
                EventTimelinePoint(
                    date=str(day),
                    messages=total,
                    edited=edited,
                    deleted=deleted,
                )
                for day, total, edited, deleted in event_rows
            ],
            recent_users=[serialize_user(user) for user in recent_users],
        )
