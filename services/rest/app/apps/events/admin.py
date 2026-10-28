from django import forms
from django.contrib import admin
from django.http import HttpRequest

from apps.events.models import Event, EventLog
from django_json_widget.widgets import JSONEditorWidget


class EventForm(forms.ModelForm):
    class Meta:
        model = Event

        fields = ("processing",)
        widgets = {"processing": JSONEditorWidget}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    form = EventForm
    list_display = (
        "id",
        "type",
    )
    fields = (
        "type",
        "processing",
    )
    readonly_fields = ("id",)
    ordering = ("type",)

    def has_add_permission(
        self,
        request: HttpRequest,
    ) -> bool:
        return True

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: Event = None,
    ) -> bool:
        return True

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: Event = None,
    ) -> bool:
        return True


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "state",
        "payload",
        "actions_log",
        "retry_count",
        "dedup_key",
        "created_at",
        "updated_at",
    )
    readonly_fields = list_display
    fields = list_display
    list_filter = ("type", "state")
    search_fields = ("=id", "dedup_key", "type")
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: EventLog = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: EventLog = None) -> bool:
        return False
