from sqlalchemy import (
    Integer,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column

from lib.utils.models import BaseModel


class UserResource(BaseModel):
    __tablename__ = "user_resources"

    id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    scraps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1000",
    )
    wood: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1000",
    )
    kegs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="3",
    )
    big_kegs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    chests: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    keys: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="3",
    )
