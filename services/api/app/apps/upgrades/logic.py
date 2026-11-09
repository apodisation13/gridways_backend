import asyncpg

from lib.utils.schemas.game import DEFAULT_USER_UPGRADES


async def get_user_upgrades(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict:
    data = await connection.fetchval(
        "SELECT data::jsonb FROM user_upgrades WHERE id = $1",
        user_id,
    )
    if data is None:
        await connection.execute(
            """
                INSERT INTO user_upgrades (id, data)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """,
            user_id,
            DEFAULT_USER_UPGRADES,
        )
        data = await connection.fetchval(
            "SELECT data::jsonb FROM user_upgrades WHERE id = $1",
            user_id,
        )

    return data
