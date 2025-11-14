import os

from dotenv import load_dotenv

from lib.utils.config.env_types import EnvType


if "CONFIG" not in os.environ:
    load_dotenv()


class BaseConfig:
    """Все настройки через env переменные"""
    ENV_TYPE: EnvType = EnvType.DEVELOPMENT_LOCAL

    DEBUG: bool = False
    TESTING: bool = False

    # Environment
    CONFIG: str = os.getenv("CONFIG")

    # Database
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME")

    DB_URL: str = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class TestingConfig(BaseConfig):
    ENV_TYPE: EnvType = EnvType.TESTING


class ProductionConfig(BaseConfig):
    ENV_TYPE: EnvType = EnvType.PRODUCTION


class DevelopmentLocalConfig(BaseConfig):
    ENV_TYPE: EnvType = EnvType.DEVELOPMENT_LOCAL


class TestsLocalConfig(BaseConfig):
    load_dotenv()

    ENV_TYPE: EnvType = EnvType.TEST_LOCAL

    DB_USER: str = os.getenv("TEST_DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("TEST_DB_PASSWORD")
    DB_HOST: str = os.getenv("TEST_DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("TEST_DB_HOST", "5432"))
    DB_NAME: str = os.getenv("TEST_DB_NAME", "test_db")

    DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    DEBUG: bool = True
    TESTING: bool = True


CONFIG_MAP = {
    EnvType.TEST_LOCAL: TestsLocalConfig,
    EnvType.DEVELOPMENT_LOCAL: DevelopmentLocalConfig,
    EnvType.TESTING: TestingConfig,
    EnvType.PRODUCTION: ProductionConfig,
}


def get_config() -> BaseConfig:
    config_name: str = os.getenv("CONFIG", "development_local")

    if config_name not in CONFIG_MAP:
        raise ValueError(f"Unknown config: {config_name}")

    env_type: EnvType = EnvType(config_name)
    config_class = CONFIG_MAP[env_type]

    return config_class()


# Глобальный инстанс настроек
config: BaseConfig = get_config()
