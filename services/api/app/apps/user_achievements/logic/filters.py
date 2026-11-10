from math import isfinite


_MISSING = object()


def get_field(data: dict, path: str) -> object:
    # Путь относительно event.data. Числовой сегмент может обращаться к элементу массива.
    current = data
    for key in path.split("."):
        if not key or key in {"__proto__", "prototype", "constructor"}:
            return _MISSING
        if isinstance(current, dict):
            if key not in current:
                return _MISSING
            current = current[key]
        elif isinstance(current, list):
            if not key.isascii() or not key.isdecimal() or (len(key) > 1 and key.startswith("0")):
                return _MISSING
            index = int(key)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


def is_number(value: object) -> bool:
    # В Python bool является int, но в правилах достижений это разные типы.
    return type(value) in (int, float) and isfinite(value)


def equal_scalar(actual: object, expected: object) -> bool:
    if is_number(actual) and is_number(expected):
        return actual == expected
    return type(actual) is type(expected) and actual == expected


def matches_condition(actual: object, condition: object) -> bool:
    if not isinstance(condition, dict):
        return actual is not _MISSING and equal_scalar(actual, condition)
    operator, expected = condition["type"], condition["value"]
    if operator == "exists":
        return (actual is not _MISSING) == expected
    # null — значение существующего поля. Отсутствие проходит только exists: false.
    if actual is _MISSING:
        return False
    if operator == "eq":
        return equal_scalar(actual, expected)
    if operator == "ne":
        return not equal_scalar(actual, expected)
    if operator == "in":
        return any(equal_scalar(actual, item) for item in expected)
    if not is_number(actual) or not is_number(expected):
        return False
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
    # Все условия соединены через И; пустой словарь не ограничивает событие.
    return all(matches_condition(get_field(data, path), condition) for path, condition in filters.items())
