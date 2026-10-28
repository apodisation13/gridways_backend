import os

from django.core.asgi import get_asgi_application

from services.rest.app.sql_logging import configure_sql_logging_if_enabled


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config")

application = get_asgi_application()
configure_sql_logging_if_enabled()
