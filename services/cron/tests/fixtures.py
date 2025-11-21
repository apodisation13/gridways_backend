import pytest

from services.cron.app.config import Config, get_config


@pytest.fixture(scope="session")
def config() -> Config:
    return get_config()
