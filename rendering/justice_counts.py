"""Justice report count preparation."""

from models import Guard, Shift


def build_cumulative_counts(
    guards: list[Guard],
    shifts: list[Shift],
    current_counts: dict,
    history: dict,
) -> dict:
    cumulative = {}
    for guard in guards:
        hist_guard = history.get("guards", {}).get(guard.name, {"total": 0, "shifts": {}, "friday_dinner": 0})
        curr = current_counts.get(guard.name, {"total": 0, "shifts": {}, "friday_dinner": 0})
        cumulative[guard.name] = {
            "total": hist_guard["total"] + curr["total"],
            "shifts": _cumulative_shift_counts(shifts, hist_guard, curr),
            "friday_dinner": hist_guard.get("friday_dinner", 0) + curr.get("friday_dinner", 0),
        }
    return cumulative


def has_history_counts(guards: list[Guard], history: dict) -> bool:
    return any(history.get("guards", {}).get(guard.name, {}).get("total", 0) > 0 for guard in guards)


def highlight_class(total: int, max_total: int, min_total: int) -> str:
    if total == max_total and max_total != min_total:
        return ' class="highlight-max"'
    if total == min_total and max_total != min_total:
        return ' class="highlight-min"'
    return ""


def total_range(rows: list[dict]) -> tuple[int, int]:
    totals = [row["total"] for row in rows]
    return (
        max(totals) if totals else 0,
        min(totals) if totals else 0,
    )


def _cumulative_shift_counts(shifts: list[Shift], hist_guard: dict, curr: dict) -> dict:
    cum_shifts = {}
    for shift in shifts:
        history_count = hist_guard.get("shifts", {}).get(shift.start_time, 0)
        current_count = curr.get("shifts", {}).get(shift.start_time, 0)
        cum_shifts[shift.start_time] = history_count + current_count
    return cum_shifts
