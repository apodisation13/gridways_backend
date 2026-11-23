from enum import StrEnum
from typing import Annotated, Literal

from lib.utils.schemas import Base
from lib.utils.schemas.game import LeaderboardGameMode, LevelDifficulty, ResourceType, UpgradeSubtype, UpgradeType
from pydantic import ConfigDict, Field, JsonValue, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator
from services.api.app.apps.progress.schemas import UserResources


# Эти модели проверяют JSON до обработки событий. Base запрещает лишние поля по умолчанию.
# strict=True не позволяет подменить целое ID строкой "123" или значением True.
PositiveId = Annotated[int, Field(strict=True, gt=0)]
# Количество может быть целым или дробным, но обязательно положительным и конечным.
PositiveAmount = (
    Annotated[int, Field(strict=True, gt=0)]
    | Annotated[
        float,
        Field(strict=True, gt=0, allow_inf_nan=False),
    ]
)


# Строки из поля type, которые понимает бэкенд.
# Сам тип описывает событие; какие задания оно продвинет, решают filters и counter в конфиге.
class AchievementEventType(StrEnum):
    # событие выигранной игры - содержит режим, сложность, убитых врагов, инфу о колоде
    GAME_WON = "game.won"  # GameWonEvent - описывает эти данные
    GAME_LOST = "game.lost"  # GameLostEvent - описывает данные

    # сыграна вообще любая карта в любой игре в любом режиме
    ACTION_PLAYED = "action.played"  # ActionPlayedEvent - данные

    # сработала пассивка любой карты игрока (в руке, в сбросе, в колоде, лидера, разовая в начале, от игры карты)
    PASSIVE_TRIGGERED = "passive.triggered"  # PassiveTriggeredEvent - данные

    # убили врага или лидера врагов
    ENEMY_KILLED = "enemy.killed"  # EnemyKilledEvent - там враг (целиком) и режим игры
    ENEMY_SHIELD_REMOVED = "enemy.shield_removed"
    ENEMY_ARMOR_REMOVED = "enemy.armor_removed"

    # события с колодами - создание, сохранение, удаление
    DECK_CREATED = "deck.created"
    DECK_SAVED = "deck.saved"
    DECK_DELETED = "deck.deleted"
    # а это проверка чтобы выполнить контракты на то, сколько колод у пользователя сейчас
    DECKS_CHECKED = "decks.checked"

    # проверка текущего значения ресурсов и прокачек
    RESOURCES_CHECKED = "resources.checked"
    UPGRADES_CHECKED = "upgrades.checked"

    # any resource spent or gained
    RESOURCE_SPENT = "resource.spent"
    RESOURCE_GAINED = "resource.gained"
    # any resource opened - keys, kegs/big kegs, chests
    RESOURCE_OPENED = "resource.opened"
    INVENTORY_USED = "inventory.used"
    INVENTORY_RESTORED = "inventory.restored"
    ARENA_UPGRADE_PURCHASED = "arena.upgrade.purchased"
    ARENA_LEVEL_REACHED = "arena.level.reached"
    RESOURCE_TRANSFORMED = "resource.transformed"

    UPGRADE_PURCHASED = "upgrade.purchased"

    # крафт или милл карты или лидера
    ACTOR_TRANSFORMED = "actor.transformed"


class ResourcesCheckedData(Base):
    # Клиент передаёт только сигнал, баланс берём из БД.
    model_config = ConfigDict(extra="forbid")


class ResourcesCheckedEvent(Base):
    type: Literal[AchievementEventType.RESOURCES_CHECKED]
    data: ResourcesCheckedData


class UpgradesCheckedEvent(Base):
    type: Literal[AchievementEventType.UPGRADES_CHECKED]
    # Как и с ресурсами, от клиента приходит пустой сигнал. Данные берёт сервис из БД.
    data: ResourcesCheckedData


class DecksCheckedEvent(Base):
    type: Literal[AchievementEventType.DECKS_CHECKED]
    data: ResourcesCheckedData


# В dict[str, JsonValue] допускается вложенный JSON: словари, массивы, числа и т.д.
# Это позволяет фильтровать новые поля снимка без отдельной Pydantic-модели на каждое поле карты.
class DeckComposition(Base):
    # Структура состава известна; внутри карт/лидера сохраняем все игровые поля.
    cards: list[dict[str, JsonValue]]
    leader: dict[str, JsonValue]


class UserDeckSnapshot(Base):
    # Создание/редактирование присылает эти поля, удаление — ещё ID и поля колоды.
    model_config = ConfigDict(extra="allow")

    cards: list[dict[str, JsonValue]]
    leader: dict[str, JsonValue]
    name: StrictStr
    health: StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)]


class DeckEventData(Base):
    deck: UserDeckSnapshot


class DeckCreatedEvent(Base):
    type: Literal[AchievementEventType.DECK_CREATED]
    data: DeckEventData


class DeckSavedEvent(Base):
    type: Literal[AchievementEventType.DECK_SAVED]
    data: DeckEventData


class DeckDeletedEvent(Base):
    type: Literal[AchievementEventType.DECK_DELETED]
    data: DeckEventData


# Здесь level — номер купленной ступени, value — ее эффект, maxed — достигнут ли максимум.
# В отличие от upgrades.checked, это данные конкретного события, переданные клиентом.
class UpgradePurchasedData(Base):
    upgrade_type: UpgradeType
    upgrade_subtype: UpgradeSubtype
    level: PositiveId
    value: StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)] | StrictBool
    maxed: StrictBool


class UpgradePurchasedEvent(Base):
    type: Literal[AchievementEventType.UPGRADE_PURCHASED]
    data: UpgradePurchasedData


# Например, resources={"money": 100, "scraps": 5}; sum может читать путь resources.money.
# Это сообщение о расходе/доходе, сам баланс при обработке такого события не изменяется.
class ResourceAmountsData(Base):
    # Фактически потраченные или полученные ресурсы, всегда положительными числами.
    resources: dict[ResourceType, PositiveAmount]
    # Необязательная причина операции для фильтров контрактов.
    subtype: str | None = None
    # Название использованного предмета для unique по item.
    item: ResourceType | None = None


class GameLostData(Base):
    # Единственное поле поражения: режим боя для фильтров сброса серии.
    mode: LeaderboardGameMode | Literal["normal"]


class GameLostEvent(Base):
    type: Literal[AchievementEventType.GAME_LOST]
    data: GameLostData


class EnemyGraveSummary(Base):
    # Текущий состав кладбища при победе, без лидера и истории убийств.
    total: Annotated[int, Field(strict=True, ge=0)]
    bronze: Annotated[int, Field(strict=True, ge=0)]
    silver: Annotated[int, Field(strict=True, ge=0)]
    gold: Annotated[int, Field(strict=True, ge=0)]


class AchievementBattleStats(Base):
    # Статистика одного боя. Защита бронёй/неуязвимостью не является уроном HP.
    leader_uses: int = Field(strict=True, ge=0)
    damage_taken: int | float = Field(ge=0, allow_inf_nan=False)
    enemy_passives_in_field: int = Field(strict=True, ge=0)


class GameWonData(Base):
    mode: LeaderboardGameMode | Literal["normal"]
    difficulty: LevelDifficulty
    starting_deck: DeckComposition
    battleStats: AchievementBattleStats
    enemy_grave: EnemyGraveSummary


class GameWonEvent(Base):
    type: Literal[AchievementEventType.GAME_WON]
    data: GameWonData


class ActionPlayedData(Base):
    actor: dict[str, JsonValue]  # Весь снимок карты/лидера, включая вложенные поля и массивы.
    mode: LeaderboardGameMode | Literal["normal"]  # режим игры


class PassiveTriggeredData(Base):
    actor: dict[str, JsonValue]  # Полный снимок владельца пассивки до эффекта.
    mode: LeaderboardGameMode | Literal["normal"]
    # Зона обычной пассивки либо отдельная ситуация запуска.
    location: Literal[
        "hand",
        "deck",
        "grave",
        "passive_once",
        "passive_upon_playing_a_card",
        "leader_passive_upon_playing_a_card",
    ]


class PassiveTriggeredEvent(Base):
    type: Literal[AchievementEventType.PASSIVE_TRIGGERED]
    data: PassiveTriggeredData


class EnemyEventData(Base):
    # Полный снимок до удаления или снятия защиты, для общих фильтров.
    enemy: dict[str, JsonValue]
    mode: LeaderboardGameMode | Literal["normal"]


class EnemyKilledEvent(Base):
    type: Literal[AchievementEventType.ENEMY_KILLED]
    data: EnemyEventData


class EnemyShieldRemovedData(Base):
    enemy: dict[str, JsonValue]  # Полный снимок врага до снятия щита.
    mode: LeaderboardGameMode | Literal["normal"]


class EnemyShieldRemovedEvent(Base):
    type: Literal[AchievementEventType.ENEMY_SHIELD_REMOVED]
    data: EnemyShieldRemovedData


class EnemyArmorRemovedData(Base):
    enemy: dict[str, JsonValue]  # Полный снимок врага до снятия брони.
    mode: LeaderboardGameMode | Literal["normal"]
    amount: PositiveAmount  # Фактически снятое количество, не запрошенный урон.


class EnemyArmorRemovedEvent(Base):
    type: Literal[AchievementEventType.ENEMY_ARMOR_REMOVED]
    data: EnemyArmorRemovedData


class ActionPlayedEvent(Base):
    type: Literal[AchievementEventType.ACTION_PLAYED]
    data: ActionPlayedData


# Для крафта/разбора доступны и исходный рецепт, и фактические расходы/доходы.
# В recipe числа могут быть отрицательными, а spent/gained содержат положительные величины.
class ActorTransformedData(Base):
    action: Literal["craft", "mill"]
    actor: dict[str, JsonValue]
    # Рецепт сохраняем со знаками, как пришёл с фронта.
    recipe: dict[ResourceType, StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)]]
    spent: dict[ResourceType, PositiveAmount]
    gained: dict[ResourceType, PositiveAmount]


class ActorTransformedEvent(Base):
    type: Literal[AchievementEventType.ACTOR_TRANSFORMED]
    data: ActorTransformedData


class ResourceSpentEvent(Base):
    type: Literal[AchievementEventType.RESOURCE_SPENT]
    data: ResourceAmountsData


class ResourceGainedEvent(Base):
    type: Literal[AchievementEventType.RESOURCE_GAINED]
    data: ResourceAmountsData


class ResourceOpenedData(Base):
    resource: ResourceType


class ResourceOpenedEvent(Base):
    type: Literal[AchievementEventType.RESOURCE_OPENED]
    data: ResourceOpenedData


class InventoryUsedData(Base):
    mode: LeaderboardGameMode | Literal["normal"]
    item: ResourceType
    # Только фактически измеренные результаты. Пустой словарь допустим.
    result: dict[str, Annotated[int, Field(strict=True, ge=0)]]


class InventoryRestoredData(Base):
    mode: LeaderboardGameMode | Literal["normal"]
    item: ResourceType


class InventoryRestoredEvent(Base):
    type: Literal[AchievementEventType.INVENTORY_RESTORED]
    data: InventoryRestoredData


class ArenaUpgradePurchasedData(Base):
    upgrade_subtype: UpgradeSubtype
    level: PositiveId


class ArenaUpgradePurchasedEvent(Base):
    type: Literal[AchievementEventType.ARENA_UPGRADE_PURCHASED]
    data: ArenaUpgradePurchasedData


class ArenaLevelReachedData(Base):
    level: PositiveId


class ArenaLevelReachedEvent(Base):
    type: Literal[AchievementEventType.ARENA_LEVEL_REACHED]
    data: ArenaLevelReachedData


class InventoryUsedEvent(Base):
    type: Literal[AchievementEventType.INVENTORY_USED]
    data: InventoryUsedData


class ResourceTransformedData(Base):
    action: Literal["buy", "sell", "craft", "mill"]
    resource: ResourceType
    # Количество предметов/единиц ресурса, а не число нажатий: quantity * step.
    amount: PositiveAmount
    # Стоимость и фактический доход этого обмена; без нулевых значений.
    spent: dict[ResourceType, PositiveAmount]
    gained: dict[ResourceType, PositiveAmount]


class ResourceTransformedEvent(Base):
    type: Literal[AchievementEventType.RESOURCE_TRANSFORMED]
    data: ResourceTransformedData


# A | B | C означает «одна из моделей событий».
# Field(discriminator="type") говорит Pydantic выбрать модель по значению type.
# Например, action.played → ActionPlayedEvent → проверяем data по ActionPlayedData.
# Annotated связывает сам тип с этой дополнительной настройкой выбора.
AchievementEvent = Annotated[
    ResourcesCheckedEvent
    | DecksCheckedEvent
    | DeckSavedEvent
    | DeckCreatedEvent
    | DeckDeletedEvent
    | UpgradesCheckedEvent
    | UpgradePurchasedEvent
    | GameWonEvent
    | GameLostEvent
    | ActionPlayedEvent
    | EnemyKilledEvent
    | EnemyShieldRemovedEvent
    | EnemyArmorRemovedEvent
    | PassiveTriggeredEvent
    | ActorTransformedEvent
    | ResourceSpentEvent
    | ResourceGainedEvent
    | ResourceOpenedEvent
    | InventoryRestoredEvent
    | ArenaUpgradePurchasedEvent
    | ArenaLevelReachedEvent
    | InventoryUsedEvent
    | ResourceTransformedEvent,
    Field(discriminator="type"),
]


# Пачка проверяется целиком. Пустой список допустим: он не продвинет задания.
class AchievementEventsRequest(Base):
    events: list[AchievementEvent]


# Награды задаются только целыми неотрицательными ресурсами, как колонки баланса в БД.
class AchievementRewards(Base):
    resources: dict[ResourceType, Annotated[int, Field(strict=True, ge=0)]]


# Одна награда за одно выполненное задание. Сейчас поддерживаются только постоянные задания.
# period всегда null: ежедневные и еженедельные периоды пока не обрабатываем.
class GrantedAchievementReward(Base):
    achievement_id: str
    period_type: Literal["permanent"]
    period: None
    rewards: AchievementRewards


# user_achievements — весь прогресс после обработки, granted_rewards — только новые награды.
# user_resources — весь итоговый баланс, если были награды, иначе null.
# Все три ключа обязательны; id событий и подтверждения отдельных событий не используются.
class AchievementEventsResponse(Base):
    user_achievements: dict
    granted_rewards: list[GrantedAchievementReward]
    user_resources: UserResources | None


# count: +1 за каждое событие, прошедшее фильтры.
class CountCounter(Base):
    type: Literal["count"]


# current: записываем текущее значение поля из серверного снимка вместо накопления.
# Например, resources.money=500 → value=500 (но не выше target).
class CurrentCounter(Base):
    type: Literal["current"]
    field: Annotated[str, Field(min_length=1)]


# unique: храним увиденные значения field в state.seen, повторное значение не прибавляет прогресс.
class UniqueCounter(Base):
    type: Literal["unique"]
    field: Annotated[str, Field(min_length=1)]


# sum: прибавляем число из поля события. Например, gained.money или enemy.data.hp.
class SumCounter(Base):
    type: Literal["sum"]
    field: Annotated[str, Field(min_length=1)]


# Новые поля карты не требуют новых моделей. Типизируем только язык условий.
# Короткий фильтр — скаляр: {"actor.color": "Bronze"}.
# Расширенный — условие: {"actor.data.damage": {"type": "gte", "value": 10}}.
# Strict-типы нужны, чтобы True, 1 и "1" не превращались друг в друга при проверке конфига.
FilterScalar = StrictStr | StrictBool | StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)] | None
FilterNumber = StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)]


class EqualityFilter(Base):
    type: Literal["eq", "ne"]
    value: FilterScalar


class ComparisonFilter(Base):
    type: Literal["gt", "gte", "lt", "lte"]
    value: FilterNumber


class InFilter(Base):
    type: Literal["in"]
    value: list[FilterScalar]


class ExistsFilter(Base):
    type: Literal["exists"]
    value: StrictBool


# Здесь type выбирает уже оператор фильтра, а не вид игрового события.
FilterCondition = Annotated[
    EqualityFilter | ComparisonFilter | InFilter | ExistsFilter,
    Field(discriminator="type"),
]


# Событие и условия, которые обрывают текущую серию. Таких правил может быть несколько.
class StreakReset(Base):
    event: AchievementEventType
    filters: dict[str, FilterScalar | FilterCondition] = Field(default_factory=dict)


# streak: length — длина одной серии, а target самого задания — количество полных серий.
# reset обязателен и непустой: описывает, когда незавершенная серия сбрасывается.
class StreakCounter(Base):
    type: Literal["streak"]
    length: Annotated[int, Field(strict=True, gt=0)]
    reset: Annotated[list[StreakReset], Field(min_length=1)]


class AchievementDefinition(Base):
    # title, ordering и другие поля интерфейса оставляем в конфиге, но не берем в расчетную модель.
    model_config = ConfigDict(extra="ignore")

    id: str
    event: AchievementEventType
    target: PositiveAmount
    counter: Annotated[
        CountCounter | SumCounter | CurrentCounter | UniqueCounter | StreakCounter,
        Field(discriminator="type"),
    ]
    filters: dict[str, FilterScalar | FilterCondition] = Field(default_factory=dict)
    rewards: AchievementRewards
    # Метаданные интерфейса; прогресс по-прежнему хранится по id задания.
    group: Annotated[StrictStr, Field(min_length=1, pattern=r"\S")] | None = None

    # Эта проверка запускается после разбора полей модели. Она проверяет сочетание event + counter,
    # потому что по отдельности оба поля могут быть корректными, а вместе — бессмысленными.
    @model_validator(mode="after")
    def validate_current_counter(self) -> "AchievementDefinition":
        # Проверки текущего состояния используют current, а не накопление событий.
        is_current = isinstance(self.counter, CurrentCounter)
        checked_events = {
            AchievementEventType.RESOURCES_CHECKED,
            AchievementEventType.UPGRADES_CHECKED,
            AchievementEventType.DECKS_CHECKED,
        }
        # Разрешаем только пары: checked-событие + current ИЛИ обычное событие + другой счетчик.
        if is_current != (self.event in checked_events):
            raise ValueError("current counter requires a state-check event and vice versa")
        # Число разных предметов и полных серий не может иметь дробную цель вроде 2.5.
        if isinstance(self.counter, (UniqueCounter, StreakCounter)) and self.target != int(self.target):
            raise ValueError("unique/streak counter requires an integer target")
        if is_current:
            # У серверных снимков заранее известная структура. Проверяем путь еще при чтении конфига.
            parts = self.counter.field.split(".")
            if self.event == AchievementEventType.RESOURCES_CHECKED:
                if len(parts) != 2 or parts[0] != "resources":
                    raise ValueError("resource current field must be resources.<resource>")
                ResourceType(parts[1])
            elif self.event == AchievementEventType.DECKS_CHECKED:
                if self.counter.field != "decks.count":
                    raise ValueError("deck current field must be decks.count")
            # Прокачка: upgrades.<тип>.<подтип>.level либо .value.
            elif len(parts) == 4 and parts[0] == "upgrades" and parts[3] in {"level", "value"}:
                UpgradeType(parts[1])
                UpgradeSubtype(parts[2])
            # Сводка: summary.all.maxed_count, summary.non_settings.all_maxed и т.д.
            elif (
                len(parts) == 3
                and parts[0] == "summary"
                and parts[2]
                in {
                    "total_count",
                    "maxed_count",
                    "all_maxed",
                }
            ):
                if parts[1] not in {"all", "non_settings"}:
                    UpgradeType(parts[1])
            else:
                raise ValueError("invalid upgrade current field")
        return self
