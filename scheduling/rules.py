"""Scheduling rules for Shabbat and holiday dinner shifts."""

from datetime import date

DEFAULT_SHABBAT_DINNER_KEY = (5, "18:00")
DEFAULT_SHABBAT_OBSERVERS: set[str] = set()
DEFAULT_SHABBAT_SHIFT_KEYS = {
    (5, "18:00"),
    (5, "22:00"),
    (6, "02:00"),
    (6, "06:00"),
    (6, "10:00"),
    (6, "14:00"),
}


def holiday_dinner_slots(rules: dict | None) -> set[tuple[date, str]]:
    """Calendar (date, start_time) pairs treated like Shabbat dinner."""
    out: set[tuple[date, str]] = set()
    if not rules:
        return out
    raw = rules.get("holiday_dinner_shifts")
    if not isinstance(raw, list):
        return out
    for entry in raw:
        parsed = _holiday_dinner_slot(entry)
        if parsed is not None:
            out.add(parsed)
    return out


def is_exclusive_dinner_slot(
    roster_day_date: date,
    shift_start: str,
    shabbat_dinner_key: tuple[int, str] | None,
    holiday_slots: set[tuple[date, str]],
) -> bool:
    """Friday Shabbat dinner or a configured holiday dinner."""
    weekday = roster_day_date.isoweekday()
    if shabbat_dinner_key is not None and (weekday, shift_start) == shabbat_dinner_key:
        return True
    return (roster_day_date, shift_start) in holiday_slots


def is_holiday_dinner_only(
    roster_day_date: date,
    shift_start: str,
    holiday_slots: set[tuple[date, str]],
) -> bool:
    return (roster_day_date, shift_start) in holiday_slots


def is_shabbat_dinner_only(
    roster_day_date: date,
    shift_start: str,
    shabbat_dinner_key: tuple[int, str] | None,
) -> bool:
    if shabbat_dinner_key is None:
        return False
    weekday = roster_day_date.isoweekday()
    return (weekday, shift_start) == shabbat_dinner_key


def shabbat_rules(rules: dict | None) -> tuple[set[str], set[tuple[int, str]], tuple[int, str] | None]:
    """Extract Shabbat-related rules from config or use defaults."""
    if rules and rules.get("patrol"):
        return set(), set(), None

    observers = set(DEFAULT_SHABBAT_OBSERVERS)
    shabbat_shift_keys = set(DEFAULT_SHABBAT_SHIFT_KEYS)
    shabbat_dinner_key = DEFAULT_SHABBAT_DINNER_KEY

    if not rules:
        return observers, shabbat_shift_keys, shabbat_dinner_key

    if "shabbat_observers" in rules:
        observers = set(rules.get("shabbat_observers") or [])

    if "shabbat_shifts" in rules and rules.get("shabbat_shifts"):
        shabbat_shift_keys = {
            (entry["weekday"], entry["start_time"])
            for entry in rules["shabbat_shifts"]
        }

    if "shabbat_dinner_shift" in rules and rules.get("shabbat_dinner_shift"):
        dinner_cfg = rules["shabbat_dinner_shift"]
        shabbat_dinner_key = (dinner_cfg["weekday"], dinner_cfg["start_time"])

    return observers, shabbat_shift_keys, shabbat_dinner_key


def _holiday_dinner_slot(entry: object) -> tuple[date, str] | None:
    if not isinstance(entry, dict):
        return None
    d = entry.get("date")
    start_time = entry.get("start_time")
    if not isinstance(d, str) or not isinstance(start_time, str):
        return None
    try:
        return date.fromisoformat(d), start_time
    except ValueError:
        return None
