"""Простой тест отправки email напрямую через EmailSender с диагностикой"""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))


from src.core.config import settings
from src.util.email_sender import EmailSender


# Тест прямой отправки
print("=" * 60)
print("Тест отправки email через EmailSender")
print("=" * 60)


# Проверка настроек SMTP
print("\n📋 Проверка SMTP настроек:")
print(f"  SMTP_HOST: {settings.SMTP_HOST or '❌ НЕ ЗАПОЛНЕНО'}")
print(f"  SMTP_PORT: {settings.SMTP_PORT}")
print(f"  SMTP_USERNAME: {settings.SMTP_USERNAME or '❌ НЕ ЗАПОЛНЕНО'}")
print(f"  SMTP_PASSWORD: {'***' if settings.SMTP_PASSWORD else '❌ НЕ ЗАПОЛНЕНО'}")
print(f"  SMTP_FROM_MAIL: {settings.SMTP_FROM_MAIL or '❌ НЕ ЗАПОЛНЕНО'}")
print(f"  SMTP_USE_TLS: {settings.SMTP_USE_TLS}")


# Проверяем, все ли параметры заполнены
missing = []
if not settings.SMTP_HOST:
    missing.append("SMTP_HOST")
if not settings.SMTP_USERNAME:
    missing.append("SMTP_USERNAME")
if not settings.SMTP_PASSWORD:
    missing.append("SMTP_PASSWORD")
if not settings.SMTP_FROM_MAIL:
    missing.append("SMTP_FROM_MAIL")


if missing:
    print(f"\n❌ Не заполнены параметры: {', '.join(missing)}")
    print("\nЗаполните их в файле .env в корне проекта:")
    print("  SMTP_HOST=smtp.gmail.com")
    print("  SMTP_USERNAME=your-email@gmail.com")
    print("  SMTP_PASSWORD=your-app-password")
    print("  SMTP_FROM=your-email@gmail.com")
    exit(1)


sender = EmailSender()


# Замените на свой email для тестирования
test_email = input("\nВведите email для тестирования: ").strip()


if not test_email:
    print("❌ Email не указан")
    exit(1)


print(f"\nОтправка тестового письма на {test_email}...\n")


result = sender.send_email(
    to_email=test_email,
    subject="Тестовое уведомление",
    body="Это тестовое сообщение для проверки работы email рассылки.\n\nЕсли вы получили это письмо, значит email рассылка работает корректно!",
)


if result:
    print(f"\n✅ Email успешно отправлен на {test_email}")
    print("Проверьте почтовый ящик (включая папку 'Спам')")
else:
    print(f"\n❌ Не удалось отправить email на {test_email}")
    print("\nВозможные причины:")
    print("1. Неправильный пароль приложения (для Gmail используйте пароль приложения)")
    print("2. Проблемы с подключением к SMTP серверу")
    print("3. Блокировка со стороны почтового провайдера")
    print("\nПроверьте логи выше для деталей ошибки")

