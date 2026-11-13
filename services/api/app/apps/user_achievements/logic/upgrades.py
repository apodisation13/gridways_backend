from lib.utils.schemas.game import UpgradeType


def build_upgrade_snapshot(config: dict, user: dict) -> dict:
    # Номер ступени и её эффект — разные вещи. Максимум: next == null, как в ручке покупки.
    snapshot = {"upgrades": {}, "summary": {}}
    for group in ("all", "non_settings"):
        snapshot["summary"][group] = {"total_count": 0, "maxed_count": 0, "all_maxed": 0}
    for upgrade_type in UpgradeType:
        items = config.get(upgrade_type, {}).get("upgrades")
        if items is None:
            continue
        snapshot["upgrades"][upgrade_type] = {}
        summary = {"total_count": 0, "maxed_count": 0, "all_maxed": 0}
        for subtype, item in items.items():
            summary["total_count"] += 1
            level = user.get(upgrade_type, {}).get(subtype, 0)
            entry = item["upgrades"].get(str(level))
            if entry is None:
                continue
            maxed = "next" in entry and entry["next"] is None
            snapshot["upgrades"][upgrade_type][subtype] = {
                "level": level, "value": entry["value"], "maxed": maxed,
            }
            summary["maxed_count"] += int(maxed)
        snapshot["summary"][upgrade_type] = summary
        groups = ["all"] if upgrade_type == UpgradeType.SETTINGS else ["all", "non_settings"]
        for group in groups:
            snapshot["summary"][group]["total_count"] += summary["total_count"]
            snapshot["summary"][group]["maxed_count"] += summary["maxed_count"]
    for summary in snapshot["summary"].values():
        # Пустые категории не завершают контракты «всё на максимум».
        summary["all_maxed"] = int(summary["total_count"] > 0 and summary["maxed_count"] == summary["total_count"])
    return snapshot
