import logging

from lib.utils.tasks.base import TaskBase


logger = logging.getLogger(__name__)


class TaskTwo(TaskBase):
    name = "task_two"

    async def do(self):
        logger.info("TASK2 Starting TaskTwo execution")

        async with self.db.connection() as conn:
            users = await conn.fetch("SELECT * FROM users ORDER BY id DESC LIMIT 1")
            logger.info("TASK2 Total users in database: %s", users)

        logger.info("TASK2 completed successfully")
