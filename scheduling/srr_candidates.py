"""SRR candidate eligibility."""

from models import Guard, RosterDay, Shift
from shift_constraints import GuardShiftConstraints, is_guard_allowed_for_slot


def srr_candidate_allowed(
    assigned_friday_shabbat_dinner: set[str],
    assigned_holiday_dinner: set[str],
    assigned_today: set[str],
    candidate: Guard,
    dinner_state: tuple[bool, bool, bool],
    guard_allowed: dict[str, GuardShiftConstraints],
    require_new_guard_today: bool,
    roster_day: RosterDay,
    shabbat_observers: set[str],
    shabbat_shift_keys: set[tuple[int, str]],
    shift: Shift,
) -> bool:
    _is_exclusive_dinner, is_sd, is_hd = dinner_state
    if not is_guard_allowed_for_slot(guard_allowed[candidate.name], roster_day.date, shift):
        return False
    if (roster_day.date.isoweekday(), shift.start_time) in shabbat_shift_keys:
        if candidate.name in shabbat_observers:
            return False
    if require_new_guard_today and candidate.name in assigned_today:
        return False
    if is_hd and candidate.name in assigned_friday_shabbat_dinner:
        return False
    return not (is_sd and candidate.name in assigned_holiday_dinner)
