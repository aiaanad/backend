from __future__ import annotations

import asyncio
import select

from src.core.celery_app import celery_app
from src.core.logging_config import get_logger
from src.core.uow import SqlAlchemyUoW
from src.notifications.channels import NotificationChannel
from src.repository.notification_repository import NotificationRepository
from src.repository.notification_settings_repository import NotificationSettingsRepository
from src.repository.user_repository import UserRepository
from src.util.telegram_sender import TelegramSender
from src.util.email_sender import EmailSender
from src.model.models import NotificationSettings, User


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

"""Таска(=фоновая задача) для отправки уведомления по email"""
@celery_app.task(name="send_email_notification")
def send_email_notification(notification_id: str):
    async def _run():
        async with SqlAlchemyUoW() as uow:
            try:
                notification_repository = NotificationRepository(uow)
                notification = await notification_repository.get_by_id(notification_id)
                
                if not notification:
                    logger.warning("Уведомление %s не найдено для отправки email", notification_id)
                    return

                # Получаем получателя уведомления
                result = await uow.session.execute(
                    select(User).where(User.id == notification.recipient_id)
                )
                recipient = result.scalar_one_or_none()
                
                if not recipient:
                    logger.warning("Получатель %s не найден для уведомления %s", notification.recipient_id, notification_id)
                    return

                # Проверяем наличие email у получателя
                if not recipient.email:
                    logger.info("У получателя %s нет email адреса, пропускаем отправку", notification.recipient_id)
                    return

                # Проверяем настройки уведомлений
                settings_repository = NotificationSettingsRepository(uow)
                settings = await settings_repository.get_by_user_id(notification.recipient_id)
                
                # Если настройки не найдены, используем значения по умолчанию (email_enabled=True)
                if settings and not settings.email_enabled:
                    logger.info("Email уведомления отключены для пользователя %s", notification.recipient_id)
                    return

                # Отправляем email
                email_sender = EmailSender()
                success = email_sender.send_email(
                    to_email=recipient.email,
                    subject=notification.title,
                    body=notification.body,
                )

                if success:
                    logger.info("Email уведомление %s успешно отправлено на %s", notification_id, recipient.email)
                    # Помечаем, что ушло через email
                    current_channels = list(notification.channels)
                    if "email" not in current_channels:
                        current_channels.append("email")
                        notification.channels = current_channels
                        await uow.commit()
                else:
                    logger.error("Не удалось отправить email уведомление %s на %s", notification_id, recipient.email)

            except Exception:
                logger.exception("Ошибка при отправке email уведомления %s", notification_id)

    asyncio.run(_run())

CHANNEL_TASKS: dict[str, object] = {
    NotificationChannel.IN_APP.value: send_notification_task,
    NotificationChannel.TELEGRAM.value: send_telegram_notification,
}
