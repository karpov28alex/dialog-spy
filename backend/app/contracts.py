from dataclasses import dataclass, field

from .models import Dialog, Event, Message, MessageMedia, User


@dataclass(slots=True)
class MessageProcessResult:
    owner: User
    dialog: Dialog
    message: Message
    event: Event
    media: list[MessageMedia] = field(default_factory=list)
    previous_text: str | None = None


@dataclass(slots=True)
class DeletedNotice:
    owner: User
    dialog: Dialog
    message: Message | None
    telegram_message_id: int
