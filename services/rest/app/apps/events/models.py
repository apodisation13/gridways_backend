from django.db import models

from lib.utils.events.event_types import EventType


class Event(models.Model):
    class Meta:
        managed = False
        db_table = "events"
        verbose_name = "Событие"
        verbose_name_plural = "События"

    id = models.AutoField(
        primary_key=True,
    )
    type = models.CharField(
        unique=True,
        max_length=255,
        verbose_name="Название события",
        blank=False,
        null=False,
        choices=EventType.choices(),
    )
    processing = models.JSONField(
        default=list,
        blank=True,
        null=True,
        verbose_name="Конфиг события",
    )

    def __str__(self) -> str:
        return f"Событие {self.type}"


class EventLog(models.Model):
    class Meta:
        managed = False
        db_table = "event_log"
        verbose_name = "Запись журнала событий"
        verbose_name_plural = "Журнал событий"
        ordering = ("-created_at",)

    id = models.UUIDField(primary_key=True)
    type = models.CharField(max_length=255, choices=EventType.choices())
    state = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    actions_log = models.JSONField(default=list)
    retry_count = models.IntegerField(default=0)
    dedup_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.type}: {self.id} ({self.state})"
