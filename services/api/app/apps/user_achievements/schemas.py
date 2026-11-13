from enum import StrEnum
from typing import Annotated, Literal

from lib.utils.schemas import Base
from lib.utils.schemas.game import ResourceType, UpgradeSubtype, UpgradeType
from pydantic import ConfigDict, Field, JsonValue, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator
from services.api.app.apps.progress.schemas import UserResources


PositiveId = Annotated[int, Field(strict=True, gt=0)]
PositiveAmount = (
    Annotated[int, Field(strict=True, gt=0)]
    | Annotated[
        float,
        Field(strict=True, gt=0, allow_inf_nan=False),
    ]
)


class AchievementEventType(StrEnum):
    # сard or leader played
    ACTION_PLAYED = "action.played"
    # any resource spent or gained
    RESOURCE_SPENT = "resource.spent"
    RESOURCE_GAINED = "resource.gained"
    # any resource opened - keys, kegs/big kegs, chests
    RESOURCE_OPENED = "resource.opened"
    INVENTORY_USED = "inventory.used"
    DECK_CREATED = "deck.created"
    DECK_DELETED = "deck.deleted"
    DECKS_CHECKED = "decks.checked"
    RESOURCE_TRANSFORMED = "resource.transformed"

    RESOURCES_CHECKED = "resources.checked"
    UPGRADES_CHECKED = "upgrades.checked"
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


class DeckEventData(Base):
    # Снимок состава с полным лидером, для общих фильтров по вложенным полям.
    deck: dict[str, JsonValue]


class DeckCreatedEvent(Base):
    type: Literal[AchievementEventType.DECK_CREATED]
    data: DeckEventData


class DeckDeletedEvent(Base):
    type: Literal[AchievementEventType.DECK_DELETED]
    data: DeckEventData


class UpgradePurchasedData(Base):
    upgrade_type: UpgradeType
    upgrade_subtype: UpgradeSubtype
    level: PositiveId
    value: StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)] | StrictBool
    maxed: StrictBool


class UpgradePurchasedEvent(Base):
    type: Literal[AchievementEventType.UPGRADE_PURCHASED]
    data: UpgradePurchasedData


class ResourceAmountsData(Base):
    # Фактически потраченные или полученные ресурсы, всегда положительными числами.
    resources: dict[ResourceType, PositiveAmount]
    # Необязательная причина операции для фильтров контрактов.
    subtype: str | None = None
    # Название использованного предмета для unique по item.
    item: ResourceType | None = None


class ActionPlayedData(Base):
    # Весь снимок карты/лидера, включая вложенные поля и массивы.
    actor: dict[str, JsonValue]


class ActionPlayedEvent(Base):
    type: Literal[AchievementEventType.ACTION_PLAYED]
    data: ActionPlayedData


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


class InventoryUseResult(Base):
    # Реально добавленные карты, а не значение прокачки или число попыток.
    cards_drawn: Annotated[int, Field(strict=True, ge=0)]


class InventoryUsedData(Base):
    item: ResourceType
    result: InventoryUseResult


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


AchievementEvent = Annotated[
    ResourcesCheckedEvent
    | DecksCheckedEvent
    | DeckCreatedEvent
    | DeckDeletedEvent
    | UpgradesCheckedEvent
    | UpgradePurchasedEvent
    | ActionPlayedEvent
    | ActorTransformedEvent
    | ResourceSpentEvent
    | ResourceGainedEvent
    | ResourceOpenedEvent
    | InventoryUsedEvent
    | ResourceTransformedEvent,
    Field(discriminator="type"),
]


class AchievementEventsRequest(Base):
    events: list[AchievementEvent]


class AchievementRewards(Base):
    resources: dict[ResourceType, Annotated[int, Field(strict=True, ge=0)]]


class GrantedAchievementReward(Base):
    achievement_id: str
    period_type: Literal["permanent"]
    period: None
    rewards: AchievementRewards


class AchievementEventsResponse(Base):
    user_achievements: dict
    granted_rewards: list[GrantedAchievementReward]
    user_resources: UserResources | None


class CountCounter(Base):
    type: Literal["count"]


class CurrentCounter(Base):
    type: Literal["current"]
    field: Annotated[str, Field(min_length=1)]


class UniqueCounter(Base):
    type: Literal["unique"]
    field: Annotated[str, Field(min_length=1)]


class SumCounter(Base):
    type: Literal["sum"]
    field: Annotated[str, Field(min_length=1)]


# Новые поля карты не требуют новых моделей. Типизируем только язык условий.
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


FilterCondition = Annotated[
    EqualityFilter | ComparisonFilter | InFilter | ExistsFilter,
    Field(discriminator="type"),
]


class AchievementDefinition(Base):
    model_config = ConfigDict(extra="ignore")

    id: str
    event: AchievementEventType
    target: PositiveAmount
    counter: Annotated[CountCounter | SumCounter | CurrentCounter | UniqueCounter, Field(discriminator="type")]
    filters: dict[str, FilterScalar | FilterCondition] = Field(default_factory=dict)
    rewards: AchievementRewards

    @model_validator(mode="after")
    def validate_current_counter(self) -> "AchievementDefinition":
        # Проверки текущего состояния используют current, а не накопление событий.
        is_current = isinstance(self.counter, CurrentCounter)
        checked_events = {
            AchievementEventType.RESOURCES_CHECKED,
            AchievementEventType.UPGRADES_CHECKED,
            AchievementEventType.DECKS_CHECKED,
        }
        if is_current != (self.event in checked_events):
            raise ValueError("current counter requires a state-check event and vice versa")
        if isinstance(self.counter, UniqueCounter) and self.target != int(self.target):
            raise ValueError("unique counter requires an integer target")
        if is_current:
            parts = self.counter.field.split(".")
            if self.event == AchievementEventType.RESOURCES_CHECKED:
                if len(parts) != 2 or parts[0] != "resources":
                    raise ValueError("resource current field must be resources.<resource>")
                ResourceType(parts[1])
            elif self.event == AchievementEventType.DECKS_CHECKED:
                if self.counter.field != "decks.count":
                    raise ValueError("deck current field must be decks.count")
            elif len(parts) == 4 and parts[0] == "upgrades" and parts[3] in {"level", "value"}:
                UpgradeType(parts[1])
                UpgradeSubtype(parts[2])
            elif len(parts) == 3 and parts[0] == "summary" and parts[2] in {
                "total_count", "maxed_count", "all_maxed",
            }:
                if parts[1] not in {"all", "non_settings"}:
                    UpgradeType(parts[1])
            else:
                raise ValueError("invalid upgrade current field")
        return self
