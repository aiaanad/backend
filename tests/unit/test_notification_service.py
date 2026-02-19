from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest

from src.core.exceptions import NotFoundError, ValidationError
from src.model.models import Notification, Project
from src.notifications.templates import list_notification_required_fields
from src.repository.notification_repository import NotificationRepository
from src.repository.project_participation_repository import ProjectParticipationRepository
from src.repository.project_repository import ProjectRepository
from src.services.notification_service import NotificationService

EXPECTED_SENDER_ID = 2
EXPECTED_PARTICIPANTS_COUNT = 3


class TestNotificationService:
    """Тесты для NotificationService"""

    @pytest.mark.asyncio
    async def test_should_send_notification_to_user(self):
        """Тест должен отправить уведомление пользователю"""
        # given
        mock_notification_repository = Mock(spec=NotificationRepository)
        mock_project_repository = Mock(spec=ProjectRepository)
        mock_participation_repository = Mock(spec=ProjectParticipationRepository)

        mock_notification = Notification(
            id="test-id",
            recipient_id=1,
            sender_id=2,
            project_id=None,
            type="system_alert",
            status="pending",
            title="Системное уведомление",
            body="Test message",
            channels=[],
            created_at=datetime.now(),
        )
        mock_notification_repository.create.return_value = mock_notification

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
        )

        # when
        with patch("src.services.notification_service.send_notification_task") as mock_task:
            result = await service.send_to_user(
                recipient_id=1,
                sender_id=2,
                template_key="system_alert",
                payload={"message": "Test message"},
            )

        # then
        assert result == mock_notification
        mock_task.delay.assert_called_once_with("test-id")
        mock_notification_repository.create.assert_called_once()

        created_data = mock_notification_repository.create.call_args[0][0]
        assert created_data["recipient_id"] == 1
        assert created_data["sender_id"] == EXPECTED_SENDER_ID
        assert created_data["type"] == "system_alert"
        assert created_data["status"] == "pending"
        assert created_data["title"] == "Системное уведомление"
        assert created_data["body"] == "Test message"
        assert isinstance(created_data["id"], str)

    @pytest.mark.asyncio
    async def test_should_send_notifications_to_project_participants(self):
        """Тест должен отправить уведомления участникам проекта"""
        # given
        mock_notification_repository = Mock(spec=NotificationRepository)
        mock_project_repository = Mock(spec=ProjectRepository)
        mock_participation_repository = Mock(spec=ProjectParticipationRepository)

        mock_project_repository.get_by_id.return_value = Project(id=1, name="Test Project", author_id=10)
        mock_participation_repository.get_participant_ids_by_project_id.return_value = [10, 11, 12]
        mock_notification_repository.create_many.return_value = [
            Notification(
                id="n-1",
                recipient_id=10,
                sender_id=2,
                project_id=1,
                type="project_announcement",
                status="pending",
                title="Объявление проекта",
                body="Hello",
                channels=[],
                created_at=datetime.now(),
            ),
            Notification(
                id="n-2",
                recipient_id=11,
                sender_id=2,
                project_id=1,
                type="project_announcement",
                status="pending",
                title="Объявление проекта",
                body="Hello",
                channels=[],
                created_at=datetime.now(),
            ),
            Notification(
                id="n-3",
                recipient_id=12,
                sender_id=2,
                project_id=1,
                type="project_announcement",
                status="pending",
                title="Объявление проекта",
                body="Hello",
                channels=[],
                created_at=datetime.now(),
            ),
        ]

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
        )

        # when
        with patch("src.services.notification_service.send_notification_task") as mock_task:
            result = await service.send_to_project_participants(
                project_id=1,
                sender_id=2,
                template_key="project_announcement",
                payload={"project_name": "Test Project", "message": "Hello"},
            )

        # then
        assert result == mock_notification_repository.create_many.return_value
        assert mock_task.delay.call_count == EXPECTED_PARTICIPANTS_COUNT
        mock_project_repository.get_by_id.assert_called_once_with(1)
        mock_participation_repository.get_participant_ids_by_project_id.assert_called_once_with(1)
        mock_notification_repository.create_many.assert_called_once()

        data_list = mock_notification_repository.create_many.call_args[0][0]
        assert len(data_list) == EXPECTED_PARTICIPANTS_COUNT
        assert {item["recipient_id"] for item in data_list} == {10, 11, 12}

    @pytest.mark.asyncio
    async def test_should_raise_not_found_for_missing_project(self):
        """Тест должен выбросить ошибку при отсутствии проекта"""
        # given
        mock_notification_repository = Mock(spec=NotificationRepository)
        mock_project_repository = Mock(spec=ProjectRepository)
        mock_participation_repository = Mock(spec=ProjectParticipationRepository)

        mock_project_repository.get_by_id.return_value = None

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
        )

        # when & then
        with pytest.raises(NotFoundError, match="Project not found"):
            await service.send_to_project_participants(
                project_id=999,
                sender_id=1,
                template_key="project_announcement",
                payload={"project_name": "Test Project", "message": "Hello"},
            )

    def test_should_raise_validation_error_for_missing_payload(self):
        """Тест должен выбросить ошибку при отсутствии обязательных полей"""
        # when & then
        with pytest.raises(ValidationError, match="Missing payload fields"):
            NotificationService._render_template("project_announcement", {"project_name": "Test Project"})

    def test_should_list_required_template_fields(self):
        """Тест должен вернуть обязательные поля шаблонов"""
        # when
        result = NotificationService.list_templates()

        # then
        assert result == list_notification_required_fields()

    @pytest.mark.asyncio
    async def test_should_execute_external_sending(self):
        """Тест должен обновить статус при отправке уведомления"""
        # given
        mock_notification_repository = Mock(spec=NotificationRepository)
        mock_project_repository = Mock(spec=ProjectRepository)
        mock_participation_repository = Mock(spec=ProjectParticipationRepository)

        mock_notification_repository.get_by_id.return_value = Notification(
            id="test-id",
            recipient_id=1,
            sender_id=2,
            project_id=None,
            type="system_alert",
            status="pending",
            title="Системное уведомление",
            body="Test message",
            channels=[],
            created_at=datetime.now(),
        )

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
        )

        # when
        await service.execute_external_sending("test-id")

        # then
        mock_notification_repository.update_status.assert_called_once_with("test-id", "sent")

    @pytest.mark.asyncio
    async def test_should_trigger_telegram_task(self):
        """Проверка, что таска Telegram вызывается при отправке уведомления"""
        # given
        mock_repo = Mock()
        mock_repo.create = AsyncMock(return_value=Mock(id="test-notif-id"))
        
        service = NotificationService(mock_repo, Mock(), Mock())

        # when
        # Мокаем таски, чтобы не запускать реальный Celery
        with patch("src.services.notification_service.send_telegram_notification") as mock_tg_task:
            with patch("src.services.notification_service.send_notification_task"):
                await service.send_to_user(1, 2, "system_alert", {"message": "test"})

        # then
        mock_tg_task.delay.assert_called_once_with("test-notif-id")