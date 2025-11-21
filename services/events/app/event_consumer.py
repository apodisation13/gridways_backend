import json
import asyncio
import logging

from aiokafka import AIOKafkaConsumer

from lib.utils.db.pool import Database
from lib.utils.events.event_processor import EventProcessor


logger = logging.getLogger(__name__)


class EventConsumer:
    def __init__(self, config):
        self.consumer = None
        self.running = False
        self.config = config

        self.db = None

    async def start_consuming(self):
        """Запуск потребителя событий"""
        db = Database()
        await db.connect()
        self.db = db


        logger.info("Starting event consumer...")

        bootstrap_servers = self.config.KAFKA_BOOTSTRAP_SERVERS
        topic = self.config.KAFKA_TOPIC

        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id="event-processor",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )

        await self.consumer.start()
        self.running = True

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    print("STR51!!!!!!!", message, message.value)
                    await self.process_message(message.value)
                    logger.info(f"Processed event: {message.value.get('event_type')}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            await self.stop()

    async def process_message(self, message_data):
        """Обработка одного сообщения"""

        try:
            processor = EventProcessor(self.db)
            await processor.process_event(message_data)

        except Exception as e:
            logger.error(f"Error processing event: {e}")
        finally:
            await self.db.disconnect()

    async def stop(self):
        """Остановка потребителя"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
