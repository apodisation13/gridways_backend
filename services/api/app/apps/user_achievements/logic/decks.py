def build_deck_summary(cards: object) -> dict:
    # Эта функция не обращается к БД: получает массив карт из снимка события и строит summary.
    # Считаем только карты, лидер находится отдельно и сюда не передаётся.
    # 1. Если массива карт нет, считаем его пустым. Флаги «все карты такие-то» тогда будут False.
    entries = cards if isinstance(cards, list) else []
    by_color = {"Bronze": 0, "Silver": 0, "Gold": 0}
    neutral_count = 0
    known_factions = 0
    # 2. Считаем цвета и фракции по отдельным картам.
    # Каждый элемент массива считается одной картой, дополнительных множителей здесь нет.
    for card in entries:
        if not isinstance(card, dict):
            continue
        color = card.get("color")
        if isinstance(color, str) and color in by_color:
            by_color[color] += 1
        faction = card.get("faction")
        # Отдельно считаем карты, у которых фракция вообще известна.
        # Без этого неизвестная фракция ошибочно прошла бы проверку «нет нейтральных карт».
        if isinstance(faction, str) and faction:
            known_factions += 1
        if faction == "Neutral":
            neutral_count += 1
    # 3. Общий размер — длина исходного массива, даже если какой-то элемент был некорректен.
    # Такой элемент не прибавит цвет/фракцию, поэтому обычно не даст пройти условиям «все ...».
    count = len(entries)
    # all_* проверяют состав целиком. Непустота обязательна: пустая колода не является «вся золотая».
    # no_neutral также требует известной фракции у КАЖДОЙ карты.
    return {
        "cards_count": count,
        "by_color": by_color,
        "neutral_count": neutral_count,
        "all_bronze": count > 0 and by_color["Bronze"] == count,
        "all_silver": count > 0 and by_color["Silver"] == count,
        "all_gold": count > 0 and by_color["Gold"] == count,
        "all_neutral": count > 0 and neutral_count == count,
        "no_neutral": count > 0 and known_factions == count and neutral_count == 0,
    }
