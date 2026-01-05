from typing import Any

from sqlalchemy.dialects.postgresql import JSONB

from lib.utils.models import BaseModel
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class Faction(BaseModel):
    __tablename__ = "factions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Faction(id={self.id}, name='{self.name}')>"


class Color(BaseModel):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)

    def __repr__(self) -> str:
        return f"<Color(id={self.id}, name='{self.name}')>"


class GameConstants(BaseModel):
    __tablename__ = "game_constants"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default="{}",
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<GameConstant(id={self.id})>"
