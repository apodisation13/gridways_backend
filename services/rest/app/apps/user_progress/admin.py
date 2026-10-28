from django.contrib import admin
from django.db import models
from django.http import HttpRequest

from apps.user_progress.models import UserInventory, UserPreferences, UserResource, UserUpgrades
from django_json_widget.widgets import JSONEditorWidget


@admin.register(UserResource)
class UserResourceAdmin(admin.ModelAdmin):
    list_display = ("user_label",)
    list_select_related = ("id",)
    search_fields = ("=id__id", "id__username", "id__email")
    autocomplete_fields = ("id",)

    @admin.display(description="Пользователь", ordering="id")
    def user_label(self, obj: UserResource) -> str:
        return str(obj)


class UserJSONInline(admin.StackedInline):
    fk_name = "user"
    extra = 0
    max_num = 1
    fields = ("data", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user")


class UserUpgradesInline(UserJSONInline):
    model = UserUpgrades


class UserPreferencesInline(UserJSONInline):
    model = UserPreferences


class UserInventoryInline(UserJSONInline):
    model = UserInventory


@admin.register(UserUpgrades, UserPreferences, UserInventory)
class UserJSONAdmin(admin.ModelAdmin):
    list_display = ("user_label", "updated_at")
    list_select_related = ("user",)
    search_fields = ("=user__id", "user__username", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}

    @admin.display(description="Пользователь", ordering="user_id")
    def user_label(self, obj: models.Model) -> str:
        return str(obj)
