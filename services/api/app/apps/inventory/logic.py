import asyncpg


async def get_user_inventory(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict:
    data = await connection.fetchval(
        "SELECT data::jsonb FROM user_inventory WHERE id = $1",
        user_id,
    )
    if data is None:
        await connection.execute(
            """
                INSERT INTO user_inventory (id, data)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """,
            user_id,
            {"slots": []},
        )
        data = await connection.fetchval(
            "SELECT data::jsonb FROM user_inventory WHERE id = $1",
            user_id,
        )

    return data
