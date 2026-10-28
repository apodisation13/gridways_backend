from django.db import models

from apps.accounts.models import User
from apps.cards.models import Leader
from apps.core.models import Faction


class UserStats(models.Model):
    class Meta:
        managed = False
        db_table = "user_stats"
        verbose_name = "Статистика пользователя"
        verbose_name_plural = "Статистика пользователей"
        unique_together = (("user", "faction", "type"),)

    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Пользователь")
    faction = models.ForeignKey(Faction, on_delete=models.PROTECT, verbose_name="Фракция")
    type = models.CharField(max_length=16, verbose_name="Тип статистики")
    count = models.IntegerField(default=1, verbose_name="Количество")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: {self.type}, фракция {self.faction_id}"


class Leaderboard(models.Model):
    class Meta:
        managed = False
        db_table = "leaderboard"
        verbose_name = "Рекорд пользователя"
        verbose_name_plural = "Таблица рекордов"
        unique_together = (("user", "leader", "mode"),)
        ordering = ("-max_kills", "id")

    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Пользователь")
    leader = models.ForeignKey(Leader, on_delete=models.PROTECT, verbose_name="Лидер")
    mode = models.CharField(max_length=32, verbose_name="Режим игры")
    max_kills = models.IntegerField(default=1, verbose_name="Максимум убийств")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self) -> str:
        return f"Юзер {self.user_id}: {self.mode}, лидер {self.leader_id}, рекорд {self.max_kills}"
