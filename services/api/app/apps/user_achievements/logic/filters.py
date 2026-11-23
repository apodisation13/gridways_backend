from math import isfinite


# Отдельная метка «поля нет». None использовать нельзя: JSON null — это существующее значение.
_MISSING = object()


def get_field(data: dict, path: str) -> object:
    # 1. Идем по пути внутри event.data, шаг за шагом.
    # Например, actor.data.damage: сначала data["actor"], затем ["data"], затем ["damage"].
    # Путь deck.cards.0.color дополнительно обращается к первой карте массива.
    current = data
    for key in path.split("."):
        # Пустой сегмент (actor..id) и служебные имена JS не поддерживаем.
        # Так правила путей остаются совместимыми с обработкой на фронте.
        if not key or key in {"__proto__", "prototype", "constructor"}:
            return _MISSING
        # 2. Для словаря сегмент пути — это обычный ключ.
        if isinstance(current, dict):
            if key not in current:
                return _MISSING
            current = current[key]
        # 3. Для списка сегмент должен быть индексом: 0, 1, 2 и т.д.
        elif isinstance(current, list):
            # Не принимаем отрицательные индексы, дроби, 01 и не-ASCII цифры.
            if not key.isascii() or not key.isdecimal() or (len(key) > 1 and key.startswith("0")):
                return _MISSING
            index = int(key)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            # Дальше идти нельзя: например, actor.id уже число, а путь требует actor.id.name.
            return _MISSING
    # Вернем и None, если поле действительно есть и содержит null. Это не _MISSING.
    return current


def is_number(value: object) -> bool:
    # В Python bool является int, но в правилах достижений это разные типы.
    # Поэтому проверяем точный type, а isfinite отсекает NaN и бесконечности.
    return type(value) in (int, float) and isfinite(value)


def equal_scalar(actual: object, expected: object) -> bool:
    # Числа 10 и 10.0 равны. Но строка "10" не равна числу 10, а True не равен 1.
    if is_number(actual) and is_number(expected):
        return actual == expected
    return type(actual) is type(expected) and actual == expected


def matches_condition(actual: object, condition: object) -> bool:
    # 1. Короткая запись: {"actor.color": "Bronze"} означает обычное равенство.
    if not isinstance(condition, dict):
        return actual is not _MISSING and equal_scalar(actual, condition)
    # 2. Полная запись: {"actor.data.damage": {"type": "gte", "value": 10}}.
    # Структуру такого условия до этого уже проверил Pydantic при чтении конфига.
    operator, expected = condition["type"], condition["value"]
    # exists проверяет наличие поля, а не его истинность: null, 0 и False тоже существуют.
    if operator == "exists":
        return (actual is not _MISSING) == expected
    # null — значение существующего поля. Отсутствие проходит только exists: false.
    if actual is _MISSING:
        return False
    # eq — равно, ne — не равно. Для отсутствующего поля даже ne вернет False: выход был выше.
    if operator == "eq":
        return equal_scalar(actual, expected)
    if operator == "ne":
        return not equal_scalar(actual, expected)
    # in: найденное значение должно совпасть хотя бы с одним элементом списка из конфига.
    if operator == "in":
        return any(equal_scalar(actual, item) for item in expected)
    # Сравнения больше/меньше работают только с числами, без преобразования строк и bool.
    if not is_number(actual) or not is_number(expected):
        return False
    # gt >, gte >=, lt <, lte <=.
    if operator == "gt":
        return actual > expected
    if operator == "gte":
        return actual >= expected
    if operator == "lt":
        return actual < expected
    if operator == "lte":
        return actual <= expected
    return False


def matches_filters(data: dict, filters: dict) -> bool:
    # Соседние условия — И. Для any достаточно одного подходящего набора И.
    # Формат (непустой список, без вложенного any) уже проверен схемой конфига.
    for path, condition in filters.items():
        if path == "any":
            matched = any(
                all(matches_condition(get_field(data, field), rule) for field, rule in group.items())
                for group in condition
            )
            if not matched:
                return False
        elif not matches_condition(get_field(data, path), condition):
            return False
    return True
