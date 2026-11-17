from lib.utils.schemas.game import UpgradeType


def build_upgrade_snapshot(config: dict, user: dict) -> dict:
    # 1. config — описание ВСЕХ прокачек, user — только сохраненные уровни конкретного пользователя.
    # Из них собираем данные для счетчиков и фильтров: upgrades.<type>.<subtype>.level/value
    # и summary.<group>.total_count/maxed_count/all_maxed.
    # Номер ступени и её эффект — разные вещи. Например, level=2, а вместимость value=5000.
    # Максимум: next == null, как в ручке покупки.
    snapshot = {"upgrades": {}, "summary": {}}
    # Две общие сводки: по всем прокачкам и по всем, кроме настроек.
    for group in ("all", "non_settings"):
        snapshot["summary"][group] = {"total_count": 0, "maxed_count": 0, "all_maxed": 0}
    # 2. Перебираем известные разделы прокачек. Если раздела нет в конфиге — пропускаем.
    for upgrade_type in UpgradeType:
        items = config.get(upgrade_type, {}).get("upgrades")
        if items is None:
            continue
        snapshot["upgrades"][upgrade_type] = {}
        summary = {"total_count": 0, "maxed_count": 0, "all_maxed": 0}
        # 3. Отдельная сводка для текущего раздела, например resources.
        for subtype, item in items.items():
            summary["total_count"] += 1
            # Новая прокачка может еще отсутствовать у пользователя — считаем ее уровнем 0.
            level = user.get(upgrade_type, {}).get(subtype, 0)
            # В JSON ключи ступеней — строки: "0", "1", "2".
            entry = item["upgrades"].get(str(level))
            # Если сохраненного уровня нет в конфиге, не выдумываем его эффект.
            # В total_count прокачка уже учтена, но максимально прокачанной считаться не будет.
            if entry is None:
                continue
            # Отсутствующее поле next не означает максимум: нужен именно явно указанный null.
            maxed = "next" in entry and entry["next"] is None
            snapshot["upgrades"][upgrade_type][subtype] = {
                "level": level,
                "value": entry["value"],
                "maxed": maxed,
            }
            # int(True) = 1, int(False) = 0: так считаем число прокачек на максимуме.
            summary["maxed_count"] += int(maxed)
        snapshot["summary"][upgrade_type] = summary
        # 4. Добавляем результаты раздела в общие сводки. Настройки не входят в non_settings.
        groups = ["all"] if upgrade_type == UpgradeType.SETTINGS else ["all", "non_settings"]
        for group in groups:
            snapshot["summary"][group]["total_count"] += summary["total_count"]
            snapshot["summary"][group]["maxed_count"] += summary["maxed_count"]
    for summary in snapshot["summary"].values():
        # 5. all_maxed — ЧИСЛО 0 или 1, чтобы его мог читать числовой счетчик current с target=1.
        # Пустые категории не завершают контракты «всё на максимум».
        summary["all_maxed"] = int(summary["total_count"] > 0 and summary["maxed_count"] == summary["total_count"])
    return snapshot
