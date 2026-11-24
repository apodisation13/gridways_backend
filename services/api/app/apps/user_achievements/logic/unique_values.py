import json

from services.api.app.apps.user_achievements.logic.filters import is_number


def unique_value(value: object) -> str | int | float | None:
    # Прежние строки/числа остаются прежними; объекты храним стабильной строкой.
    if isinstance(value, str):
        if value.startswith(("object:", "string:")):
            return "string:" + value
        return value
    if is_number(value):
        return value
    if isinstance(value, dict):
        return "object:" + json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return None


def has_unique_value(seen: list, value: object, key: str | float) -> bool:
    if not isinstance(value, dict):
        return key in seen
    for saved in seen:
        if not isinstance(saved, str) or not saved.startswith("object:"):
            continue
        try:
            # Сравнение через свой сериализатор учитывает разные записи чисел
            # между JS/Python: 1 и 1.0 должны означать один рецепт.
            previous = json.loads(saved[7:])
            if same_json(previous, value):
                return True
        except (ValueError, TypeError):
            continue
    return False


def same_json(left: object, right: object) -> bool:
    # В Python True == 1, но в JSON это разные значения.
    if is_number(left) and is_number(right):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_json(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right, strict=True))
    return left == right
