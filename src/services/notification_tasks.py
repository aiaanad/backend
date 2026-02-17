from __future__ import annotations

import asyncio

from src.core.celery_app import celery_app
from src.core.logging_config import get_logger
from src.core.uow import SqlAlchemyUoW
from src.repository.notification_repository import NotificationRepository

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
