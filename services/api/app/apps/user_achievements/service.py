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


# Сервис связывает три части: чтение БД → подсчет заданий → начисление и сохранение.
# Сами правила подсчета находятся в logic/events.py, SQL и транзакция — здесь.
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
        # Вся пачка событий — одна транзакция. Если любой шаг упадет, изменения в БД откатятся.
        # В том числе нельзя сохранить отметку о награде, если сами ресурсы не начислились.
        async with self.db_pool.transaction() as connection:
            # 1. Берем конфиги, нам нужны будут оттуда achievements
            game_constants: dict = await game_const_logic.get_game_constants(connection=connection)
            categories: dict = game_constants.get("achievements", {}).get("permanent", {}).get("categories", {})

            # 2. Собираем задания всех категорий в один плоский список и проверяем их конфиги
            # Категории нужны для интерфейса, а счетчики работают непосредственно по id задания.
            definitions: list[AchievementDefinition] = get_permanent_definitions(categories)

            # 3. Подготавливаем серверные данные только для тех проверок, которые есть в пачке.
            # Обычные игровые события используют data с фронта. События *.checked — только сигнал:
            # количество колод, баланс и уровни прокачек для них читаем сами из БД.
            decks = None
            if any(event.type == AchievementEventType.DECKS_CHECKED for event in events):
                # Та же блокировка, что при создании/удалении колод: состав стабилен
                # до выдачи награды. users берём до остальных блокировок.
                await connection.fetchval("SELECT id FROM users WHERE id = $1 FOR UPDATE", user_id)
                count = await connection.fetchval(
                    """SELECT count(*) FROM user_decks WHERE user_id = $1""", user_id,
                )
                # Базовая колода входит в хранение наравне с пользовательскими.
                # В apply_events это станет {"decks": {"count": ...}}, путь счетчика — decks.count.
                decks = {"count": count}

            # 4. Читаем сохраненный прогресс и блокируем именно строку этого пользователя.
            # Второй такой запрос подождет завершения первого и затем увидит его изменения.
            # ВАЖНО: здесь строка должна уже существовать — этот SELECT ее не создает.
            # Создание пустой записи предусмотрено в logic.get_user_achievements при чтении прогресса.
            progress: dict = await connection.fetchval(
                """SELECT progress FROM user_achievements WHERE id = $1 FOR UPDATE""",
                user_id,
            )

            # 5. Если нужно проверить прокачки, собираем их текущие уровни и сводные числа.
            # Снимок будет общим для всех upgrades.checked в этой пачке.
            upgrades = None
            if any(event.type == AchievementEventType.UPGRADES_CHECKED for event in events):
                # Как при покупке, сначала блокируем прокачки, затем ресурсы.
                # Подтверждение опирается на БД, а не на переданный фронтом снимок.
                user_upgrades = await connection.fetchval(
                    """SELECT data::jsonb FROM user_upgrades WHERE id = $1 FOR UPDATE""", user_id,
                )
                upgrades = build_upgrade_snapshot(game_constants["upgrades"], user_upgrades)

            # 6. Для resources.checked берем весь текущий баланс, до наград этой пачки.
            # Отдельный запрос на каждое событие не нужен: все проверки используют этот снимок.
            resources = None
            if any(event.type == AchievementEventType.RESOURCES_CHECKED for event in events):
                # Баланс стабилен до конца проверки и выдачи наград в этой транзакции.
                await connection.fetchval("""SELECT id FROM user_resources WHERE id = $1 FOR UPDATE""", user_id)
                balance = await progress_logic.get_user_resources(user_id, connection)
                resources = balance.model_dump(mode="json")

            # 7. Считаем задания. Функция меняет переданный progress прямо в памяти
            # и возвращает список новых наград. Никаких запросов к БД внутри нее нет.
            # Награды, которые начислим ниже, не создают новые события и здесь повторно не проверяются.
            rewards = apply_events(progress, events, definitions, resources, upgrades, decks)

            # 8. Если задания выполнились — начисляем их награды.
            # Если новых наград нет, user_resources останется None: фронту не нужно заменять баланс.
            user_resources = None
            if rewards:
                # Блокируем баланс до конца транзакции, чтобы считать прибавки по стабильным значениям.
                await connection.fetchval("""SELECT id FROM user_resources WHERE id = $1 FOR UPDATE""", user_id)

                # change_resources учитывает вместимость склада, а она зависит от прокачек.
                for reward in rewards:
                    # Запоминаем баланс ДО конкретной награды. Награды начисляются последовательно.
                    before = await progress_logic.get_user_resources(user_id, connection)
                    user_resources = await progress_logic.change_resources(
                        connection=connection,
                        user_id=user_id,
                        resources_to_change=reward.rewards.resources,
                        scenario=f"Achievement reward: {reward.achievement_id}",
                    )
                    # В ответе показываем реальную прибавку, а не обещанное число из конфига.
                    # Например, награда 10 денег, но до лимита склада осталось 3 — вернем 3.
                    # Если склад полный, прибавка может быть 0, но задание уже отмечено награжденным.
                    reward.rewards.resources = {
                        resource: getattr(user_resources, resource) - getattr(before, resource)
                        for resource in reward.rewards.resources
                    }

            # 9. Сохраняем весь измененный словарь: счетчики, серии, увиденные ID и даты наград.
            # Пока транзакция не завершилась, это сохранение и начисления еще могут откатиться.
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

            # 10. Возвращаем полный прогресс, только новые награды и итоговый баланс после них.
            # Здесь нет дедупликации событий: повторная отправка снова продвинет незавершенные задания.
            response = AchievementEventsResponse(
                user_achievements=progress,
                granted_rewards=rewards,
                user_resources=user_resources,
            )

        return response
