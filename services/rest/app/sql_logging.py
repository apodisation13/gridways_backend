import logging
import sys
from typing import TYPE_CHECKING

from django.db import connections
from django.db.backends.signals import connection_created


if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper


def enable_sql_debug_cursor(sender: object, connection: "BaseDatabaseWrapper", **kwargs) -> None:
    connection.force_debug_cursor = True


def configure_sql_logging_if_enabled() -> None:
    from services.rest.app.config import get_config

    if get_config().SQL_LOGGING:
        configure_sql_logging()


def configure_sql_logging() -> None:
    logger = logging.getLogger("django.db.backends")
    logger.setLevel(logging.DEBUG)
    # Отдельный вывод в stdout работает и в runserver/management commands, и в Gunicorn.
    # Не дублируем SQL через родительские обработчики, в том числе Elasticsearch.
    logger.propagate = False
    if not any(handler.name == "django_sql_console" for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.set_name("django_sql_console")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)

    connection_created.connect(
        enable_sql_debug_cursor,
        dispatch_uid="rest_sql_logging",
        weak=False,
    )
    for connection in connections.all():
        connection.force_debug_cursor = True
