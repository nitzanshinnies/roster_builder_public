"""ARR rest-window calculations."""

from datetime import datetime

from roster_builder_app.models import Shift

REST_PENALTY_MEDIUM_RATIO = 0.5
REST_PENALTY_STRONG_RATIO = 0.25
REST_PENALTY_WEAK_RATIO = 0.75
SECONDS_PER_HOUR = 3600


def rest_ok(last_shift_end: datetime | None, slot_start: datetime, min_rest_hours: int) -> bool:
    if last_shift_end is None:
        return True
    return (slot_start - last_shift_end).total_seconds() / SECONDS_PER_HOUR >= min_rest_hours


def rest_penalty(
    last_shift_end: datetime | None,
    slot_start: datetime,
    target_rest: float,
) -> int:
    if last_shift_end is None:
        return 0
    rest_gap = (slot_start - last_shift_end).total_seconds() / SECONDS_PER_HOUR
    if rest_gap >= target_rest * REST_PENALTY_WEAK_RATIO:
        return 0
    if rest_gap >= target_rest * REST_PENALTY_MEDIUM_RATIO:
        return 1
    if rest_gap >= target_rest * REST_PENALTY_STRONG_RATIO:
        return 2
    return 3


def shift_hours(shifts: list[Shift]) -> int:
    if len(shifts) < 2:
        return shift_hours_from_label(shifts[0])
    return shift_hours_between(shifts[0].start_time, shifts[1].start_time)


def shift_hours_between(start_time: str, end_time: str) -> int:
    start_hour = int(start_time.split(":")[0])
    end_hour = int(end_time.split(":")[0])
    hours = end_hour - start_hour
    return hours if hours > 0 else hours + 24


def shift_hours_from_label(shift: Shift) -> int:
    return shift_hours_between(shift.start_time, shift.end_time)


def target_rest_hours(shifts_per_day: int, guard_count: int, shift_hours_value: int) -> float:
    avg_shifts_per_day = shifts_per_day / guard_count
    return (24.0 / avg_shifts_per_day) - shift_hours_value
