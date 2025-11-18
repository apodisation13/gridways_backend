import os
from unittest.mock import patch, AsyncMock

# Переопределяем конфиг для тестов
os.environ["CONFIG"] = "test_local"
print("STR75))))))))))))))))))))))))))))))))")


import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi.testclient import TestClient
from httpx import AsyncClient

from services.api.app.main import app
from services.api.app.config import get_config as get_app_config


import sys
from pathlib import Path

from lib.tests.conftest import *

__all__ = [
    'event_loop',
    'setup_database',
    'db_pool',
    'clean_data',
    'db_connection'
]

print(11111111111111111111111111)





@pytest_asyncio.fixture
async def client():
    from services.api.app.main import app
    from services.api.app.dependencies import get_db, get_config  # если есть такая зависимость

    # Создаем мок Database
    mock_db = AsyncMock()
    mock_db.pool = db_pool
    test_config = get_app_config()

    # Подменяем зависимость get_db
    async def override_get_db():
        return mock_db

    async def override_get_config():
        return test_config

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_config] = override_get_config

    app.state.config = test_config

    async with AsyncClient(app=app, base_url='http://test') as client:
        yield client

    # Очищаем
    app.dependency_overrides.pop(get_db, None)
    if hasattr(app.state, 'config'):
        del app.state.config


@pytest.fixture(autouse=True)
def override_app_dependencies(db_pool):
    """Подменяем зависимости приложения на тестовые"""
    from services.api.app.main import app

    # Подменяем глобальные зависимости
    app.state.db_pool = db_pool  # если приложение использует app.state.db_pool

    yield

    # Очистка
    if hasattr(app.state, 'db_pool'):
        del app.state.db_pool
