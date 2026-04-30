"""ARR mutable scheduling state."""

from datetime import datetime

from history_manager import get_guard_history
from models import Guard, Shift


def arr_state(
    guards: list[Guard],
    history: dict,
    shifts: list[Shift],
    last_shift_end_seed: dict[str, datetime | None] | None,
) -> dict:
    hist_total: dict[str, int] = {}
    hist_shifts: dict[str, dict[str, int]] = {}
    friday_dinner_hist: dict[str, int] = {}
    for guard in guards:
        guard_history = get_guard_history(history, guard.name)
        hist_total[guard.name] = guard_history["total"]
        hist_shifts[guard.name] = dict(guard_history.get("shifts", {}))
        friday_dinner_hist[guard.name] = guard_history.get("friday_dinner", 0)

    last_shift_end: dict[str, datetime | None] = {guard.name: None for guard in guards}
    if last_shift_end_seed:
        for guard in guards:
            value = last_shift_end_seed.get(guard.name)
            if value is not None:
                last_shift_end[guard.name] = value

    return {
        "current_shifts": {guard.name: {shift.start_time: 0 for shift in shifts} for guard in guards},
        "current_total": {guard.name: 0 for guard in guards},
        "friday_dinner_counts": {guard.name: 0 for guard in guards},
        "friday_dinner_hist": friday_dinner_hist,
        "hist_shifts": hist_shifts,
        "hist_total": hist_total,
        "last_shift_end": last_shift_end,
    }
