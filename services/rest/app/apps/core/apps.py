from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Общее для всех карт"

    def ready(self) -> None:
        from services.rest.app.sql_logging import configure_sql_logging_if_enabled

        configure_sql_logging_if_enabled()
