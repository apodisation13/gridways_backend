import json

from aiokafka import AIOKafkaProducer
from jinja2 import Template
from typing import Dict, Optional, Any

from lib.utils.events.event_types import EventType


class EventSender:
    def __init__(self, config):
        self._producer = None
        self._initialized = False
        self.config = config

    async def _ensure_initialized(self):
        """Инициализирует producer если еще не инициализирован"""
        if not self._initialized:
            bootstrap_servers = self.config.KAFKA_BOOTSTRAP_SERVERS
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await self._producer.start()
            self._initialized = True

    async def event(self, event_type: EventType, payload: Dict):
        """Отправка события в Kafka"""
        await self._ensure_initialized()

        message = {
            'event_type': event_type.value if hasattr(event_type, 'value') else event_type,
            'payload': payload
        }

        try:
            topic = self.config.KAFKA_TOPIC
            await self._producer.send_and_wait(topic, message)
            return True

        except Exception as e:
            # При ошибке сбрасываем состояние и пробуем переинициализировать при следующем вызове
            self._initialized = False
            if self._producer:
                await self._producer.stop()
                self._producer = None
            raise Exception(f"Failed to send event to Kafka: {e}")

    async def close(self):
        """Закрытие соединения"""
        if self._producer and self._initialized:
            await self._producer.stop()
            self._initialized = False


# Глобальный инстанс с ленивой инициализацией
_event_sender: Optional[EventSender] = None


def get_event_sender(config) -> EventSender:
    """Получить или создать инстанс EventSender"""
    global _event_sender
    if _event_sender is None:
        _event_sender = EventSender(config)
    return _event_sender


async def event(event_type: EventType, payload: Dict, config):
    """
    Основная функция для отправки событий.
    Автоматически инициализирует соединение при первом вызове.
    """
    sender = get_event_sender(config)
    return await sender.event(event_type, payload)


def close_event_sender():
    """Явное закрытие соединения (опционально)"""
    global _event_sender
    if _event_sender:
        _event_sender.close()
        _event_sender = None
