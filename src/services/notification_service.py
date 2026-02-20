from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.core.exceptions import NotFoundError, ValidationError
from src.model.models import Notification
from src.notifications.channels import NotificationChannel
from src.notifications.templates import list_notification_required_fields, list_notification_templates
from src.repository.notification_repository import NotificationRepository
from src.repository.notification_settings_repository import NotificationSettingsRepository
from src.repository.project_participation_repository import ProjectParticipationRepository
from src.repository.project_repository import ProjectRepository
from src.services.notification_tasks import CHANNEL_TASKS


class NotificationService:
    """Сервис управляет системой уведомлений платформы и их доставкой."""

    def __init__(
        self,
        notification_repository: NotificationRepository,
        project_repository: ProjectRepository,
        project_participation_repository: ProjectParticipationRepository,
        notification_settings_repository: NotificationSettingsRepository,
    ) -> None:
        """Инициализирует сервис репозиториями уведомлений и проектов."""
        self._notification_repository = notification_repository
        self._project_repository = project_repository
        self._project_participation_repository = project_participation_repository
        self._notification_settings_repository = notification_settings_repository

    @staticmethod
    def _templates() -> dict[str, dict[str, Any]]:
        """Возвращает словарь всех доступных шаблонов уведомлений."""
        return list_notification_templates()

    @classmethod
    def _render_template(cls, template_key: str, payload: dict[str, Any]) -> tuple[str, str]:
        """Рендерит заголовок и тело уведомления по шаблону и payload."""
        templates = cls._templates()
        template = templates.get(template_key)
        if not template:
            raise ValidationError(f"Unknown template key: {template_key}")

        required_fields = template.get("required", [])
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValidationError(f"Missing payload fields for template '{template_key}': {', '.join(missing)}")

        title = template["title"].format(**payload)
        body = template["body"].format(**payload)
        return title, body

    async def list_user_notifications(self, user_id: int, page: int, limit: int) -> tuple[list[Notification], int]:
        """Возвращает список уведомлений пользователя с пагинацией."""
        skip = (page - 1) * limit
        notifications = await self._notification_repository.get_by_user_id(user_id, skip=skip, limit=limit)
        total = await self._notification_repository.count_by_user_id(user_id)
        return notifications, total

    async def send_to_user(
        self,
        recipient_id: int,
        sender_id: int | None,
        template_key: str,
        payload: dict[str, Any],
        project_id: int | None = None,
        channels: list[str] | None = None,
    ) -> tuple[Notification, int]:
        """Создает уведомление для пользователя и отправляет его по выбранным каналам.
        Returns:
            Кортеж (notification, status_code) где status_code 200 если все каналы отправлены,
            202 если некоторые каналы были отключены в настройках пользователя.
        """
        normalized_channels = self._normalize_channels(channels)

        # Получаем настройки и фильтруем каналы
        settings = await self._notification_settings_repository.get_or_create(recipient_id)
        allowed_channels = self._filter_allowed_channels(normalized_channels, settings)
        title, body = self._render_template(template_key, payload)
        data = {
            "id": str(uuid4()),
            "recipient_id": recipient_id,
            "sender_id": sender_id,
            "project_id": project_id,
            "type": template_key,
            "status": "pending",
            "title": title,
            "body": body,
            "channels": allowed_channels,
        }
        notification = await self._notification_repository.create(data)
        await self._dispatch_notification(notification.id, allowed_channels, recipient_id)

        # Возвращаем 202 если были отключены некоторые каналы
        status_code = 200 if len(allowed_channels) == len(normalized_channels) else 202
        return notification, status_code

    async def send_to_project_participants(
        self,
        project_id: int,
        sender_id: int | None,
        template_key: str,
        payload: dict[str, Any],
        include_author: bool = True,
        channels: list[str] | None = None,
    ) -> tuple[list[Notification], int]:
        """Создает уведомления участникам проекта и отправляет их по выбранным каналам.
        Returns:
            Кортеж (notifications, status_code) где status_code 200 если все каналы отправлены,
            202 если некоторые каналы были отключены в настройках пользователей.
        """
        normalized_channels = self._normalize_channels(channels)
        project = await self._project_repository.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        participant_ids = await self._project_participation_repository.get_participant_ids_by_project_id(project_id)
        recipients = set(participant_ids)
        if include_author:
            recipients.add(project.author_id)

        if not recipients:
            return [], 200

        title, body = self._render_template(template_key, payload)

        notifications_data: list[dict[str, Any]] = []
        channels_disabled = False
        for recipient_id in recipients:
            settings = await self._notification_settings_repository.get_or_create(recipient_id)
            allowed_channels = self._filter_allowed_channels(normalized_channels, settings)
            if len(allowed_channels) < len(normalized_channels):
                channels_disabled = True
            notifications_data.append(
                {
                    "id": str(uuid4()),
                    "recipient_id": recipient_id,
                    "sender_id": sender_id,
                    "project_id": project_id,
                    "type": template_key,
                    "status": "pending",
                    "title": title,
                    "body": body,
                    "channels": allowed_channels,
                }
            )

        notifications = await self._notification_repository.create_many(notifications_data)
        for notification in notifications:
            await self._dispatch_notification(notification.id, notification.channels, notification.recipient_id)

        status_code = 202 if channels_disabled else 200
        return notifications, status_code

    async def mark_read(self, user_id: int, notification_id: str) -> Notification:
        """Помечает уведомление как прочитанное для пользователя."""
        notification = await self._notification_repository.mark_read(user_id, notification_id)
        if not notification:
            raise NotFoundError("Notification not found")
        return notification

    async def mark_all_read(self, user_id: int) -> int:
        """Помечает все уведомления пользователя как прочитанные."""
        return await self._notification_repository.mark_all_read(user_id)

    @classmethod
    def list_templates(cls) -> dict[str, dict[str, Any]]:
        """Возвращает словарь обязательных полей для каждого типа шаблона."""
        return list_notification_required_fields()

    @staticmethod
    def _normalize_channels(channels: list[str] | None) -> list[str]:
        """Нормализует и валидирует каналы доставки."""
        if not channels:
            return [NotificationChannel.IN_APP.value]
        normalized = [
            (channel.value if isinstance(channel, NotificationChannel) else str(channel)) for channel in channels
        ]
        allowed = {channel.value for channel in NotificationChannel}
        unknown = sorted(set(normalized) - allowed)
        if unknown:
            raise ValidationError(f"Unknown notification channels: {', '.join(unknown)}")
        return normalized

    @staticmethod
    def _filter_allowed_channels(channels: list[str], settings: Any) -> list[str]:
        """Фильтрует каналы по настройкам пользователя."""
        channel_settings = {
            "in-app": settings.in_app_enabled,
            "telegram": settings.telegram_enabled,
            "email": settings.email_enabled,
        }
        return [channel for channel in channels if channel_settings.get(channel, False)]

    async def _dispatch_notification(self, notification_id: str, channels: list[str], recipient_id: int) -> None:
        """Отправляет уведомление в задачи по каналам, если они разрешены в настройках пользователя."""

        settings = await self._notification_settings_repository.get_or_create(recipient_id)

        channel_settings = {
            "in-app": settings.in_app_enabled,
            "telegram": settings.telegram_enabled,
            "email": settings.email_enabled,
        }

        for channel in set(channels):
            if not channel_settings.get(channel, False):
                continue

            task = CHANNEL_TASKS.get(channel)
            if task:
                task.delay(notification_id)

    async def execute_external_sending(self, notification_id: str) -> None:
        """Выполняет логику отправки уведомления через внешние каналы."""
        notification = await self._notification_repository.get_by_id(notification_id)
        if not notification:
            return

        await self._notification_repository.update_status(notification_id, "sent")
