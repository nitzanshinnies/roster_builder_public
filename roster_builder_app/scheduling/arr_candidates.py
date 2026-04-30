"""ARR candidate filtering."""

from datetime import datetime

from roster_builder_app.models import Guard, RosterDay, Shift
from roster_builder_app.shift_constraints import GuardShiftConstraints, is_guard_allowed_for_slot

from .arr_rest import rest_ok


def arr_candidates(
    assigned_friday_shabbat_dinner: set[str],
    assigned_holiday_dinner: set[str],
    assigned_today: set[str],
    dinner_state: tuple[bool, bool, bool],
    guard_allowed: dict[str, GuardShiftConstraints],
    guards: list[Guard],
    min_rest_hours: int,
    roster_day: RosterDay,
    shabbat_observers: set[str],
    shabbat_shift_keys: set[tuple[int, str]],
    shift: Shift,
    slot_start: datetime,
    last_shift_end: dict[str, datetime | None],
) -> list[Guard]:
    for enforce_rest, enforce_same_day in ((True, True), (True, False), (False, False)):
        candidates = _arr_candidates_for_pass(
            assigned_friday_shabbat_dinner,
            assigned_holiday_dinner,
            assigned_today,
            dinner_state,
            guard_allowed,
            guards,
            min_rest_hours,
            roster_day,
            shabbat_observers,
            shabbat_shift_keys,
            shift,
            slot_start,
            last_shift_end,
            enforce_rest=enforce_rest,
            enforce_same_day=enforce_same_day,
        )
        if candidates:
            return candidates
    return []


def _arr_candidate_allowed(
    assigned_friday_shabbat_dinner: set[str],
    assigned_holiday_dinner: set[str],
    assigned_today: set[str],
    candidate: Guard,
    dinner_state: tuple[bool, bool, bool],
    guard_allowed: dict[str, GuardShiftConstraints],
    roster_day: RosterDay,
    shabbat_observers: set[str],
    shabbat_shift_keys: set[tuple[int, str]],
    shift: Shift,
    *,
    enforce_same_day: bool,
) -> bool:
    _is_exclusive_dinner, is_sd, is_hd = dinner_state
    if not is_guard_allowed_for_slot(guard_allowed[candidate.name], roster_day.date, shift):
        return False
    if (roster_day.date.isoweekday(), shift.start_time) in shabbat_shift_keys:
        if candidate.name in shabbat_observers:
            return False
    if enforce_same_day and candidate.name in assigned_today:
        return False
    if is_hd and candidate.name in assigned_friday_shabbat_dinner:
        return False
    return not (is_sd and candidate.name in assigned_holiday_dinner)


def _arr_candidates_for_pass(
    assigned_friday_shabbat_dinner: set[str],
    assigned_holiday_dinner: set[str],
    assigned_today: set[str],
    dinner_state: tuple[bool, bool, bool],
    guard_allowed: dict[str, GuardShiftConstraints],
    guards: list[Guard],
    min_rest_hours: int,
    roster_day: RosterDay,
    shabbat_observers: set[str],
    shabbat_shift_keys: set[tuple[int, str]],
    shift: Shift,
    slot_start: datetime,
    last_shift_end: dict[str, datetime | None],
    *,
    enforce_rest: bool,
    enforce_same_day: bool,
) -> list[Guard]:
    return [
        guard
        for guard in guards
        if _arr_candidate_allowed(
            assigned_friday_shabbat_dinner,
            assigned_holiday_dinner,
            assigned_today,
            guard,
            dinner_state,
            guard_allowed,
            roster_day,
            shabbat_observers,
            shabbat_shift_keys,
            shift,
            enforce_same_day=enforce_same_day,
        )
        and (not enforce_rest or rest_ok(last_shift_end[guard.name], slot_start, min_rest_hours))
    ]
