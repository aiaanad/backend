from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.exceptions import NotFoundError, ValidationError
from src.model.models import Notification, NotificationSettings, Project, User
from src.notifications.templates import list_notification_required_fields
from src.repository.notification_repository import NotificationRepository
from src.repository.notification_settings_repository import NotificationSettingsRepository
from src.repository.project_participation_repository import ProjectParticipationRepository
from src.repository.project_repository import ProjectRepository
from src.services.notification_service import NotificationService
from src.services.notification_tasks import send_email_notification

EXPECTED_SENDER_ID = 2
EXPECTED_PARTICIPANTS_COUNT = 3
EXPECTED_OK_STATUS = 200


class TestNotificationService:
    """Тесты для NotificationService"""

    @pytest.mark.asyncio
    async def test_should_send_notification_to_user(self):
        """Тест должен отправить уведомление пользователю"""
        # given
        mock_notification_repository = Mock(spec=NotificationRepository)
        mock_project_repository = Mock(spec=ProjectRepository)
        mock_participation_repository = Mock(spec=ProjectParticipationRepository)
        mock_settings_repository = Mock(spec=NotificationSettingsRepository)

        mock_notification = Notification(
            id="test-id",
            recipient_id=1,
            sender_id=2,
            project_id=None,
            type="system_alert",
            status="pending",
            title="Системное уведомление",
            body="Test message",
            channels=["in-app"],
            created_at=datetime.now(),
        )
        # create() это async метод, поэтому используем AsyncMock
        mock_notification_repository.create = AsyncMock(return_value=mock_notification)

        # Настройки пользователя разрешают все каналы
        mock_settings = Mock(spec=NotificationSettings)
        mock_settings.in_app_enabled = True
        mock_settings.telegram_enabled = True
        mock_settings.email_enabled = True
        mock_settings_repository.get_or_create = AsyncMock(return_value=mock_settings)

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
            mock_settings_repository,
        )

        # when
        with patch.object(service, "_dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
            result, status_code = await service.send_to_user(
                recipient_id=1,
                sender_id=2,
                template_key="system_alert",
                payload={"message": "Test message"},
            )

        # then
        assert result == mock_notification
        assert status_code == EXPECTED_OK_STATUS
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args[0]
        assert call_args[0] == "test-id"  # notification_id
        assert "in-app" in call_args[1]  # channels list
        assert call_args[2] == 1  # recipient_id
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
        mock_settings_repository = Mock(spec=NotificationSettingsRepository)

        mock_project_repository.get_by_id = AsyncMock(return_value=Project(id=1, name="Test Project", author_id=10))
        mock_participation_repository.get_participant_ids_by_project_id = AsyncMock(return_value=[10, 11, 12])

        notifications = [
            Notification(
                id="n-1",
                recipient_id=10,
                sender_id=2,
                project_id=1,
                type="project_announcement",
                status="pending",
                title="Объявление проекта",
                body="Hello",
                channels=["in-app"],
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
        mock_notification_repository.create_many = AsyncMock(return_value=notifications)

        # Все пользователи имеют разрешенные каналы
        mock_settings = Mock(spec=NotificationSettings)
        mock_settings.in_app_enabled = True
        mock_settings.telegram_enabled = True
        mock_settings.email_enabled = True
        mock_settings_repository.get_or_create = AsyncMock(return_value=mock_settings)

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
            mock_settings_repository,
        )

        # when
        with patch.object(service, "_dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
            result, status_code = await service.send_to_project_participants(
                project_id=1,
                sender_id=2,
                template_key="project_announcement",
                payload={"project_name": "Test Project", "message": "Hello"},
            )

        # then
        assert result == notifications
        assert status_code == EXPECTED_OK_STATUS
        assert mock_dispatch.call_count == EXPECTED_PARTICIPANTS_COUNT
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
        mock_settings_repository = Mock(spec=NotificationSettingsRepository)

        mock_project_repository.get_by_id = AsyncMock(return_value=None)

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
            mock_settings_repository,
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
        mock_settings_repository = Mock(spec=NotificationSettingsRepository)

        mock_notification_repository.get_by_id = AsyncMock(
            return_value=Notification(
                id="test-id",
                recipient_id=1,
                sender_id=2,
                project_id=None,
                type="system_alert",
                status="pending",
                title="Системное уведомление",
                body="Test message",
                channels=["in-app"],
                created_at=datetime.now(),
            )
        )
        mock_notification_repository.update_status = AsyncMock()

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
            mock_settings_repository,
        )

        # when
        await service.execute_external_sending("test-id")

        # then
        mock_notification_repository.get_by_id.assert_called_once_with("test-id")
        mock_notification_repository.update_status.assert_called_once_with("test-id", "sent")

    @pytest.mark.asyncio
    async def test_should_trigger_telegram_task(self):
        """Проверка, что таска Telegram вызывается при отправке уведомления"""
        # given
        mock_notification_repository = Mock(spec=NotificationRepository)
        mock_project_repository = Mock(spec=ProjectRepository)
        mock_participation_repository = Mock(spec=ProjectParticipationRepository)
        mock_settings_repository = Mock(spec=NotificationSettingsRepository)

        mock_notification = Mock(id="test-notif-id")
        mock_notification_repository.create = AsyncMock(return_value=mock_notification)

        # Пользователь разрешил Telegram канал
        mock_settings = Mock(spec=NotificationSettings)
        mock_settings.in_app_enabled = False
        mock_settings.telegram_enabled = True
        mock_settings.email_enabled = False
        mock_settings_repository.get_or_create = AsyncMock(return_value=mock_settings)

        service = NotificationService(
            mock_notification_repository,
            mock_project_repository,
            mock_participation_repository,
            mock_settings_repository,
        )

        # when
        with patch.object(service, "_dispatch_notification", new_callable=AsyncMock) as mock_dispatch:
            await service.send_to_user(
                recipient_id=1,
                sender_id=2,
                template_key="system_alert",
                payload={"message": "test"},
                channels=["telegram"],
            )

        # then
        # Проверяем что _dispatch_notification вызвана с правильными аргументами
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args[0]
        assert call_args[0] == "test-notif-id"  # notification_id
        assert "telegram" in call_args[1]  # channels
        assert call_args[2] == 1  # recipient_id

    def test_send_email_notification_success(self):
        """Тест успешной отправки email уведомления"""
        # given
        notification = Notification(
            id="test-id",
            recipient_id=1,
            sender_id=2,
            project_id=None,
            type="system_alert",
            status="pending",
            title="Test Title",
            body="Test Body",
            channels=[],
            created_at=datetime.now(),
        )


        user = User(
            id=1,
            email="user@test.com",
            first_name="Test",
            middle_name="User",
            password_hashed="hashed",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


        settings = NotificationSettings(
            id=1,
            user_id=1,
            email_enabled=True,
            telegram_enabled=True,
            in_app_enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


        # when
        with patch("src.services.notification_tasks.SqlAlchemyUoW") as mock_uow_class:
            mock_uow = AsyncMock()
            mock_uow.__aenter__.return_value = mock_uow
            mock_uow.__aexit__.return_value = None
            mock_uow_class.return_value = mock_uow


            with patch("src.services.notification_tasks.NotificationRepository") as mock_repo_class:
                mock_repo = Mock(spec=NotificationRepository)
                mock_repo.get_by_id = AsyncMock(return_value=notification)
                mock_repo_class.return_value = mock_repo


                with patch("src.services.notification_tasks.select"):
                    mock_result = Mock()
                    mock_result.scalar_one_or_none.return_value = user
                    mock_uow.session.execute = AsyncMock(return_value=mock_result)


                    with patch("src.services.notification_tasks.NotificationSettingsRepository") as mock_settings_repo_class:
                        mock_settings_repo = Mock(spec=NotificationSettingsRepository)
                        mock_settings_repo.get_by_user_id = AsyncMock(return_value=settings)
                        mock_settings_repo_class.return_value = mock_settings_repo


                        with patch("src.services.notification_tasks.EmailSender") as mock_email_sender_class:
                            mock_email_sender = Mock()
                            mock_email_sender.send_email.return_value = True
                            mock_email_sender_class.return_value = mock_email_sender


                            send_email_notification.apply(args=("test-id",))


        # then
        mock_email_sender.send_email.assert_called_once_with(
            to_email="user@test.com",
            subject="Test Title",
            body="Test Body",
        )


    def test_send_email_notification_no_notification(self):
        """Тест когда уведомление не найдено"""
        # when
        with patch("src.services.notification_tasks.SqlAlchemyUoW") as mock_uow_class:
            mock_uow = AsyncMock()
            mock_uow.__aenter__.return_value = mock_uow
            mock_uow.__aexit__.return_value = None
            mock_uow_class.return_value = mock_uow


            with patch("src.services.notification_tasks.NotificationRepository") as mock_repo_class:
                mock_repo = Mock(spec=NotificationRepository)
                mock_repo.get_by_id = AsyncMock(return_value=None)
                mock_repo_class.return_value = mock_repo


                with patch("src.services.notification_tasks.EmailSender") as mock_email_sender_class:
                    send_email_notification.apply(args=("test-id",))


        # then
        mock_email_sender_class.assert_not_called()


    def test_send_email_notification_no_user_email(self):
        """Тест когда у пользователя нет email"""
        # given
        notification = Notification(
            id="test-id",
            recipient_id=1,
            sender_id=2,
            project_id=None,
            type="system_alert",
            status="pending",
            title="Test Title",
            body="Test Body",
            channels=[],
            created_at=datetime.now(),
        )


        user = User(
            id=1,
            email=None,
            first_name="Test",
            middle_name="User",
            password_hashed="hashed",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


        # when
        with patch("src.services.notification_tasks.SqlAlchemyUoW") as mock_uow_class:
            mock_uow = AsyncMock()
            mock_uow.__aenter__.return_value = mock_uow
            mock_uow.__aexit__.return_value = None
            mock_uow_class.return_value = mock_uow


            with patch("src.services.notification_tasks.NotificationRepository") as mock_repo_class:
                mock_repo = Mock(spec=NotificationRepository)
                mock_repo.get_by_id = AsyncMock(return_value=notification)
                mock_repo_class.return_value = mock_repo


                with patch("src.services.notification_tasks.select"):
                    mock_result = Mock()
                    mock_result.scalar_one_or_none.return_value = user
                    mock_uow.session.execute = AsyncMock(return_value=mock_result)


                    with patch("src.services.notification_tasks.EmailSender") as mock_email_sender_class:
                        send_email_notification.apply(args=("test-id",))


        # then
        mock_email_sender_class.assert_not_called()


    def test_send_email_notification_email_disabled(self):
        """Тест когда email уведомления отключены в настройках"""
        # given
        notification = Notification(
            id="test-id",
            recipient_id=1,
            sender_id=2,
            project_id=None,
            type="system_alert",
            status="pending",
            title="Test Title",
            body="Test Body",
            channels=[],
            created_at=datetime.now(),
        )


        user = User(
            id=1,
            email="user@test.com",
            first_name="Test",
            middle_name="User",
            password_hashed="hashed",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


        settings = NotificationSettings(
            id=1,
            user_id=1,
            email_enabled=False,
            telegram_enabled=True,
            in_app_enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


        # when
        with patch("src.services.notification_tasks.SqlAlchemyUoW") as mock_uow_class:
            mock_uow = AsyncMock()
            mock_uow.__aenter__.return_value = mock_uow
            mock_uow.__aexit__.return_value = None
            mock_uow_class.return_value = mock_uow


            with patch("src.services.notification_tasks.NotificationRepository") as mock_repo_class:
                mock_repo = Mock(spec=NotificationRepository)
                mock_repo.get_by_id = AsyncMock(return_value=notification)
                mock_repo_class.return_value = mock_repo


                with patch("src.services.notification_tasks.select"):
                    mock_result = Mock()
                    mock_result.scalar_one_or_none.return_value = user
                    mock_uow.session.execute = AsyncMock(return_value=mock_result)


                    with patch("src.services.notification_tasks.NotificationSettingsRepository") as mock_settings_repo_class:
                        mock_settings_repo = Mock(spec=NotificationSettingsRepository)
                        mock_settings_repo.get_by_user_id = AsyncMock(return_value=settings)
                        mock_settings_repo_class.return_value = mock_settings_repo


                        with patch("src.services.notification_tasks.EmailSender") as mock_email_sender_class:
                            send_email_notification.apply(args=("test-id",))


        # then
        mock_email_sender_class.assert_not_called()

