from __future__ import annotations

from sqlalchemy import select

from src.core.uow import IUnitOfWork
from src.model.models import NotificationSettings
from src.repository.base_repository import BaseRepository


class NotificationSettingsRepository(BaseRepository[NotificationSettings, dict, dict]):
    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)
        self._model = NotificationSettings

    async def get_by_user_id(self, user_id: int) -> NotificationSettings | None:
        result = await self.uow.session.execute(
            select(NotificationSettings).where(NotificationSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> NotificationSettings:
        settings = await self.get_by_user_id(user_id)
        if settings:
            return settings
        return await self.create({"user_id": user_id})

    async def update_by_user_id(self, user_id: int, update_data: dict) -> NotificationSettings:
        settings = await self.get_or_create(user_id)
        for key, value in update_data.items():
            setattr(settings, key, value)
        await self.uow.session.flush()
        return settings
