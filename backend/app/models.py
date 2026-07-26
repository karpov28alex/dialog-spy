import enum
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class SubscriptionStatus(str, enum.Enum):
    trial="trial"; active="active"; past_due="past_due"; cancelled="cancelled"; expired="expired"; blocked="blocked"
class EventType(str, enum.Enum):
    created="created"; edited="edited"; deleted="deleted"; media="media"; connection="connection"

class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    telegram_id:Mapped[int]=mapped_column(BigInteger,unique=True,index=True)
    username:Mapped[str|None]=mapped_column(String(64))
    first_name:Mapped[str|None]=mapped_column(String(128))
    last_name:Mapped[str|None]=mapped_column(String(128))
    language_code:Mapped[str|None]=mapped_column(String(16))
    subscription_status:Mapped[SubscriptionStatus]=mapped_column(Enum(SubscriptionStatus),default=SubscriptionStatus.trial)
    trial_started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    trial_ends_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    vip_ends_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    is_blocked:Mapped[bool]=mapped_column(Boolean,default=False)
    retention_days:Mapped[int]=mapped_column(Integer,default=30)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    referral_link_id:Mapped[int|None]=mapped_column(Integer,index=True)
    referral_joined_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    bot_blocked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),index=True)
    connections=relationship("BusinessConnection",back_populates="owner")

class BusinessConnection(Base):
    __tablename__="business_connections"
    id:Mapped[int]=mapped_column(primary_key=True)
    connection_id:Mapped[str]=mapped_column(String(128),unique=True,index=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    business_user_id:Mapped[int]=mapped_column(BigInteger,index=True)
    is_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    rights:Mapped[dict]=mapped_column(JSON,default=dict)
    connected_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    owner=relationship("User",back_populates="connections")

class Dialog(Base):
    __tablename__="dialogs"
    id:Mapped[int]=mapped_column(primary_key=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    connection_id:Mapped[str]=mapped_column(String(128),index=True)
    telegram_chat_id:Mapped[int]=mapped_column(BigInteger,index=True)
    title:Mapped[str|None]=mapped_column(String(255))
    username:Mapped[str|None]=mapped_column(String(64))
    is_muted:Mapped[bool]=mapped_column(Boolean,default=False)
    is_excluded:Mapped[bool]=mapped_column(Boolean,default=False)
    last_event_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    __table_args__=(UniqueConstraint("owner_id","telegram_chat_id", name="uq_dialog_owner_chat"),)

class Message(Base):
    __tablename__="messages"
    id:Mapped[int]=mapped_column(primary_key=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    dialog_id:Mapped[int]=mapped_column(ForeignKey("dialogs.id"),index=True)
    connection_id:Mapped[str]=mapped_column(String(128),index=True)
    telegram_chat_id:Mapped[int]=mapped_column(BigInteger,index=True)
    telegram_message_id:Mapped[int]=mapped_column(BigInteger,index=True)
    from_user_id:Mapped[int|None]=mapped_column(BigInteger)
    from_name:Mapped[str|None]=mapped_column(String(255))
    from_username:Mapped[str|None]=mapped_column(String(64))
    current_text:Mapped[str|None]=mapped_column(Text)
    content_type:Mapped[str]=mapped_column(String(32),default="text")
    media_group_id:Mapped[str|None]=mapped_column(String(128))
    reply_to_message_id:Mapped[int|None]=mapped_column(BigInteger)
    is_deleted:Mapped[bool]=mapped_column(Boolean,default=False)
    sent_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    edited_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    deleted_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    raw:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint("connection_id","telegram_chat_id","telegram_message_id"),)

class MessageVersion(Base):
    __tablename__="message_versions"
    id:Mapped[int]=mapped_column(primary_key=True)
    message_id:Mapped[int]=mapped_column(ForeignKey("messages.id"),index=True)
    version_no:Mapped[int]=mapped_column(Integer)
    text:Mapped[str|None]=mapped_column(Text)
    raw:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint("message_id","version_no"),)

class MessageMedia(Base):
    __tablename__="message_media"
    id:Mapped[int]=mapped_column(primary_key=True)
    message_id:Mapped[int]=mapped_column(ForeignKey("messages.id"),index=True)
    media_type:Mapped[str]=mapped_column(String(32))
    telegram_file_id:Mapped[str|None]=mapped_column(String(512))
    telegram_file_unique_id:Mapped[str|None]=mapped_column(String(256))
    local_path:Mapped[str|None]=mapped_column(String(1024))
    mime_type:Mapped[str|None]=mapped_column(String(128))
    file_size:Mapped[int|None]=mapped_column(BigInteger)
    is_ephemeral_hint:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class Event(Base):
    __tablename__="events"
    id:Mapped[int]=mapped_column(primary_key=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    dialog_id:Mapped[int|None]=mapped_column(ForeignKey("dialogs.id"),index=True)
    message_id:Mapped[int|None]=mapped_column(ForeignKey("messages.id"),index=True)
    event_type:Mapped[EventType]=mapped_column(Enum(EventType),index=True)
    title:Mapped[str]=mapped_column(String(255))
    summary:Mapped[str|None]=mapped_column(Text)
    payload:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)

class NotificationSettings(Base):
    __tablename__="notification_settings"
    id:Mapped[int]=mapped_column(primary_key=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"),unique=True)
    deleted_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    edited_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    media_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    connection_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    hide_preview:Mapped[bool]=mapped_column(Boolean,default=False)
    digest_mode:Mapped[str]=mapped_column(String(32),default="instant")

class Admin(Base):
    __tablename__="admins"
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(255),unique=True)
    password_hash:Mapped[str]=mapped_column(String(255))
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class ProcessedUpdate(Base):
    __tablename__="processed_updates"
    id:Mapped[int]=mapped_column(primary_key=True)
    update_id:Mapped[int]=mapped_column(BigInteger,unique=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())


class BackgroundJob(Base):
    __tablename__="background_jobs"
    id:Mapped[int]=mapped_column(primary_key=True)
    kind:Mapped[str]=mapped_column(String(64),index=True)
    payload:Mapped[dict]=mapped_column(JSON,default=dict)
    status:Mapped[str]=mapped_column(String(32),default="pending",index=True)
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    max_attempts:Mapped[int]=mapped_column(Integer,default=5)
    available_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
    locked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    last_error:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class FailedUpdate(Base):
    __tablename__="failed_updates"
    id:Mapped[int]=mapped_column(primary_key=True)
    update_id:Mapped[int|None]=mapped_column(BigInteger,index=True)
    update_type:Mapped[str|None]=mapped_column(String(64),index=True)
    raw:Mapped[dict]=mapped_column(JSON,default=dict)
    error:Mapped[str]=mapped_column(Text)
    retry_count:Mapped[int]=mapped_column(Integer,default=0)
    resolved:Mapped[bool]=mapped_column(Boolean,default=False,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)

class Payment(Base):
    __tablename__="payments"
    id:Mapped[int]=mapped_column(primary_key=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    provider:Mapped[str]=mapped_column(String(32),default="impaya")
    external_id:Mapped[str|None]=mapped_column(String(255),unique=True)
    amount_minor:Mapped[int]=mapped_column(Integer,default=0)
    currency:Mapped[str]=mapped_column(String(8),default="RUB")
    status:Mapped[str]=mapped_column(String(32),default="pending",index=True)
    is_recurring:Mapped[bool]=mapped_column(Boolean,default=False)
    payload:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

class PromoCode(Base):
    __tablename__="promo_codes"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(64),unique=True,index=True)
    days:Mapped[int]=mapped_column(Integer,default=7)
    max_uses:Mapped[int|None]=mapped_column(Integer)
    uses:Mapped[int]=mapped_column(Integer,default=0)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class AdminAudit(Base):
    __tablename__="admin_audit"
    id:Mapped[int]=mapped_column(primary_key=True)
    admin_id:Mapped[int|None]=mapped_column(ForeignKey("admins.id"),index=True)
    action:Mapped[str]=mapped_column(String(128),index=True)
    target_type:Mapped[str|None]=mapped_column(String(64))
    target_id:Mapped[str|None]=mapped_column(String(128))
    payload:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)


class ReferralLink(Base):
    __tablename__="referral_links"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(64),unique=True,index=True)
    source:Mapped[str]=mapped_column(String(255),index=True)
    campaign:Mapped[str|None]=mapped_column(String(255))
    placement:Mapped[str|None]=mapped_column(String(255))
    spend_minor:Mapped[int]=mapped_column(BigInteger,default=0)
    currency:Mapped[str]=mapped_column(String(8),default="RUB")
    notes:Mapped[str|None]=mapped_column(Text)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
