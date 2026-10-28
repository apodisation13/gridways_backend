import os

from django.core.wsgi import get_wsgi_application

from services.rest.app.sql_logging import configure_sql_logging_if_enabled


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config")


def init_app():
    import logging.config

    from lib.utils.elk.elastic_logger import ElasticLoggerManager
    from services.rest.app.config import Config, get_config

    config: Config = get_config()

    logging.config.dictConfig(config.LOGGING)

    elastic_logger_manager = ElasticLoggerManager()
    elastic_logger_manager.initialize(
        config=config,
        service_name="django_admin",
        delay_seconds=5,
    )

    logger = logging.getLogger(__name__)
    logger.info("REST is starting...")


# Инициализируем при импорте wsgi (при запуске gunicorn)
init_app()

application = get_wsgi_application()

# runserver уже вызывал django.setup(): WSGI повторно сбрасывает логгеры, но не вызывает ready().
configure_sql_logging_if_enabled()
