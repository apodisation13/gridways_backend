import logging

from lib.utils.db.pool import Database
from services.api.app.apps.game_data.logic import cards as cards_logic
from services.api.app.apps.game_data.logic import game_const as game_const_logic
from services.api.app.apps.game_data.schemas import GameDataResponse
from services.api.app.config import Config


logger = logging.getLogger(__name__)


class GameDataService:
    def __init__(
        self,
        db_pool: Database,
        config: Config,
    ):
        self.db_pool = db_pool
        self.config = config

    async def get_game_data(
        self,
        base_url: str,
    ) -> GameDataResponse:
        async with self.db_pool.connection() as connection:
            return GameDataResponse(
                cards=await cards_logic.get_cards(connection, base_url),
                leaders=await cards_logic.get_leaders(connection, base_url),
                enemies=await cards_logic.get_enemies(connection, base_url),
                enemy_leaders=await cards_logic.get_enemy_leaders(connection, base_url),
                seasons=await cards_logic.construct_seasons(connection),
                game_const=await game_const_logic.get_game_constants(connection) or {},
            )
