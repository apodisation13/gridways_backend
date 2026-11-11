from enum import StrEnum
from typing import Annotated, Literal

from lib.utils.schemas import Base
from lib.utils.schemas.game import ResourceType
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
    RESOURCE_TRANSFORMED = "resource.transformed"

    RESOURCES_CHECKED = "resources.checked"


class ResourcesCheckedData(Base):
    # Клиент передаёт только сигнал, баланс берём из БД.
    model_config = ConfigDict(extra="forbid")


class ResourcesCheckedEvent(Base):
    type: Literal[AchievementEventType.RESOURCES_CHECKED]
    data: ResourcesCheckedData


class ResourceAmountsData(Base):
    # Фактически потраченные или полученные ресурсы, всегда положительными числами.
    resources: dict[ResourceType, PositiveAmount]


class ActionPlayedData(Base):
    # Весь снимок карты/лидера, включая вложенные поля и массивы.
    actor: dict[str, JsonValue]


class ActionPlayedEvent(Base):
    type: Literal[AchievementEventType.ACTION_PLAYED]
    data: ActionPlayedData


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
    | ActionPlayedEvent
    | ResourceSpentEvent
    | ResourceGainedEvent
    | ResourceOpenedEvent
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
    field: Annotated[str, Field(pattern=r"^resources\.[a-z_]+$")]


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
    counter: Annotated[CountCounter | SumCounter | CurrentCounter, Field(discriminator="type")]
    filters: dict[str, FilterScalar | FilterCondition] = Field(default_factory=dict)
    rewards: AchievementRewards

    @model_validator(mode="after")
    def validate_current_counter(self) -> "AchievementDefinition":
        # Сигнал проверки баланса не должен становиться обычным count/sum-событием.
        is_current = isinstance(self.counter, CurrentCounter)
        if is_current != (self.event == AchievementEventType.RESOURCES_CHECKED):
            raise ValueError("current counter requires resources.checked event and vice versa")
        if is_current:
            ResourceType(self.counter.field.removeprefix("resources."))
        return self
