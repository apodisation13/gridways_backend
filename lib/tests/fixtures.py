# import asyncio
# from collections.abc import AsyncGenerator
# import asyncpg
# import pytest_asyncio
# from sqlalchemy.ext.asyncio import create_async_engine
# from lib.utils.config.base import config
# from lib.utils.models import Base  # Ваш базовый класс для моделей
#
#
# @pytest_asyncio.fixture(scope="session")
# async def setup_database():
#     """Настройка БД для тестов - простая версия"""
#
#     # Проверяем/создаем БД
#     try:
#         conn = await asyncpg.connect(
#             host=config.DB_HOST,
#             port=config.DB_PORT,
#             user=config.DB_USER,
#             password=config.DB_PASSWORD,
#             database=config.DB_NAME
#         )
#         await conn.close()
#         print(f"\n✅ Connected to test database '{config.DB_NAME}'")
#     except asyncpg.InvalidCatalogNameError:
#         pass
#
#     # Создаем все таблицы через SQLAlchemy
#     engine = create_async_engine(
#         config.DB_URL,
#         echo=False  # Поставьте True для отладки SQL
#     )
#
#     async with engine.begin() as conn:
#         # Удаляем все таблицы
#         await conn.run_sync(Base.metadata.drop_all)
#         # Создаем все таблицы
#         await conn.run_sync(Base.metadata.create_all)
#         print("✅ Tables created")
#
#     await engine.dispose()
#
#     yield
#
#     # После всех тестов можно очистить таблицы (опционально)
#     engine = create_async_engine(
#         config.DB_URL,
#         echo=False,
#     )
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#         print("✅ Tables dropped")
#     await engine.dispose()
#
#
# @pytest_asyncio.fixture(scope="session")
# async def db_pool(setup_database) -> AsyncGenerator[asyncpg.Pool, None]:
#     """Создание пула подключений для всей сессии"""
#     pool = await asyncpg.create_pool(
#         dsn=config.DB_URL.replace("postgresql+asyncpg://", "postgresql://"),
#         # dsn=config.DB_URL,
#         min_size=1,
#         max_size=10,
#         command_timeout=60
#     )
#     print("✅ Connection pool created")
#
#     yield pool
#
#     await pool.close()
#     print("✅ Connection pool closed")
#
#
# @pytest_asyncio.fixture(autouse=True)
# async def clean_data(db_pool):
#     """Автоматическая очистка данных после каждого теста"""
#     yield
#
#     async with db_pool.acquire() as conn:
#         # Получаем список всех таблиц (кроме системных)
#         tables = await conn.fetch(
#             """
#                 SELECT tablename
#                 FROM pg_tables
#                 WHERE schemaname = 'public'
#             """
#         )
#
#         if tables:
#             # Отключаем проверку внешних ключей
#             await conn.execute('SET session_replication_role = replica;')
#
#             # Очищаем каждую таблицу
#             for table in tables:
#                 await conn.execute(f'TRUNCATE TABLE "{table["tablename"]}" CASCADE')
#
#             # Включаем обратно проверку внешних ключей
#             await conn.execute('SET session_replication_role = DEFAULT;')
#
#             print("\n✅ Data cleaned")
#
#
# @pytest_asyncio.fixture
# async def db_connection(db_pool) -> AsyncGenerator[asyncpg.Connection, None]:
#     """Подключение для каждого теста"""
#     async with db_pool.acquire() as conn:
#         yield conn
#
#
# @pytest_asyncio.fixture(scope="session")
# def event_loop():
#     """Создаем event loop для всей тестовой сессии"""
#     print('\n', 111111111111111111111111111111111111111111111111111)
#     policy = asyncio.get_event_loop_policy()
#     loop = policy.new_event_loop()
#     asyncio.set_event_loop(loop)
#
#     yield loop
#     print(2222222222222222222222222222222222222222222222222222)
#
#     # Закрываем корректно
#     loop.close()
#     print(3333333333333333333333333333333333333333333333333333)


# lib/tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator
import os
import threading

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from lib.utils.config.base import config
from lib.utils.models import Base

# Глобальные переменные для синглтонов
_event_loop_lock = threading.Lock()
_event_loop = None
_event_loop_closed = False

_db_setup_lock = threading.Lock()
_db_setup_done = False

_db_pool_lock = threading.Lock()
_db_pool = None


@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop - синглтон для всех тестов"""
    global _event_loop, _event_loop_closed

    with _event_loop_lock:
        if _event_loop is None and not _event_loop_closed:
            print('\n🔄 Creating NEW event loop...')
            policy = asyncio.get_event_loop_policy()
            _event_loop = policy.new_event_loop()
            asyncio.set_event_loop(_event_loop)
        else:
            print('\n♻️ Reusing EXISTING event loop')

    yield _event_loop

    # Закрываем только если еще не закрыт
    with _event_loop_lock:
        if _event_loop and not _event_loop_closed:
            print('🔄 Closing event loop...')
            try:
                pending = asyncio.all_tasks(_event_loop)
                for task in pending:
                    task.cancel()

                if pending:
                    _event_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )

                _event_loop.run_until_complete(_event_loop.shutdown_asyncgens())
            finally:
                _event_loop.close()
                _event_loop_closed = True
                print('✅ Event loop closed')


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Настройка БД - синглтон"""
    global _db_setup_done

    with _db_setup_lock:
        if not _db_setup_done:
            print("\n🔧 Setting up database...")

            try:
                conn = await asyncpg.connect(
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    database=config.DB_NAME
                )
                await conn.close()
                print(f"✅ Connected to test database '{config.DB_NAME}'")
            except asyncpg.InvalidCatalogNameError:
                pass

            engine = create_async_engine(config.DB_URL, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
                print("✅ Tables created")
            await engine.dispose()

            _db_setup_done = True
        else:
            print("♻️ Database already setup")

    yield

    # Очистка в конце
    with _db_setup_lock:
        if _db_setup_done:
            print("\n🧹 Cleaning up database...")
            engine = create_async_engine(config.DB_URL, echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                print("✅ Tables dropped")
            await engine.dispose()
            _db_setup_done = False


@pytest_asyncio.fixture(scope="session")
async def db_pool(setup_database) -> AsyncGenerator[asyncpg.Pool, None]:
    """Пул подключений - синглтон"""
    global _db_pool

    with _db_pool_lock:
        if _db_pool is None:
            print("🔌 Creating NEW connection pool...")
            _db_pool = await asyncpg.create_pool(
                dsn=config.DB_URL.replace("postgresql+asyncpg://", "postgresql://"),
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            print("✅ Connection pool created")
        else:
            print("♻️ Reusing EXISTING connection pool")

    yield _db_pool

    # Закрываем в конце
    with _db_pool_lock:
        if _db_pool:
            await _db_pool.close()
            print("✅ Connection pool closed")
            _db_pool = None


@pytest_asyncio.fixture(autouse=True)
async def clean_data(db_pool):
    """Очистка данных после каждого теста"""
    yield

    async with db_pool.acquire() as conn:
        tables = await conn.fetch(
            """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            """
        )

        if tables:
            await conn.execute('SET session_replication_role = replica;')
            for table in tables:
                await conn.execute(f'TRUNCATE TABLE "{table["tablename"]}" CASCADE')
            await conn.execute('SET session_replication_role = DEFAULT;')
            print("✅ Data cleaned")


@pytest_asyncio.fixture
async def db_connection(db_pool) -> AsyncGenerator[asyncpg.Connection, None]:
    """Подключение для каждого теста"""
    async with db_pool.acquire() as conn:
        yield conn
