from future import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.config import settings
from src.core.logging_config import get_logger

logger = get_logger(name)

"""Класс для отправки email через SMTP"""
class EmailSender:

    """Инициализация EmailSender с параметрами из config.py"""
    def init(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USERNAME 
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_MAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS

    """Отправление письма на email получателю"""
    def send_email(self, to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
        """
        Args:
            to_email: Email адрес получателя
            subject: Тема письма
            body: Текст письма (plain text)
            html_body: HTML версия письма (опционально)
        """
        if not self.host or not self.user or not self.password:
            logger.warning("SMTP параметры не настроены, письмо не отправлено")
            return False

        try:
            # Создаем сообщение
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
            msg["To"] = to_email

            # Добавляем plain text версию
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            # Добавляем HTML версию, если она есть
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                msg.attach(html_part)

            # Подключаемся к SMTP серверу и отправляем
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            logger.info("Email успешно отправлен на %s", to_email)
            return True

        except smtplib.SMTPException as e:
            logger.error("Ошибка SMTP при отправке email на %s: %s", to_email, str(e))
            return False
        except Exception as e:
            logger.exception("Неожиданная ошибка при отправке email на %s: %s", to_email, str(e))
            return False