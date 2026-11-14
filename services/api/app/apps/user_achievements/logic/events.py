from datetime import UTC, datetime

from services.api.app.apps.user_achievements.logic.decks import build_deck_summary
from services.api.app.apps.user_achievements.logic.filters import get_field, is_number, matches_filters
from services.api.app.apps.user_achievements.schemas import (
    AchievementDefinition,
    AchievementEvent,
    AchievementEventType,
    CurrentCounter,
    GrantedAchievementReward,
    SumCounter,
    StreakCounter,
    UniqueCounter,
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


# Эта функция не сохраняет данные в БД. Она изменяет progress, который передал сервис,
# и собирает награды для последующего начисления в той же транзакции.
def apply_events(
    progress: dict,
    events: list[AchievementEvent],
    definitions: list[AchievementDefinition],
    resources: dict | None = None,
    upgrades: dict | None = None,
    decks: dict | None = None,
) -> list[GrantedAchievementReward]:
    rewards = []
    # Одно время для всех заданий, которые выполнились в этой пачке событий
    timestamp = datetime.now(UTC).isoformat()

    # 1. Начинаем перебирать список пришедших с фронта событий
    # Порядок важен для серий: победа → поражение → победа отличается от двух побед подряд.
    for event in events:
        # 2. Превращаем data из Pydantic-модели в обычный словарь
        # actor остаётся полным снимком, не привязанным к заранее перечисленным полям.
        data = event.data.model_dump(mode="json", by_alias=True)
        # Для сохраненной колоды вычисляем сводку по ее картам: сколько бронзовых, все ли нейтральные и т.д.
        # Сами карты здесь пришли с фронта, но готовую summary от него не используем.
        if event.type == AchievementEventType.DECK_SAVED:
            # Всегда пересчитываем из карт: клиентская summary не является источником.
            data["deck"]["summary"] = build_deck_summary(event.data.deck.cards)

        # При победе проверять можно стартовую колоду, а не только ее состояние в конце игры.
        if event.type == AchievementEventType.GAME_WON:
            # Состав уже проверен схемой. Дополняем словарь для фильтров сводкой,
            # не меняя входную Pydantic-модель; повторно проверять тип колоды не нужно.
            data["starting_deck"]["summary"] = build_deck_summary(event.data.starting_deck.cards)

        # Для проверок состояния заменяем пустое data события снимком, который сервис прочитал из БД.
        # В фильтрах и counter.field будут пути resources.money, upgrades.resources.money.level и decks.count.
        if event.type == AchievementEventType.RESOURCES_CHECKED:
            data = {"resources": resources or {}}
        elif event.type == AchievementEventType.UPGRADES_CHECKED:
            data = upgrades or {}
        elif event.type == AchievementEventType.DECKS_CHECKED:
            data = {"decks": decks or {}}

        # 3. Перебираем ВЕСЬ плоский список ВСЕХ заданий
        for definition in definitions:
            # 4. current — проверка текущего состояния, например «иметь 1000 денег».
            # Обычное игровое событие не должно менять такой счетчик.
            is_current = isinstance(definition.counter, CurrentCounter)
            if is_current and event.type not in {
                AchievementEventType.RESOURCES_CHECKED, AchievementEventType.UPGRADES_CHECKED,
                AchievementEventType.DECKS_CHECKED,
            }:
                continue
            counter = definition.counter
            # 5. У серии сначала проверяем условия СБРОСА, даже если это не основное событие задания.
            # Например, задание считает game.won, но сбрасывает текущую серию на game.lost.
            if isinstance(counter, StreakCounter):
                if any(
                    reset.event == event.type and matches_filters(
                        data, reset.model_dump(mode="json")["filters"],
                    )
                    for reset in counter.reset
                ):
                    state = progress.get("permanent", {}).get(definition.id)
                    # Здесь не создаем запись задания, если ее еще нет.
                    # Сбрасываем только streak — текущую незавершенную серию.
                    # value хранит количество уже набранных ПОЛНЫХ серий и остается прежним.
                    # Завершённые контракты не сбрасываем, полные серии сохраняем.
                    if state and not state.get("reward_granted_at") and not state.get("completed_at"):
                        state["streak"] = 0
                    # Событие сброса уже обработали: оно не должно одновременно продолжить эту серию.
                    continue
            # Теперь проверяем основное событие задания: чужой тип пропускаем.
            if definition.event != event.type:
                continue

            # 6. Проверяем ВСЕ фильтры задания. Например, событие action.played подходит по типу,
            # но задание только для Bronze — Silver его не продвинет.
            # model_dump превращает модели условий в словари, которые понимает matches_filters.
            # Пути и операторы одинаковы с фронтом: actor.color, actor.data.damage и т.д.
            filters = definition.model_dump(mode="json")["filters"]
            if not matches_filters(data, filters):
                continue

            # 7. Берем раздел permanent из прогресса юзера
            # setdefault возвращает существующее значение, а если ключа нет — добавляет его с {}
            tasks = progress.setdefault("permanent", {})

            # 8. Так же берем прогресс конкретного задания, а если его нет — создаем нулевой
            # tasks и state ссылаются на вложенные словари progress: меняя state, меняем и progress
            state = tasks.setdefault(
                definition.id,
                {"value": 0, "completed_at": None, "reward_granted_at": None},
            )

            # 9. Если награда за это задание уже выдана — больше его не считаем
            if state.get("reward_granted_at") is not None:
                continue

            # 10. Выбираем способ подсчета, который указан в конфиге задания.
            if isinstance(counter, StreakCounter):
                # streak: считаем события подряд. length — длина одной серии, target — число полных серий.
                # Например, length=3 и target=2: нужны две серии по 3 события, всего 6 без сбросов.
                streak = state.get("streak", 0) + 1
                if streak >= counter.length:
                    state["value"] = min(definition.target, state["value"] + 1)
                    # Серии не перекрываются: после третьей победы следующая начинает новую тройку.
                    streak = 0
                state["streak"] = streak
            elif isinstance(definition.counter, UniqueCounter):
                # unique: считаем разные значения поля, а не количество событий.
                # Например, actor.id: карта 7, карта 7, карта 9 дадут прогресс 2, а не 3.
                item = get_field(data, definition.counter.field)
                # Только названия и числовые ID; bool/null/объекты не являются ID.
                if not isinstance(item, str) and not is_number(item):
                    continue
                # seen сохраняется в progress и попадет в БД, поэтому уникальность работает между запросами.
                seen = state.setdefault("seen", [])
                if item in seen:
                    continue
                seen.append(item)
                state["value"] = min(definition.target, len(seen))
            else:
                # count: +1 за событие. sum: прибавляем число из counter.field, например resources.money.
                # current: тем же способом читаем поле, но дальше ЗАМЕНЯЕМ счетчик текущим значением.
                # get_field понимает вложенные пути: actor.data.damage, starting_deck.summary.cards_count.
                increment = (
                    get_field(data, definition.counter.field)
                    if isinstance(definition.counter, (SumCounter, CurrentCounter))
                    else 1
                )
                # Отсутствующее поле, строка, bool, NaN и бесконечность не увеличивают счетчик.
                # Для current допустим 0 (баланс мог обнулиться), для прибавления нужны числа больше 0.
                if not is_number(increment) or (increment < 0 if is_current else increment <= 0):
                    continue

                # Для current прогресс может уменьшаться: было 500 денег, стало 200 — value станет 200.
                # Остальные счетчики накапливаются. В обоих случаях ограничиваем значение целью.
                # Уже награжденное задание сюда не попадет: его пропустили выше.
                state["value"] = min(definition.target, increment if is_current else state["value"] + increment)
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
