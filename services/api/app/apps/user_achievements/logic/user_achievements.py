import asyncpg


async def get_user_achievements(
    connection: asyncpg.Connection,
    user_id: int,
) -> dict:
    # 1. Возвращаем весь JSON-прогресс пользователя: permanent, daily, weekly, если они уже есть.
    # Здесь обычное чтение без FOR UPDATE — для выдачи наград сервис блокирует строку отдельно.
    data = await connection.fetchval(
        "SELECT progress::jsonb FROM user_achievements WHERE id = $1",
        user_id,
    )
    # 2. None означает отсутствие записи. Существующий пустой {} повторно создавать не нужно.
    if data is None:
        # Два первых запроса могут одновременно не найти запись.
        # ON CONFLICT позволяет второму не упасть и не перезаписать уже созданный прогресс.
        await connection.execute(
            """
                INSERT INTO user_achievements (id, progress)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
            """,
            user_id,
            {},
        )
        # 3. Читаем именно сохраненную запись: ее могли создать мы или параллельный запрос.
        data = await connection.fetchval(
            "SELECT progress::jsonb FROM user_achievements WHERE id = $1",
            user_id,
        )

    return data
