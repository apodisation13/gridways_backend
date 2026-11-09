import asyncpg

from services.api.app.apps.preferences.schemas import DEFAULT_PREFERENCES, UserPreferencesResponse


async def get_user_preferences(
    connection: asyncpg.Connection,
    user_id: int,
) -> UserPreferencesResponse:
    data = await connection.fetchval(
        "SELECT data::jsonb FROM user_preferences WHERE id = $1",
        user_id,
    )
    if data is None:
        await connection.execute(
            """
                INSERT INTO user_preferences (id, data)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """,
            user_id,
            DEFAULT_PREFERENCES,
        )
        data = await connection.fetchval(
            "SELECT data::jsonb FROM user_preferences WHERE id = $1",
            user_id,
        )

    return UserPreferencesResponse(data=data)
