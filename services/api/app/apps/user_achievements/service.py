from lib.utils.db.pool import Database
from services.api.app.apps.game_data.logic import game_const as game_const_logic
from services.api.app.apps.progress import logic as progress_logic
from services.api.app.apps.upgrades import logic as upgrades_logic
from services.api.app.apps.user_achievements.logic.events import apply_events, get_permanent_definitions
from services.api.app.apps.user_achievements.logic.upgrades import build_upgrade_snapshot
from services.api.app.apps.user_achievements.schemas import (
    AchievementDefinition,
    AchievementEvent,
    AchievementEventType,
    AchievementEventsResponse,
)
from services.api.app.config import Config


class AchievementsService:
    def __init__(
        self,
        db_pool: Database,
        config: Config,
    ):
        self.db_pool = db_pool
        self.config = config

    async def process_events(
        self,
        user_id: int,
        events: list[AchievementEvent],
    ) -> AchievementEventsResponse:
        async with self.db_pool.transaction() as connection:
            # 1. Берем конфиги, нам нужны будут оттуда achievements
            game_constants: dict = await game_const_logic.get_game_constants(connection=connection)
            categories: dict = game_constants.get("achievements", {}).get("permanent", {}).get("categories", {})

            # 2. Определеляем сами задания - плоским списком?
            definitions: list[AchievementDefinition] = get_permanent_definitions(categories)

            # 3. Блокируем строку на случай двух запросов одновременно
            progress: dict = await connection.fetchval(
                """SELECT progress FROM user_achievements WHERE id = $1 FOR UPDATE""",
                user_id,
            )

            # 4. Применяем все события
            upgrades = None
            if any(event.type == AchievementEventType.UPGRADES_CHECKED for event in events):
                # Как при покупке, сначала блокируем прокачки, затем ресурсы.
                # Подтверждение опирается на БД, а не на переданный фронтом снимок.
                user_upgrades = await connection.fetchval(
                    "SELECT data::jsonb FROM user_upgrades WHERE id = $1 FOR UPDATE", user_id,
                )
                if user_upgrades is None:
                    user_upgrades = await upgrades_logic.get_user_upgrades(connection, user_id)
                upgrades = build_upgrade_snapshot(game_constants["upgrades"], user_upgrades)
            resources = None
            if any(event.type == AchievementEventType.RESOURCES_CHECKED for event in events):
                # Баланс стабилен до конца проверки и выдачи наград в этой транзакции.
                await connection.fetchval("SELECT id FROM user_resources WHERE id = $1 FOR UPDATE", user_id)
                balance = await progress_logic.get_user_resources(user_id, connection)
                resources = balance.model_dump(mode="json")
            rewards = apply_events(progress, events, definitions, resources, upgrades)

            # 5. Если награды нужно - начисляем их тут.
            user_resources = None
            if rewards:
                # 6. Блокируем строку на случай двух запросов одновременно
                await connection.fetchval("""SELECT id FROM user_resources WHERE id = $1 FOR UPDATE""", user_id)

                # 7. Начисляем ресурсы, и тут надо брать еще уровни апгрейдов если что
                await upgrades_logic.get_user_upgrades(connection, user_id)
                for reward in rewards:
                    before = await progress_logic.get_user_resources(user_id, connection)
                    user_resources = await progress_logic.change_resources(
                        connection=connection,
                        user_id=user_id,
                        resources_to_change=reward.rewards.resources,
                        scenario=f"Achievement reward: {reward.achievement_id}",
                    )
                    reward.rewards.resources = {
                        resource: getattr(user_resources, resource) - getattr(before, resource)
                        for resource in reward.rewards.resources
                    }

            # И вот только тут меняем прогресс пользователя
            await connection.execute(
                """
                    UPDATE
                        user_achievements
                    SET
                        progress = $2::jsonb,
                        updated_at = NOW()
                    WHERE
                        id = $1
                """,
                user_id,
                progress,
            )

            response = AchievementEventsResponse(
                user_achievements=progress,
                granted_rewards=rewards,
                user_resources=user_resources,
            )

        return response
