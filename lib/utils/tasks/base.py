import abc
import asyncio
import time
from typing import Dict, Any, Optional
import asyncpg
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED

from lib.utils.config.base import BaseConfig
from lib.utils.db.pool import Database


logger = logging.getLogger(__name__)


class TaskBase(abc.ABC):
    name: str = "base_task"

    def __init__(
        self,
        config: BaseConfig,
        db: Database,
    ):
        self.config = config
        self.db = db

    @abc.abstractmethod
    async def do(self):
        pass


class TaskScheduler:
    def __init__(
        self,
        config: BaseConfig,
        db: Database,
    ):
        self.config = config
        self.db = db
        self.tasks: Dict[str, Any] = {}

        self.last_reload_time = 0
        self.reload_interval = 60
        self._scheduled_task_ids: set[str] = set()  # ID задач в планировщике

        # Настройка APScheduler
        jobstores = {
            'default': MemoryJobStore()  # или SQLAlchemyJobStore для персистентности
        }

        job_defaults = {
            'coalesce': True,  # объединять пропущенные выполнения
            'max_instances': 1,  # только один экземпляр задачи одновременно
            'misfire_grace_time': 60  # 60 секунд на выполнение пропущенной задачи
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone='UTC',
        )

        # # Подписка на события
        # self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        # self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        # self.scheduler.add_listener(self._job_missed, EVENT_JOB_MISSED)

    def register_task(self, task_class):
        """Регистрирует класс задачи"""
        self.tasks[task_class.name] = task_class
        logger.info(f"Registered task: {task_class.name}")

    async def start(self):
        """Запуск планировщика"""
        logger.info("Starting APScheduler")
        await self._load_tasks_from_db()
        self.scheduler.start()

        # Запускаем фонтовую задачу для проверки изменений
        asyncio.create_task(self._periodic_reload_check())

    async def _get_active_tasks(self):
        async with self.db.connection() as conn:
            active_tasks = await conn.fetch("""SELECT * FROM cron_tasks WHERE is_active is TRUE""")
            print("LEN(active_tasks)", len(active_tasks))
            print("active_tasks", active_tasks)
        return active_tasks

    async def _load_tasks_from_db(self):
        """Загрузка активных задач из базы данных"""
        active_tasks = await self._get_active_tasks()

        for task_record in active_tasks:
            task_name = task_record['name']
            task_id = task_record['id']
            schedule = task_record['schedule']
            print(98, task_name, task_id, schedule)

            if task_name in self.tasks:
                await self._schedule_task(task_id, task_name, schedule)
            else:
                logger.warning(f"Unknown task '{task_name}' found in database")

    async def _execute_task(self, task_class, task_id: int, task_name: str):
        """Выполняет задачу с обработкой ошибок и логированием"""
        task_instance = task_class(self.config, self.db)

        try:
            logger.info(f"Starting execution of task: {task_name}")
            await task_instance.do()

            # Логируем успешное выполнение
            # await self.db.update_task_last_run(task_id, success=True)
            logger.info(f"Task '{task_name}' completed successfully")

        except Exception as e:
            error_msg = f"Task '{task_name}' failed: {str(e)}"
            logger.error(error_msg)

            # Логируем ошибку в БД
            # await self.db.update_task_last_run(task_id, success=False, error_message=error_msg)

    # def _job_executed(self, event):
    #     """Обработчик успешного выполнения задачи"""
    #     if event.job_id.startswith('task_'):
    #         logger.debug(f"Job {event.job_id} executed successfully")
    #
    # def _job_error(self, event):
    #     """Обработчик ошибок выполнения задачи"""
    #     if event.job_id.startswith('task_'):
    #         logger.error(f"Job {event.job_id} failed with exception: {event.exception}")
    #
    # def _job_missed(self, event):
    #     """Обработчик пропущенных задач"""
    #     if event.job_id.startswith('task_'):
    #         logger.warning(f"Job {event.job_id} was missed")

    def stop(self):
        """Останавливает планировщик"""
        self.scheduler.shutdown(wait=False)

    def get_scheduled_jobs(self):
        """Возвращает информацию о запланированных задачах"""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs_info

    async def _periodic_reload_check(self):
        """Периодическая проверка необходимости перезагрузки задач"""
        while True:
            try:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                await self.reload_tasks()

            except Exception as e:
                logger.error(f"Error in periodic reload check: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке

    async def reload_tasks(self):
        """Перезагружает задачи из базы данных"""
        logger.info("Reloading tasks from database!!!!!!!!!!!!!!!!!!!!!!!")

        try:
            db_tasks = await self._get_active_tasks()

            # Создаем множество ID активных задач из БД
            db_task_ids = {f"task_{task['id']}" for task in db_tasks}

            # Удаляем задачи, которых нет в БД или которые неактивны
            for job in self.scheduler.get_jobs():
                if job.id.startswith('task_'):
                    if job.id not in db_task_ids:
                        job.remove()
                        logger.info(f"Removed task: {job.name} (id: {job.id})")

            # Добавляем/обновляем задачи из БД
            for task_record in db_tasks:
                task_name = task_record['name']
                task_id = task_record['id']
                schedule = task_record['schedule']

                if task_name in self.tasks:
                    await self._schedule_task(task_id, task_name, schedule)

            self.last_reload_time = time.time()
            logger.info("Tasks reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload tasks: {e}")

    async def _schedule_task(self, task_id: int, task_name: str, schedule: str):
        """Добавляет или обновляет задачу в планировщике"""
        try:
            task_class = self.tasks[task_name]
            job_id = f"task_{task_id}"

            # Проверяем, существует ли уже задача
            existing_job = self.scheduler.get_job(job_id)

            if existing_job:
                # Если расписание изменилось - обновляем
                current_trigger = str(existing_job.trigger)
                new_trigger = str(CronTrigger.from_crontab(schedule))

                if current_trigger != new_trigger:
                    existing_job.reschedule(trigger=CronTrigger.from_crontab(schedule))
                    logger.info(f"Rescheduled task '{task_name}' with new schedule: {schedule}")
            else:
                # Добавляем новую задачу
                self.scheduler.add_job(
                    self._execute_task,
                    trigger=CronTrigger.from_crontab(schedule),
                    args=[task_class, task_id, task_name],
                    id=job_id,
                    name=task_name,
                    replace_existing=True
                )

        except Exception as e:
            logger.error(f"Failed to schedule task '{task_name}': {e}")
