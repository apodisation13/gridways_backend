def build_deck_summary(cards: object) -> dict:
    # Считаем только карты, лидер находится отдельно и сюда не передаётся.
    entries = cards if isinstance(cards, list) else []
    by_color = {"Bronze": 0, "Silver": 0, "Gold": 0}
    neutral_count = 0
    known_factions = 0
    for card in entries:
        if not isinstance(card, dict):
            continue
        color = card.get("color")
        if isinstance(color, str) and color in by_color:
            by_color[color] += 1
        faction = card.get("faction")
        if isinstance(faction, str) and faction:
            known_factions += 1
        if faction == "Neutral":
            neutral_count += 1
    count = len(entries)
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
