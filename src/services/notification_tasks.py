from __future__ import annotations

import asyncio

from src.core.celery_app import celery_app
from src.core.logging_config import get_logger
from src.core.uow import SqlAlchemyUoW
from src.notifications.channels import NotificationChannel
from src.repository.notification_repository import NotificationRepository
from src.repository.notification_settings_repository import NotificationSettingsRepository
from src.repository.user_repository import UserRepository
from src.util.telegram_sender import TelegramSender

logger = get_logger(__name__)


@celery_app.task(name="send_notification_task")
def send_notification_task(notification_id: str):
    # Фоновая задача для отправки уведомления
    async def _run():
        async with SqlAlchemyUoW() as uow:
            try:
                repository = NotificationRepository(uow)
                notification = await repository.get_by_id(notification_id)
                if not notification:
                    logger.warning("Уведомление %s не найдено для отправки", notification_id)
                    return

                await repository.update_status(notification_id, "sent")
                logger.info("Уведомление %s успешно отправлено через воркер", notification_id)
            except Exception:
                logger.exception("Ошибка при отправке уведомления %s", notification_id)

    asyncio.run(_run())


@celery_app.task(name="send_telegram_notification")
def send_telegram_notification(notification_id: str):
    async def _run():
        async with SqlAlchemyUoW() as uow:
            notif_repo = NotificationRepository(uow)
            user_repo = UserRepository(uow)
            settings_repo = NotificationSettingsRepository(uow)

            notification = await notif_repo.get_by_id(notification_id)
            if not notification:
                return

            # Проверяем настройки и наличие chat_id
            user = await user_repo.get_by_id(notification.recipient_id)
            user_settings = await settings_repo.get_or_create(notification.recipient_id)

            if user_settings.telegram_enabled and user and user.telegram_chat_id:
                sender = TelegramSender()
                msg = f"<b>{notification.title}</b>\n\n{notification.body}"

                success = await sender.send_message(user.telegram_chat_id, msg)
                if success:
                    # Помечаем, что ушло через Telegram
                    current_channels = list(notification.channels)
                    if "telegram" not in current_channels:
                        current_channels.append("telegram")
                        notification.channels = current_channels
                    await uow.commit()

    asyncio.run(_run())


CHANNEL_TASKS: dict[str, object] = {
    NotificationChannel.IN_APP.value: send_notification_task,
    NotificationChannel.TELEGRAM.value: send_telegram_notification,
}
