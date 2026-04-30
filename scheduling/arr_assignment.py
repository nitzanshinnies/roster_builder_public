"""ARR scoring and assignment recording."""

import random
from datetime import datetime, timedelta

from models import Guard, RosterDay, Shift

from .arr_rest import rest_penalty, shift_hours, shift_hours_from_label, target_rest_hours


def arr_score(
    guard: Guard,
    shift: Shift,
    slot_start: datetime,
    shifts: list[Shift],
    state: dict,
    is_exclusive_dinner: bool,
) -> tuple:
    hist_shift = state["hist_shifts"].get(guard.name, {}).get(shift.start_time, 0)
    cum_shift = hist_shift + state["current_shifts"][guard.name][shift.start_time]
    current_total = state["current_total"][guard.name]
    hist_total = state["hist_total"].get(guard.name, 0)
    dinner_total = state["friday_dinner_hist"].get(guard.name, 0) + state["friday_dinner_counts"][guard.name]
    rest_score = rest_penalty(
        state["last_shift_end"][guard.name],
        slot_start,
        target_rest_hours(len(shifts), len(state["current_total"]), shift_hours(shifts)),
    )
    if is_exclusive_dinner:
        return dinner_total, current_total, rest_score, cum_shift, random.random()
    return current_total, hist_total, rest_score, cum_shift, random.random()


def record_arr_assignment(
    assigned_friday_shabbat_dinner: set[str],
    assigned_holiday_dinner: set[str],
    assigned_today: set[str],
    chosen: Guard,
    current_dinner_state: tuple[bool, bool, bool],
    shift: Shift,
    slot_start: datetime,
    state: dict,
    roster_day: RosterDay,
) -> None:
    is_exclusive_dinner, is_sd, is_hd = current_dinner_state
    roster_day.assignments[shift.label] = chosen.name
    assigned_today.add(chosen.name)
    state["current_total"][chosen.name] += 1
    state["current_shifts"][chosen.name][shift.start_time] += 1
    if is_exclusive_dinner:
        state["friday_dinner_counts"][chosen.name] += 1
    if is_sd:
        assigned_friday_shabbat_dinner.add(chosen.name)
    if is_hd:
        assigned_holiday_dinner.add(chosen.name)
    state["last_shift_end"][chosen.name] = slot_start + timedelta(hours=shift_hours_from_label(shift))
