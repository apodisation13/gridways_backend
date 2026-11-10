from enum import StrEnum
from typing import Annotated, Literal

from lib.utils.schemas import Base
from lib.utils.schemas.game import ResourceType
from pydantic import ConfigDict, Field
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
    CARD_PLAYED = "card.played"
    LEADER_PLAYED = "leader.played"
    RESOURCE_SPENT = "resource.spent"


class CardPlayedData(Base):
    card_id: PositiveId = Field(alias="cardId")
    rarity: Literal["bronze", "silver", "gold"]


class LeaderPlayedData(Base):
    leader_id: PositiveId = Field(alias="leaderId")


class ResourceSpentData(Base):
    resource: ResourceType
    amount: PositiveAmount


class CardPlayedEvent(Base):
    type: Literal[AchievementEventType.CARD_PLAYED]
    data: CardPlayedData


class LeaderPlayedEvent(Base):
    type: Literal[AchievementEventType.LEADER_PLAYED]
    data: LeaderPlayedData


class ResourceSpentEvent(Base):
    type: Literal[AchievementEventType.RESOURCE_SPENT]
    data: ResourceSpentData


AchievementEvent = Annotated[
    CardPlayedEvent | LeaderPlayedEvent | ResourceSpentEvent,
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


class SumCounter(Base):
    type: Literal["sum"]
    field: Literal["amount"]


class AchievementDefinition(Base):
    model_config = ConfigDict(extra="ignore")

    id: str
    event: AchievementEventType
    target: PositiveAmount
    counter: Annotated[CountCounter | SumCounter, Field(discriminator="type")]
    filters: dict = Field(default_factory=dict)
    rewards: AchievementRewards
