from datetime import UTC, datetime

from services.api.app.apps.user_achievements.logic.filters import get_field, is_number, matches_filters
from services.api.app.apps.user_achievements.schemas import (
    AchievementDefinition,
    AchievementEvent,
    GrantedAchievementReward,
    SumCounter,
)


def get_permanent_definitions(
    categories: dict,
) -> list[AchievementDefinition]:
    definitions = []
    seen = set()

    # 1. Перебираем категории из конфига: cards, resources и остальные
    for category in categories.values():
        # 2. В каждой категории берем задания: key — ключ задания, data — его конфиг
        for key, data in category.get("achievements", {}).items():
            # 3. Проверяем конфиг через Pydantic и получаем модель задания
            definition = AchievementDefinition.model_validate(data)

            # 4. id внутри задания должен совпадать с ключом в словаре
            # И одно и то же id не должно встречаться в разных категориях — их запоминаем в seen
            if definition.id != key or key in seen:
                raise ValueError(f"Invalid or duplicate achievement ID: {key}")

            # Запоминаем id и добавляем задание в список без категорий.
            seen.add(key)
            definitions.append(definition)

    return definitions


def apply_events(
    progress: dict,
    events: list[AchievementEvent],
    definitions: list[AchievementDefinition],
) -> list[GrantedAchievementReward]:
    rewards = []
    # Одно время для всех заданий, которые выполнились в этой пачке событий
    timestamp = datetime.now(UTC).isoformat()

    # 1. Начинаем перебирать список пришедших с фронта событий
    for event in events:
        # 2. Превращаем data из Pydantic-модели в обычный словарь
        # actor остаётся полным снимком, не привязанным к заранее перечисленным полям.
        data = event.data.model_dump(mode="json", by_alias=True)

        # 3. Перебираем ВЕСЬ плоский список ВСЕХ заданий
        for definition in definitions:
            # 4. Если задание ждет другое событие — пропускаем его
            if definition.event != event.type:
                continue

            # Пути и операторы одинаковы с фронтом: actor.color, actor.data.damage и т.д.
            filters = definition.model_dump(mode="json")["filters"]
            if not matches_filters(data, filters):
                continue

            # 6. Берем раздел permanent из прогресса юзера
            # setdefault возвращает существующее значение, а если ключа нет — добавляет его с {}
            tasks = progress.setdefault("permanent", {})

            # 7. Так же берем прогресс конкретного задания, а если его нет — создаем нулевой
            # tasks и state ссылаются на вложенные словари progress: меняя state, меняем и progress
            state = tasks.setdefault(
                definition.id,
                {"value": 0, "completed_at": None, "reward_granted_at": None},
            )

            # 8. Если награда за это задание уже выдана — больше его не считаем
            if state.get("reward_granted_at") is not None:
                continue

            # 9. sum может брать любое числовое поле, в том числе вложенное.
            # Для count просто прибавляем 1 за одно подходящее событие
            increment = get_field(data, definition.counter.field) if isinstance(definition.counter, SumCounter) else 1
            if not is_number(increment) or increment <= 0:
                continue

            # 10. Увеличиваем прогресс, но не выше цели: для задания на 10 карт максимум будет 10
            state["value"] = min(definition.target, state["value"] + increment)

            # 11. Если цель еще не достигнута — счетчик уже увеличили, а награду пока не выдаем
            if state["value"] < definition.target:
                continue

            # 12. Цель достигнута! Сохраняем время выполнения (если его еще нет) и отметку о награде
            # Пока это только словарь в памяти. Сервис ниже начислит ресурсы и сохранит progress
            # в одной транзакции: если начисление упадет, эти отметки в БД тоже не сохранятся
            state["completed_at"] = state.get("completed_at") or timestamp
            state["reward_granted_at"] = timestamp

            # 13. Добавляем награду в список для начисления в сервисе
            # period=None, потому что постоянное задание не привязано к дню или неделе
            # Копируем rewards, чтобы дальнейшие изменения награды не меняли сам конфиг задания
            rewards.append(
                GrantedAchievementReward(
                    achievement_id=definition.id,
                    period_type="permanent",
                    period=None,
                    rewards=definition.rewards.model_copy(deep=True),
                ),
            )

    # Прогресс уже изменили в переданном словаре, отдельно возвращаем только новые награды
    return rewards
