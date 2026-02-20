from __future__ import annotations

from enum import StrEnum

__all__ = ["NotificationChannel"]


class NotificationChannel(StrEnum):
    """Каналы доставки уведомлений платформы."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    IN_APP = "in-app"
