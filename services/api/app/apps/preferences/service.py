from lib.utils.db.pool import Database
from services.api.app.apps.preferences.schemas import (
    UpdateUserPreferencesRequest,
    UserPreferencesResponse,
)
from services.api.app.config import Config


class PreferencesService:
    def __init__(
        self,
        db_pool: Database,
        config: Config,
    ):
        self.db_pool = db_pool
        self.config = config

    async def update_user_preferences(
        self,
        user_id: int,
        preferences: UpdateUserPreferencesRequest,
    ) -> UserPreferencesResponse:
        async with self.db_pool.connection() as connection:
            preferences: dict = await connection.fetchval(
                """
                    UPDATE user_preferences
                    SET
                        data = $2,
                        updated_at = NOW()
                    WHERE id = $1
                    RETURNING data::jsonb
                """,
                user_id,
                preferences.data,
            )

        return UserPreferencesResponse(data=preferences)
