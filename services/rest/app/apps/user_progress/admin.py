from django import forms
from django.contrib import admin
from django.db import models
from django.http import HttpRequest

from apps.cards.models import Card, CardDeck, Leader
from apps.user_progress.models import (
    Deck,
    UserCard,
    UserDeck,
    UserInventory,
    UserLeader,
    UserLevel,
    UserPreferences,
    UserResource,
    UserSeason,
    UserUpgrades,
)
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


class UserProgressEntryAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    list_display_links = ("id", "user_label")
    ordering = ("user_id", "id")

    @admin.display(description="Пользователь", ordering="user_id")
    def user_label(self, obj: models.Model) -> str:
        return f"Юзер {obj.user_id}: {obj.user.username} {obj.user.email}"

    def formfield_for_foreignkey(
        self,
        db_field: models.ForeignKey,
        request: HttpRequest,
        **kwargs,
    ) -> forms.ModelChoiceField:
        if db_field.name in ("card", "leader"):
            kwargs["queryset"] = db_field.remote_field.model.objects.select_related("ability")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(UserCard)
class UserCardAdmin(UserProgressEntryAdmin):
    list_display = ("id", "user_label", "card", "count", "updated_at")
    autocomplete_fields = ("user", "card")
    search_fields = ("=user__id", "user__username", "user__email", "=card__id", "card__name")
    list_filter = ("card__faction", "card__color")

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user", "card__ability")


@admin.register(UserLeader)
class UserLeaderAdmin(UserProgressEntryAdmin):
    list_display = ("id", "user_label", "leader", "count", "updated_at")
    autocomplete_fields = ("user", "leader")
    search_fields = ("=user__id", "user__username", "user__email", "=leader__id", "leader__name")
    list_filter = ("leader__faction",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user", "leader__ability")


@admin.register(UserSeason)
class UserSeasonAdmin(UserProgressEntryAdmin):
    list_display = ("id", "user_label", "season", "finished", "updated_at")
    autocomplete_fields = ("user", "season")
    search_fields = ("=user__id", "user__username", "user__email", "=season__id", "season__name")
    list_filter = ("finished", "season")

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user", "season")


@admin.register(UserLevel)
class UserLevelAdmin(UserProgressEntryAdmin):
    list_display = ("id", "user_label", "level", "season_label", "finished", "updated_at")
    autocomplete_fields = ("user", "level")
    search_fields = ("=user__id", "user__username", "user__email", "=level__id", "level__name", "level__season__name")
    list_filter = ("finished", "level__season", "level__difficulty")

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user", "level__season")

    @admin.display(description="Сезон", ordering="level__season__name")
    def season_label(self, obj: UserLevel) -> str:
        return str(obj.level.season)


class CardDeckInline(admin.TabularInline):
    model = CardDeck
    extra = 0
    autocomplete_fields = ("card",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("card__ability")

    def formfield_for_foreignkey(
        self,
        db_field: models.ForeignKey,
        request: HttpRequest,
        **kwargs,
    ) -> forms.ModelChoiceField:
        if db_field.name == "card":
            kwargs["queryset"] = Card.objects.select_related("ability")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class UserDeckInline(admin.TabularInline):
    model = UserDeck
    fk_name = "deck"
    extra = 0
    fields = ("user", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("user",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return super().get_queryset(request).select_related("user")


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "leader", "owners_label")
    list_display_links = ("id", "name")
    search_fields = (
        "=id",
        "name",
        "leader__name",
        "=userdeck__user__id",
        "userdeck__user__username",
        "userdeck__user__email",
    )
    autocomplete_fields = ("leader",)
    fields = ("name", "leader")
    inlines = (CardDeckInline, UserDeckInline)

    def get_inlines(self, request: HttpRequest, obj: Deck = None) -> tuple:
        if obj is not None and obj.pk == 1:
            return (CardDeckInline,)
        return self.inlines

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related("leader__ability")
            .prefetch_related(
                models.Prefetch(
                    "userdeck_set",
                    queryset=UserDeck.objects.exclude(deck_id=1).select_related("user").order_by("user_id"),
                    to_attr="owners",
                ),
            )
        )

    @admin.display(description="Владелец")
    def owners_label(self, obj: Deck) -> str:
        if obj.pk == 1:
            return "Общая базовая колода"
        return (
            "; ".join(f"Юзер {owner.user_id}: {owner.user.username} {owner.user.email}" for owner in obj.owners)
            or "Нет владельца"
        )

    def formfield_for_foreignkey(
        self,
        db_field: models.ForeignKey,
        request: HttpRequest,
        **kwargs,
    ) -> forms.ModelChoiceField:
        if db_field.name == "leader":
            kwargs["queryset"] = Leader.objects.select_related("ability")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
