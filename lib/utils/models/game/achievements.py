from datetime import date
from typing import Any

from lib.utils.models import BaseModel, TimestampMixin
from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class AchievementSet(BaseModel, TimestampMixin):
    __tablename__ = "achievement_sets"
    __table_args__ = (
        UniqueConstraint(
            "period_type",
            "period_start",
            name="uq_achievement_sets_period_type_period_start",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    period_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    task_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )


class UserAchievements(BaseModel, TimestampMixin):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    progress: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default="{}",
        nullable=False,
    )
