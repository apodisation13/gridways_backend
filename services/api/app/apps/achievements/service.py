import logging

from lib.utils.db.pool import Database
from services.api.app.config import Config


logger = logging.getLogger(__name__)


class AchievementsService:
    def __init__(
        self,
        db_pool: Database,
        config: Config,
    ):
        self.db_pool = db_pool
        self.config = config

    async def get_achievements(self) -> dict:
        """Заглушка до реализации системы заданий."""
        return {}
