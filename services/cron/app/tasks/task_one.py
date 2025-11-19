import logging

from lib.utils.tasks.base import TaskBase


logger = logging.getLogger(__name__)


class TaskOne(TaskBase):
    name = "task_one"

    async def do(self):
        logger.info("Starting TaskOne execution")

        print("STR15", type(self.db))

        async with self.db.connection() as conn:
            users = await conn.fetch("SELECT * FROM users")
            logger.info(f"Total tasks in database: {len(users)}")

        # for user in users:
        #     logger.info(user)

        logger.info("TaskOne completed successfully")
