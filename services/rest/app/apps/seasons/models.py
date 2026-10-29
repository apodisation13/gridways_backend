from django.db import models

from apps.enemies.models import Enemy, EnemyLeader
from lib.utils.schemas.game import LevelDifficulty


LINE_CHOICES = (
    ("down", "down"),
    ("up", "up"),
    ("right", "right"),
    ("left", "left"),
    (None, None),
)


class Season(models.Model):
    class Meta:
        managed = False
        db_table = "seasons"
        verbose_name = "Сезон"
        verbose_name_plural = "Сезоны"

    name = models.CharField(
        verbose_name="Название сезона",
        max_length=255,
        blank=False,
        null=False,
    )
    description = models.TextField(
        verbose_name="Описание сезона",
        blank=False,
        null=False,
    )
    unlocked = models.BooleanField(
        verbose_name="Открыт ли сезон по умолчанию",
        default=False,
    )

    x = models.IntegerField(default=0, verbose_name="Координата X")
    y = models.IntegerField(default=0, verbose_name="Координата Y")
    data = models.JSONField(default=dict, blank=True, null=True, verbose_name="Награды сезона")
    related_seasons = models.ManyToManyField(
        "self",
        through="SeasonRelatedSeasons",
        through_fields=("season", "related_season"),
        symmetrical=False,
        related_name="previous_seasons",
    )

    def __str__(self) -> str:
        return f"{self.pk}: {self.name}"


class Level(models.Model):
    class Meta:
        managed = False
        db_table = "levels"
        verbose_name = "Уровень"
        verbose_name_plural = "Уровни"
        ordering = ("-pk",)

    name = models.CharField(
        verbose_name="Название уровня",
        max_length=255,
        blank=False,
        null=False,
        unique=True,
    )
    starting_enemies_number = models.IntegerField(
        verbose_name="Количество стартоваых врагов",
        default=3,
        blank=False,
        null=False,
    )
    difficulty = models.CharField(
        verbose_name="Сложность уровня",
        choices=LevelDifficulty.choices(),
        blank=False,
        null=False,
        max_length=20,
    )
    unlocked = models.BooleanField(
        verbose_name="Открыт ли уровень по умолчанию",
        default=False,
    )
    x = models.IntegerField(
        default=0,
        verbose_name="Координаты уровня по X в дереве на экране",
    )
    y = models.IntegerField(
        default=0,
        verbose_name="Координаты уровня по Y в дереве на экране",
    )

    season = models.ForeignKey(
        Season,
        on_delete=models.PROTECT,
        related_name="levels",
        blank=False,
        null=False,
    )
    enemy_leader = models.ForeignKey(
        EnemyLeader,
        related_name="levels",
        on_delete=models.PROTECT,
        blank=False,
        null=False,
    )

    data = models.JSONField(default=dict, blank=True, null=True, verbose_name="Награды уровня")

    enemies = models.ManyToManyField(
        Enemy,
        related_name="levels",
        through="LevelEnemy",
    )
    related_levels = models.ManyToManyField(
        "Level",
        through="LevelRelatedLevels",
        through_fields=("level", "related_level"),
        symmetrical=False,
        related_name="rel_levels",
    )

    def __str__(self) -> str:
        return f"{self.pk}: {self.name}"

    def number_of_enemies(self) -> int:
        if hasattr(self, "enemies_count"):
            return self.enemies_count
        return self.l.count()

    def get_related_levels(self) -> list:
        """для админки, чтобы показать краткую информацию"""
        return [(level.id, level.name) for level in self.related_levels.all()]


class LevelRelatedLevels(models.Model):
    class Meta:
        managed = False
        db_table = "level_related_levels"
        verbose_name = "Уровень"
        verbose_name_plural = "Уровни"
        ordering = ("-pk",)
        unique_together = (
            "level",
            "related_level",
        )

    level = models.ForeignKey(
        Level,
        related_name="children",
        on_delete=models.PROTECT,
    )
    related_level = models.ForeignKey(
        Level,
        related_name="l2",
        on_delete=models.PROTECT,
    )
    line = models.CharField(
        verbose_name="Линия соединения в дереве",
        choices=LINE_CHOICES,
        blank=True,
        null=True,
        max_length=16,
    )


class LevelEnemy(models.Model):
    class Meta:
        managed = False
        db_table = "level_enemies"
        verbose_name = "Враг уровня"
        verbose_name_plural = "Враги уровня"

    level = models.ForeignKey(
        Level,
        related_name="l",
        on_delete=models.PROTECT,
    )
    enemy = models.ForeignKey(
        Enemy,
        related_name="l",
        on_delete=models.PROTECT,
    )


class SeasonRelatedSeasons(models.Model):
    class Meta:
        managed = False
        db_table = "season_related_seasons"
        verbose_name = "Связь сезонов"
        verbose_name_plural = "Связи сезонов"
        unique_together = (("season", "related_season"),)

    season = models.ForeignKey(Season, related_name="children", on_delete=models.PROTECT)
    related_season = models.ForeignKey(Season, related_name="incoming_links", on_delete=models.PROTECT)
    line = models.CharField(max_length=16, choices=LINE_CHOICES, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.season_id} → {self.related_season_id}"
