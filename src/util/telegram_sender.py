from __future__ import annotations
import httpx
from src.core.config import settings
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class TelegramSender:
    def __init__(self, token: str | None = None):
        """Инициализация с токеном из конфига."""
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Отправка сообщения. Возвращает True при успехе."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN is not set in config")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                logger.info(f"Telegram message sent to {chat_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                return False