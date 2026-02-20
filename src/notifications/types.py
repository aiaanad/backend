from __future__ import annotations

from enum import StrEnum

__all__ = ["NotificationType"]


class NotificationType(StrEnum):
    """Типы уведомлений для системы оповещений платформы."""

    PROJECT_INVITATION = "project_invitation"
    PROJECT_REMOVAL = "project_removal"
    JOIN_REQUEST = "join_request"
    JOIN_REQUEST_APPROVED = "join_request_approved"
    JOIN_REQUEST_REJECTED = "join_request_rejected"
    PROJECT_ANNOUNCEMENT = "project_announcement"
    SYSTEM_ALERT = "system_alert"
