from django.db import models

from apps.accounts.models import User


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
