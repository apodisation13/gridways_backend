from enum import StrEnum
from typing import Any

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from lib.utils.models import BaseModel


class Event(BaseModel):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(255), unique=True)
    processing: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        server_default="[]",
        nullable=False,
    )
