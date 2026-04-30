"""ARR roster grid replay."""

import random
from datetime import datetime

from models import Guard
from scheduler import ALG_ARR
from scheduling.arr import build_arr
from scheduling.continuity import continuity_snapshot
from shift_constraints import build_guard_shift_constraints_lookup

from .roster_grid import fresh_roster_days, grid_matches


def match_seeded_arr(
    guards: list[Guard],
    shifts: list,
    shift_duration: int,
    start_date: datetime,
    roster_length: int,
    history: dict,
    rules: dict,
    expected: list[list[str]],
) -> tuple[str, dict, dict] | None:
    random.seed(int(start_date.timestamp()))
    roster_days = fresh_roster_days(start_date, roster_length)
    counts, arr_ends = build_arr(
        guards,
        shifts,
        roster_days,
        history,
        build_guard_shift_constraints_lookup(guards),
        min_rest_hours=8,
        rules=rules,
        last_shift_end_seed=None,
    )
    if not grid_matches(roster_days, shifts, expected):
        return None
    snap = continuity_snapshot(
        start_date,
        roster_length,
        ALG_ARR,
        shift_duration,
        shifts[0].start_time,
        guards,
        arr_last_shift_end=arr_ends,
    )
    return ALG_ARR, counts, snap
