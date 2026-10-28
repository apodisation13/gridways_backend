from django import forms
from django.contrib import admin
from django.db import models
from django.http import HttpRequest

from apps.enemies.models import Enemy
from apps.seasons.models import Level, LevelEnemy, LevelRelatedLevels, Season, SeasonRelatedSeasons
from django_json_widget.widgets import JSONEditorWidget


class SeasonRelatedSeasonsInline(admin.TabularInline):
    model = SeasonRelatedSeasons
    fk_name = "season"
    fields = ("line", "related_season", "connection")
    readonly_fields = ("connection",)
    autocomplete_fields = ("related_season",)
    extra = 0

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("season", "related_season")


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unlocked", "x", "y")
    search_fields = ("name",)
    inlines = (SeasonRelatedSeasonsInline,)
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}


class LevelEnemyInLine(admin.TabularInline):
    model = LevelEnemy
    extra = 0
    verbose_name_plural = "level enemies"
    autocomplete_fields = ("enemy",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("level", "enemy__faction", "enemy__color", "enemy__move")

    def formfield_for_foreignkey(
        self, db_field: models.ForeignKey, request: HttpRequest, **kwargs,
    ) -> forms.ModelChoiceField:
        if db_field.name == "enemy":
            kwargs["queryset"] = Enemy.objects.select_related("faction", "color", "move")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class LevelInline(admin.TabularInline):
    model = LevelRelatedLevels
    fk_name = "level"
    fields = ("line", "related_level")
    extra = 0
    verbose_name_plural = "level related levels"
    autocomplete_fields = ("related_level",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("level", "related_level")


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    inlines = (LevelEnemyInLine, LevelInline)
    list_filter = ("difficulty", "enemy_leader_id", "season")
    list_display = (
        "id", "name", "starting_enemies_number", "difficulty", "enemy_leader_admin",
        "number_of_enemies_admin", "get_related_levels", "x", "y", "season",
    )
    list_display_links = ("id", "name")
    search_fields = ("name",)
    autocomplete_fields = ("season", "enemy_leader")
    formfield_overrides = {models.JSONField: {"widget": JSONEditorWidget}}

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return (
            super().get_queryset(request)
            .select_related("season", "enemy_leader__ability", "enemy_leader__passive_ability")
            .annotate(enemies_count=models.Count("l", distinct=True))
            .prefetch_related(models.Prefetch("related_levels", queryset=Level.objects.only("id", "name")))
        )

    def formfield_for_foreignkey(
        self, db_field: models.ForeignKey, request: HttpRequest, **kwargs,
    ) -> forms.ModelChoiceField:
        if db_field.name == "enemy_leader":
            kwargs["queryset"] = db_field.remote_field.model.objects.select_related("ability", "passive_ability")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="enemy_leader")
    def enemy_leader_admin(self, obj: Level) -> str:
        return f"{obj.enemy_leader.name} - {obj.enemy_leader.ability}"

    @admin.display(description="en_№", ordering="enemies_count")
    def number_of_enemies_admin(self, obj: Level) -> int:
        return obj.number_of_enemies()
