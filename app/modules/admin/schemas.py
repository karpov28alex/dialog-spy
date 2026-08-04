from pydantic import BaseModel


class AdminMetricSummary(BaseModel):
    users_total: int
    users_today: int
    users_month: int
    active_business: int
    active_trial: int
    active_vip: int
    dialogs: int
    messages: int
    edited_messages: int
    deleted_messages: int
    protected_media: int
    failed_updates: int
    revenue_today: float
    revenue_month: float
    revenue_total: float


class TimelinePoint(BaseModel):
    date: str
    count: int


class EventTimelinePoint(BaseModel):
    date: str
    messages: int
    edited: int
    deleted: int


class RecentUser(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    name: str
    registered_at: str
    last_seen_at: str
    trial_ends_at: str
    vip_ends_at: str | None
    subscription_status: str
    blocked: bool


class AdminDashboardResponse(BaseModel):
    metrics: AdminMetricSummary
    registrations: list[TimelinePoint]
    events: list[EventTimelinePoint]
    recent_users: list[RecentUser]
