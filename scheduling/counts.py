"""Shared count and rest calculations for schedulers."""

from datetime import datetime, timedelta

from models import Guard, Roster

from .time_utils import shift_datetime


def build_counts_dict(
    guards: list[Guard],
    current_total: dict[str, int],
    current_shifts: dict[str, dict[str, int]],
    friday_dinner_counts: dict[str, int] | None = None,
) -> dict:
    """Build the current_counts dict for history commit."""
    return {
        guard.name: {
            "total": current_total[guard.name],
            "shifts": current_shifts[guard.name],
            "friday_dinner": (friday_dinner_counts or {}).get(guard.name, 0),
        }
        for guard in guards
    }


def compute_min_rest_per_guard(roster: Roster, shift_duration_hours: int) -> dict[str, float | None]:
    """Compute the minimum rest duration between consecutive shifts for each guard."""
    shifts = roster.shifts
    start_date = roster.start_date
    guard_shift_times: dict[str, list[tuple[datetime, datetime]]] = {
        guard.name: []
        for guard in roster.guards
    }

    for day_offset, roster_day in enumerate(roster.days):
        for shift in shifts:
            guard_name = roster_day.assignments.get(shift.label)
            if not guard_name:
                continue
            slot_start = shift_datetime(
                start_date,
                day_offset,
                shift.start_time,
                shifts[0].start_time,
            )
            slot_end = slot_start + timedelta(hours=shift_duration_hours)
            guard_shift_times[guard_name].append((slot_start, slot_end))

    return {
        guard_name: _minimum_rest(times)
        for guard_name, times in guard_shift_times.items()
    }


def _minimum_rest(times: list[tuple[datetime, datetime]]) -> float | None:
    if len(times) <= 1:
        return None
    times.sort(key=lambda item: item[0])
    return min(
        (times[index][0] - times[index - 1][1]).total_seconds() / 3600
        for index in range(1, len(times))
    )
