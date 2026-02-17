from __future__ import annotations

import asyncio

from src.core.celery_app import celery_app
from src.core.logging_config import get_logger
from src.core.uow import SqlAlchemyUoW
from src.repository.notification_repository import NotificationRepository
from src.repository.project_participation_repository import ProjectParticipationRepository
from src.repository.project_repository import ProjectRepository
from src.services.notification_service import NotificationService

logger = get_logger(__name__)


@celery_app.task(name="send_notification_task")
def send_notification_task(notification_id: str):
    # Фоновая задача для отправки уведомления
    async def _run():
        async with SqlAlchemyUoW() as uow:
            service = NotificationService(
                NotificationRepository(uow), ProjectRepository(uow), ProjectParticipationRepository(uow)
            )

            try:
                await service.execute_external_sending(notification_id)
                logger.info(f"Уведомление {notification_id} успешно отправлено через воркер")
            except Exception:
                logger.exception("Ошибка при отправке уведомления %s", notification_id)

    asyncio.run(_run())
