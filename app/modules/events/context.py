from dataclasses import dataclass

from sqlalchemy import select

from app.db.models import BusinessConnection, Dialog, Message, User, UserSettings


@dataclass(slots=True)
class OwnerContext:
    user: User
    dialog: Dialog
    preferences: UserSettings


class EventContextService:
    async def ensure_preferences(self, session, user: User) -> UserSettings:
        preferences = user.settings or await session.get(UserSettings, user.id)
        if preferences is None:
            preferences = UserSettings(user_id=user.id, language=user.language_code or "ru")
            session.add(preferences)
            await session.flush()
        return preferences

    async def owner_context(self, session, message: Message) -> OwnerContext | None:
        dialog = await session.get(Dialog, message.dialog_id)
        if dialog is None:
            return None
        user = await session.get(User, dialog.owner_user_id)
        if user is None:
            return None
        return OwnerContext(
            user=user,
            dialog=dialog,
            preferences=await self.ensure_preferences(session, user),
        )

    async def preferences_for_connection(
        self, session, connection_id: str
    ) -> UserSettings | None:
        connection = await session.scalar(
            select(BusinessConnection).where(
                BusinessConnection.telegram_connection_id == connection_id
            )
        )
        if connection is None:
            return None
        user = await session.get(User, connection.owner_user_id)
        if user is None:
            return None
        return await self.ensure_preferences(session, user)
