import smtplib
import ssl

import aiosmtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
import logging

from lib.utils.config.base import BaseConfig


logger = logging.getLogger(__name__)


class BaseClient(ABC):
    """Базовый класс для клиентов отправки сообщений"""

    def __init__(self, config: BaseConfig):
        self.config = config

    @abstractmethod
    async def send(self, to: str, message: str, subject: str | None = None) -> bool:
        """Отправка сообщения"""
        pass


class EmailClient(BaseClient):
    """Клиент для отправки email сообщений"""

    def __init__(self, config: BaseConfig):
        super().__init__(config)

    async def send(self, to: str, message: str, subject: str | None = None) -> bool:
        """Асинхронная отправка email"""
        try:
            # Создание сообщения
            msg = MIMEMultipart()
            msg['From'] = self.config.EMAIL_USER
            msg['To'] = to
            msg['Subject'] = subject or "Уведомление"
            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP_SSL(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email отправлен на {to}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False


class SmsClient(BaseClient):
    """Клиент для отправки SMS сообщений"""

    def __init__(self, config: BaseConfig):
        super().__init__(config)

    async def send(self, to: str, message: str, subject: str | None = None) -> bool:
        """Отправка SMS через email2sms"""
        try:
            # Формируем email адрес для SMS
            sms_email = f"{self.config.SMS_TOKEN}+{to}@sms.ru"

            # mts_email = f"{to}@sms.mts.ru"

            print(555555555555555555555555, sms_email)

            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = self.config.EMAIL_USER
            msg['To'] = sms_email
            msg['Subject'] = "SMS"  # Тема не важна для SMS

            # Текст сообщения - это и будет SMS
            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP_SSL(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.login(self.config.EMAIL_USER, self.config.EMAIL_PASSWORD)
                server.send_message(msg)

            logger.info(f"SMS отправлено на {to} через email2sms")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
            return False


class TelegramClient(BaseClient):
    """Клиент для отправки сообщений в Telegram"""

    def __init__(self, config: BaseConfig):
        super().__init__(config)

    async def send(self, to: str, message: str, subject: str | None = None) -> bool:
        """Отправка сообщения в Telegram"""
        try:
            # Формирование URL для API Telegram
            url = f"https://api.telegram.org/bot{self.config.TG_TOKEN}/sendMessage"

            # Параметры запроса
            payload = {
                'chat_id': to,  # ID чата или пользователя
                'text': message,
                'parse_mode': 'HTML'
            }

            # Отправка запроса
            response = requests.post(url, data=payload, timeout=30)
            result = response.json()

            if result.get('ok'):
                logger.info(f"Сообщение отправлено в Telegram chat_id: {to}")
                return True
            else:
                logger.error(f"Ошибка Telegram API: {result.get('description')}")
                return False

        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False


# # Пример использования
# if __name__ == "__main__":
#     # Настройка логирования
#     logging.basicConfig(level=logging.INFO)
#
#     # Конфигурации для разных клиентов
#     email_config = {
#         'smtp_server': 'smtp.gmail.com',
#         'smtp_port': 587,
#         'username': 'your_email@gmail.com',
#         'password': 'your_app_password'
#     }
#
#     sms_config = {
#         'api_key': 'your_sms_api_key',
#         'api_url': 'https://sms-provider.com/api/send',
#         'sender_name': 'YourCompany'
#     }
#
#     telegram_config = {
#         'bot_token': 'your_bot_token_here'
#     }
#
#     try:
#         # Создание клиентов
#         email_client = EmailClient(email_config)
#         sms_client = SmsClient(sms_config)
#         telegram_client = TelegramClient(telegram_config)
#
#         # Отправка тестовых сообщений
#         test_message = "Тестовое сообщение от системы уведомлений"
#
#         # Email (замените на реальный email)
#         email_client.send("recipient@example.com", test_message, "Тестовое уведомление")
#
#         # SMS (замените на реальный номер телефона)
#         sms_client.send("+79123456789", test_message)
#
#         # Telegram (замените на реальный chat_id)
#         telegram_client.send("123456789", test_message)
#
#     except Exception as e:
#         print(f"Ошибка инициализации клиентов: {e}")