from django import forms
from django.contrib import admin
from django.db import models
from django.http import HttpRequest

from apps.cards.models import Leader
from apps.stats.models import Leaderboard, UserStats


class UserStatsAdminBase(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("user",)

    @admin.display(description="Пользователь", ordering="user_id")
    def user_label(self, obj: models.Model) -> str:
        return f"Юзер {obj.user_id}: {obj.user.username} {obj.user.email}"


@admin.register(UserStats)
class UserStatsAdmin(UserStatsAdminBase):
    list_display = ("id", "user_label", "faction", "type", "count", "created_at", "updated_at")
    list_filter = ("type", "faction")
    search_fields = ("=user__id", "user__username", "user__email", "faction__name")

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user", "faction")


@admin.register(Leaderboard)
class LeaderboardAdmin(UserStatsAdminBase):
    list_display = ("id", "user_label", "leader", "mode", "max_kills", "created_at", "updated_at")
    list_filter = ("mode",)
    search_fields = ("=user__id", "user__username", "user__email", "leader__name")
    autocomplete_fields = ("user", "leader")

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user", "leader__ability")

    def formfield_for_foreignkey(
        self, db_field: models.ForeignKey, request: HttpRequest, **kwargs,
    ) -> forms.ModelChoiceField:
        if db_field.name == "leader":
            kwargs["queryset"] = Leader.objects.select_related("ability")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
