from __future__ import annotations

from src.model.models import NotificationSettings
from src.repository.notification_settings_repository import NotificationSettingsRepository
from src.schema.notification import NotificationSettingsUpdate


class NotificationSettingsService:
    """Сервис настроек уведомлений"""

    def __init__(self, notification_settings_repository: NotificationSettingsRepository) -> None:
        self._notification_settings_repository = notification_settings_repository

    async def get_settings(self, user_id: int) -> NotificationSettings:
        """Возвращает настройки уведомлений пользователя"""
        return await self._notification_settings_repository.get_or_create(user_id)

    async def update_settings(self, user_id: int, update_data: NotificationSettingsUpdate) -> NotificationSettings:
        """Обновляет настройки уведомлений пользователя"""
        data = update_data.model_dump(exclude_unset=True)
        return await self._notification_settings_repository.update_by_user_id(user_id, data)
