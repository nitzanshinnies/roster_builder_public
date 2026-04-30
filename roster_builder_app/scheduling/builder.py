"""Roster generation orchestration."""

import random
from datetime import datetime, timedelta

from roster_builder_app.models import (
    Guard,
    PATROL_SHIFT_DURATION_HOURS,
    Roster,
    RosterDay,
    generate_shifts,
    get_hebrew_day_name,
    patrol_shifts,
)
from roster_builder_app.shift_constraints import build_guard_shift_constraints_lookup

from .arr import build_arr
from .continuity import continuity_matches, continuity_snapshot, parse_arr_continuity, parse_srr_continuity
from .counts import compute_min_rest_per_guard
from .srr import build_srr

ALG_ARR = "arr"
ALG_SRR = "srr"
DEFAULT_MIN_REST_HOURS = 8
VALID_ALGORITHMS = {ALG_SRR, ALG_ARR}


def build_roster(
    guards: list[Guard],
    shift_duration_hours: int,
    start_date: datetime,
    roster_length_days: int,
    history: dict,
    algorithm: str = ALG_SRR,
    min_rest_hours: int = DEFAULT_MIN_REST_HOURS,
    rules: dict | None = None,
    patrol: bool = False,
    rotation_start: str | None = None,
) -> tuple[Roster, dict, dict, bool]:
    """Build a roster by dispatching to the selected algorithm."""
    if algorithm not in VALID_ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Use one of: {VALID_ALGORITHMS}")

    random.seed(int(start_date.timestamp()))
    schedule = _schedule_shape(guards, shift_duration_hours, start_date, history, algorithm, patrol)
    roster_days = _build_roster_days(start_date, roster_length_days)
    guard_allowed = build_guard_shift_constraints_lookup(guards)
    srr_state_out: dict | None = None
    arr_ends_out: dict[str, datetime | None] | None = None

    if algorithm == ALG_SRR:
        srr_seed = None if patrol else parse_srr_continuity(schedule["continuity"], guards)
        current_counts, srr_state_out = build_srr(
            guards,
            schedule["shifts"],
            roster_days,
            history,
            guard_allowed,
            rules,
            srr_seed=srr_seed,
            patrol=patrol,
            rotation_start=rotation_start,
        )
    else:
        arr_last_seed = None if patrol else parse_arr_continuity(schedule["continuity"], guards)
        current_counts, arr_ends_out = build_arr(
            guards,
            schedule["shifts"],
            roster_days,
            history,
            guard_allowed,
            min_rest_hours,
            rules,
            last_shift_end_seed=arr_last_seed,
            roster_start=start_date,
        )

    roster = Roster(days=roster_days, shifts=schedule["shifts"], guards=guards, start_date=start_date)
    next_continuity_snapshot = continuity_snapshot(
        start_date,
        roster_length_days,
        algorithm,
        schedule["effective_shift_hours"],
        schedule["first_shift_start"],
        guards,
        srr_state=srr_state_out,
        arr_last_shift_end=arr_ends_out,
    )
    return roster, current_counts, next_continuity_snapshot, schedule["continuity"] is not None


def _build_roster_days(start_date: datetime, roster_length_days: int) -> list[RosterDay]:
    roster_days = []
    for day_offset in range(roster_length_days):
        day_date = (start_date + timedelta(days=day_offset)).date()
        roster_days.append(RosterDay(date=day_date, day_name_he=get_hebrew_day_name(day_date)))
    return roster_days


def _schedule_shape(
    guards: list[Guard],
    shift_duration_hours: int,
    start_date: datetime,
    history: dict,
    algorithm: str,
    patrol: bool,
) -> dict:
    if patrol:
        shifts = patrol_shifts()
        return {
            "continuity": None,
            "effective_shift_hours": PATROL_SHIFT_DURATION_HOURS,
            "first_shift_start": shifts[0].start_time,
            "shifts": shifts,
        }
    shifts = generate_shifts(start_date.hour, shift_duration_hours)
    first_shift_start = shifts[0].start_time
    return {
        "continuity": continuity_matches(
            history,
            start_date,
            guards,
            algorithm,
            shift_duration_hours,
            first_shift_start,
        ),
        "effective_shift_hours": shift_duration_hours,
        "first_shift_start": first_shift_start,
        "shifts": shifts,
    }
