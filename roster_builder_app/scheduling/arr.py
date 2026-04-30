"""Advanced round-robin scheduler."""

from datetime import datetime

from roster_builder_app.models import Guard, RosterDay, Shift
from roster_builder_app.shift_constraints import GuardShiftConstraints, coerce_guard_shift_constraints_lookup

from .arr_assignment import arr_score, record_arr_assignment
from .arr_candidates import arr_candidates
from .arr_state import arr_state
from .counts import build_counts_dict
from .dinner import dinner_state
from .rules import holiday_dinner_slots, shabbat_rules
from .time_utils import shift_datetime


def build_arr(
    guards: list[Guard],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    history: dict,
    guard_allowed: dict[str, GuardShiftConstraints | set[str] | None],
    min_rest_hours: int,
    rules: dict | None = None,
    last_shift_end_seed: dict[str, datetime | None] | None = None,
    roster_start: datetime | None = None,
) -> tuple[dict, dict[str, datetime | None]]:
    """Advanced round-robin: scoring-based with shift-type variety and rest handling."""
    guard_allowed = coerce_guard_shift_constraints_lookup(guard_allowed)
    state = arr_state(guards, history, shifts, last_shift_end_seed)
    shabbat_observers, shabbat_shift_keys, shabbat_dinner_key = shabbat_rules(rules)
    holiday_slots = holiday_dinner_slots(rules)
    assigned_friday_shabbat_dinner: set[str] = set()
    assigned_holiday_dinner: set[str] = set()
    anchor = roster_start or datetime.combine(roster_days[0].date, _first_shift_time(shifts))

    for day_offset, roster_day in enumerate(roster_days):
        assigned_today: set[str] = set()
        for shift in shifts:
            slot_start = shift_datetime(anchor, day_offset, shift.start_time, shifts[0].start_time)
            current_dinner_state = dinner_state(roster_day, shift, shabbat_dinner_key, holiday_slots)
            candidates = arr_candidates(
                assigned_friday_shabbat_dinner,
                assigned_holiday_dinner,
                assigned_today,
                current_dinner_state,
                guard_allowed,
                guards,
                min_rest_hours,
                roster_day,
                shabbat_observers,
                shabbat_shift_keys,
                shift,
                slot_start,
                state["last_shift_end"],
            )
            if not candidates:
                raise RuntimeError(
                    f"No candidate for {roster_day.day_name_he} {roster_day.date} "
                    f"shift {shift.label}. Constraints too restrictive."
                )

            chosen = min(
                candidates,
                key=lambda guard: arr_score(guard, shift, slot_start, shifts, state, current_dinner_state[0]),
            )
            record_arr_assignment(
                assigned_friday_shabbat_dinner,
                assigned_holiday_dinner,
                assigned_today,
                chosen,
                current_dinner_state,
                shift,
                slot_start,
                state,
                roster_day,
            )

    return (
        build_counts_dict(
            guards,
            state["current_total"],
            state["current_shifts"],
            state["friday_dinner_counts"],
        ),
        state["last_shift_end"],
    )


def _first_shift_time(shifts: list[Shift]):
    hour, minute = (int(part) for part in shifts[0].start_time.split(":"))
    return datetime.min.replace(hour=hour, minute=minute).time()


