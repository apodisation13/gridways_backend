import asyncpg


async def get_user_achievements(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict:
    data = await connection.fetchval(
        "SELECT progress::jsonb FROM user_achievements WHERE id = $1",
        user_id,
    )
    if data is None:
        await connection.execute(
            """
                INSERT INTO user_achievements (id, progress)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """,
            user_id,
            {},
        )
        data = await connection.fetchval(
            "SELECT progress::jsonb FROM user_achievements WHERE id = $1",
            user_id,
        )

    return data
