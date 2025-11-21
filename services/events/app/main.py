import asyncio
import logging.config
import os
import sys

# Добавляем корневую директорию проекта в Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.events.app.config import get_config
from services.events.app.event_consumer import EventConsumer


async def main():
    config = get_config()

    logger = logging.getLogger(__name__)
    logging.config.dictConfig(config.LOGGING)

    logger.info("Starting Event Processor...")

    consumer = EventConsumer(config=config)
    await consumer.start_consuming()


if __name__ == "__main__":
    asyncio.run(main())
