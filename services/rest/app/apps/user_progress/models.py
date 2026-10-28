from django.db import models

from apps.accounts.models import User
from apps.cards.models import Deck as BaseDeck


class UserResource(models.Model):
    class Meta:
        managed = False
        db_table = "user_resources"
        verbose_name = "Ресурсы пользователя"
        verbose_name_plural = "Ресурсы пользователей"

    id = models.OneToOneField(User, primary_key=True, on_delete=models.PROTECT, db_column="id", editable=True)
    money = models.IntegerField(default=3000, blank=False, null=False)
    scraps = models.IntegerField(default=1000, blank=False, null=False)
    crops = models.IntegerField(default=1000, blank=False, null=False)
    wood = models.IntegerField(default=1000, blank=False, null=False)
    silk = models.IntegerField(default=0, blank=False, null=False)
    flowers = models.IntegerField(default=0, blank=False, null=False)
    kegs = models.IntegerField(default=0, blank=False, null=False)
    big_kegs = models.IntegerField(default=0, blank=False, null=False)
    chests = models.IntegerField(default=0, blank=False, null=False)
    keys = models.IntegerField(default=1, blank=False, null=False)
    raw_bronze = models.IntegerField(default=0, blank=False, null=False)
    raw_silver = models.IntegerField(default=0, blank=False, null=False)
    raw_gold = models.IntegerField(default=0, blank=False, null=False)
    bronze_ingots = models.IntegerField(default=0, blank=False, null=False)
    silver_ingots = models.IntegerField(default=0, blank=False, null=False)
    gold_ingots = models.IntegerField(default=0, blank=False, null=False)
    rare_gem = models.IntegerField(default=0, blank=False, null=False)
    # inventory items
    first_aid_kits = models.IntegerField(default=0, blank=False, null=False)
    shields = models.IntegerField(default=0, blank=False, null=False)
    immune_magics = models.IntegerField(default=0, blank=False, null=False)
    draw_cards = models.IntegerField(default=0, blank=False, null=False)
    mega_bombs = models.IntegerField(default=0, blank=False, null=False)
    random_bombs = models.IntegerField(default=0, blank=False, null=False)
    clears = models.IntegerField(default=0, blank=False, null=False)
    purifies = models.IntegerField(default=0, blank=False, null=False)
    random_effects = models.IntegerField(default=0, blank=False, null=False)


    def __str__(self) -> str:
        return f"Юзер {self.pk}: {self.id.username} {self.id.email}"


class UserJSONData(models.Model):
    user = models.OneToOneField(
        User, primary_key=True, db_column="id", on_delete=models.PROTECT, verbose_name="Пользователь",
    )
    data = models.JSONField(default=dict, blank=True, verbose_name="Данные")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        abstract = True
        managed = False

    def __str__(self) -> str:
        return f"Юзер {self.pk}: {self.user.username} {self.user.email}"


class UserUpgrades(UserJSONData):
    class Meta:
        managed = False
        db_table = "user_upgrades"
        verbose_name = "Апгрейды пользователя"
        verbose_name_plural = "Апгрейды пользователей"


class UserPreferences(UserJSONData):
    class Meta:
        managed = False
        db_table = "user_preferences"
        verbose_name = "Настройки пользователя"
        verbose_name_plural = "Настройки пользователей"


class UserInventory(UserJSONData):
    class Meta:
        managed = False
        db_table = "user_inventory"
        verbose_name = "Инвентарь пользователя"
        verbose_name_plural = "Инвентари пользователей"


class UserProgressEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        abstract = True
        managed = False


class UserCard(UserProgressEntry):
    card = models.ForeignKey("cards.Card", on_delete=models.PROTECT, verbose_name="Карта")
    count = models.IntegerField(default=0, verbose_name="Количество")

    class Meta:
        managed = False
        db_table = "user_cards"
        verbose_name = "Карта пользователя"
        verbose_name_plural = "Карты пользователей"
        unique_together = (("user", "card"),)

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: карта {self.card_id}, количество {self.count}"


class UserLeader(UserProgressEntry):
    leader = models.ForeignKey("cards.Leader", on_delete=models.PROTECT, verbose_name="Лидер")
    count = models.IntegerField(default=0, verbose_name="Количество")

    class Meta:
        managed = False
        db_table = "user_leaders"
        verbose_name = "Лидер пользователя"
        verbose_name_plural = "Лидеры пользователей"
        unique_together = (("user", "leader"),)

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: лидер {self.leader_id}, количество {self.count}"


class UserSeason(UserProgressEntry):
    season = models.ForeignKey("seasons.Season", on_delete=models.PROTECT, verbose_name="Сезон")
    finished = models.BooleanField(default=False, verbose_name="Завершён")

    class Meta:
        managed = False
        db_table = "user_seasons"
        verbose_name = "Сезон пользователя"
        verbose_name_plural = "Сезоны пользователей"
        unique_together = (("user", "season"),)

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: сезон {self.season_id}"


class UserLevel(UserProgressEntry):
    level = models.ForeignKey("seasons.Level", on_delete=models.PROTECT, verbose_name="Уровень")
    finished = models.BooleanField(default=False, verbose_name="Завершён")

    class Meta:
        managed = False
        db_table = "user_levels"
        verbose_name = "Уровень пользователя"
        verbose_name_plural = "Уровни пользователей"
        unique_together = (("user", "level"),)

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: уровень {self.level_id}"


class Deck(BaseDeck):
    """Та же таблица decks, отображаемая в разделе прогресса пользователей."""

    class Meta:
        proxy = True
        managed = False
        verbose_name = "Колода"
        verbose_name_plural = "Колоды"


class UserDeck(UserProgressEntry):
    deck = models.ForeignKey("cards.Deck", on_delete=models.PROTECT, verbose_name="Колода")

    class Meta:
        managed = False
        db_table = "user_decks"
        verbose_name = "Владелец колоды"
        verbose_name_plural = "Владельцы колоды"
        unique_together = (("user", "deck"),)

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: колода {self.deck_id}"
