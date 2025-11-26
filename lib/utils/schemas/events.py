from uuid import UUID, uuid4

from pydantic import Field, ConfigDict

from lib.utils.events.event_types import EventType
from lib.utils.schemas import Base


class EventMessage(Base):
    id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    payload: dict

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        json_encoders={
            UUID: str,
            EventType: str,
        },
    )


class ActionConfigData(Base):
    type: str
    conditions: bool | list[dict]
    receiver: str | None
