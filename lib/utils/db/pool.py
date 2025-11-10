import asyncpg

from lib.utils.config.base import BaseConfig


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self) -> asyncpg.Pool:
        """Создание пула подключений"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                dsn=BaseConfig.DB_URL,  # ← Используем как есть!
                min_size=1,
                max_size=10,
                command_timeout=60
            )
        return self.pool

    async def disconnect(self) -> None:
        """Закрытие пула подключений"""
        if self.pool:
            await self.pool.close()
            self.pool = None


# Глобальный инстанс БД
db = Database()
