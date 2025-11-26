from enum import StrEnum


class EventType(StrEnum):
    EVENT_1 = "event_1"
    EVENT_2 = "event_2"


class EventProcessingState(StrEnum):
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
