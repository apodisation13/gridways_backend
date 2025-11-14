import asyncio
from logging.config import fileConfig
import os

# Добавляем корень проекта в PYTHONPATH
import sys

import asyncpg

from alembic import context
from dotenv import load_dotenv
from lib.utils.config.base import BaseConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from lib.utils.models import *  # noqa: F403


load_dotenv()

config = context.config

# Переопределяем URL из alembic.ini нашим конфигом
config.set_main_option("sqlalchemy.url", BaseConfig.DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata  # noqa: F405


def run_migrations_offline() -> None:
    """Запуск миграций в offline режиме"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: asyncpg.Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Запуск миграций в online режиме"""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
