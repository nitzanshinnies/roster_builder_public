"""Public scheduler facade for roster generation."""

import random
from datetime import datetime, timedelta

from models import (
    Guard,
    PATROL_SHIFT_DURATION_HOURS,
    Roster,
    RosterDay,
    generate_shifts,
    get_hebrew_day_name,
    patrol_shifts,
)
from scheduling.arr import build_arr
from scheduling.continuity import (
    continuity_matches,
    continuity_snapshot,
    parse_arr_continuity,
    parse_srr_continuity,
)
from scheduling.counts import compute_min_rest_per_guard
from scheduling.srr import build_srr
from shift_constraints import build_guard_shift_constraints_lookup

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
    """Build a roster by dispatching to the selected algorithm.

    Returns:
        roster, current_counts, continuity_snapshot (for commit — links this period
        to the next when start dates are back-to-back), continuity_applied.
    """
    if algorithm not in VALID_ALGORITHMS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Use one of: {VALID_ALGORITHMS}")

    # Make generation deterministic for the given date, so preview runs
    # match the final --commit run perfectly.
    random.seed(int(start_date.timestamp()))

    if patrol:
        shifts = patrol_shifts()
        first_shift_start = shifts[0].start_time
        effective_shift_hours = PATROL_SHIFT_DURATION_HOURS
        cont = None
        continuity_applied = False
    else:
        shifts = generate_shifts(start_date.hour, shift_duration_hours)
        first_shift_start = shifts[0].start_time
        effective_shift_hours = shift_duration_hours
        cont = continuity_matches(
            history,
            start_date,
            guards,
            algorithm,
            shift_duration_hours,
            first_shift_start,
        )
        continuity_applied = cont is not None

    # Build roster days
    roster_days = []
    for day_offset in range(roster_length_days):
        day_date = (start_date + timedelta(days=day_offset)).date()
        day_name = get_hebrew_day_name(day_date)
        roster_days.append(RosterDay(date=day_date, day_name_he=day_name))

    guard_allowed = build_guard_shift_constraints_lookup(guards)

    srr_state_out: dict | None = None
    arr_ends_out: dict[str, datetime | None] | None = None

    if algorithm == ALG_SRR:
        srr_seed = None if patrol else parse_srr_continuity(cont, guards)
        current_counts, srr_state_out = build_srr(
            guards,
            shifts,
            roster_days,
            history,
            guard_allowed,
            rules,
            srr_seed=srr_seed,
            patrol=patrol,
            rotation_start=rotation_start,
        )
    else:
        arr_last_seed = None if patrol else parse_arr_continuity(cont, guards)
        current_counts, arr_ends_out = build_arr(
            guards,
            shifts,
            roster_days,
            history,
            guard_allowed,
            min_rest_hours,
            rules,
            last_shift_end_seed=arr_last_seed,
            roster_start=start_date,
        )

    roster = Roster(
        days=roster_days,
        shifts=shifts,
        guards=guards,
        start_date=start_date,
    )

    next_continuity_snapshot = continuity_snapshot(
        start_date,
        roster_length_days,
        algorithm,
        effective_shift_hours,
        first_shift_start,
        guards,
        srr_state=srr_state_out,
        arr_last_shift_end=arr_ends_out,
    )

    return roster, current_counts, next_continuity_snapshot, continuity_applied
