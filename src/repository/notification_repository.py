from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from src.core.uow import IUnitOfWork
from src.model.models import Notification
from src.repository.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification, dict, dict]):
    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)
        self._model = Notification

    async def get_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Notification]:
        result = await self.uow.session.execute(
            select(Notification)
            .where(Notification.recipient_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user_id(self, user_id: int) -> int:
        result = await self.uow.session.execute(
            select(func.count()).select_from(Notification).where(Notification.recipient_id == user_id)
        )
        return result.scalar_one()

    async def create_many(self, notifications_data: list[dict]) -> list[Notification]:
        notifications = [Notification(**data) for data in notifications_data]
        self.uow.session.add_all(notifications)
        await self.uow.session.flush()
        return notifications

    async def mark_read(self, user_id: int, notification_id: str) -> Notification | None:
        notification = await self.get_by_id(notification_id)
        if not notification:
            return None
        if notification.recipient_id != user_id:
            return None
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
        notification.status = "read"
        return notification

    async def mark_all_read(self, user_id: int) -> int:
        result = await self.uow.session.execute(select(Notification).where(Notification.recipient_id == user_id))
        notifications = result.scalars().all()
        updated = 0
        now = datetime.now(UTC)
        for notification in notifications:
            if notification.read_at is None:
                notification.read_at = now
                notification.status = "read"
                updated += 1
        return updated

    async def update_status(self, notification_id: str, status: str) -> Notification | None:
        notification = await self.get_by_id(notification_id)
        if not notification:
            return None
        notification.status = status
        if status == "sent" and notification.sent_at is None:
            notification.sent_at = datetime.now(UTC)
        return notification
