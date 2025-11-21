from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from lib.utils.models import BaseModel


class CronTask(BaseModel):
    __tablename__ = "cron_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    schedule: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(server_default="true")
