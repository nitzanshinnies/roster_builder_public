"""SRR roster grid replay."""

import itertools
import random
from datetime import datetime

from history_manager import get_guard_history
from models import Guard
from scheduling.builder import ALG_SRR
from scheduling.continuity import continuity_snapshot
from scheduling.srr import build_srr
from shift_constraints import build_guard_shift_constraints_lookup

from .roster_grid import fresh_roster_days, grid_matches


def match_any_srr_permutation(
    guards: list[Guard],
    shifts: list,
    shift_duration: int,
    start_date: datetime,
    roster_length: int,
    history: dict,
    rules: dict,
    expected: list[list[str]],
) -> tuple[str, dict, dict] | None:
    guard_allowed = build_guard_shift_constraints_lookup(guards)
    for rotation_order in itertools.permutations(guards):
        result = _match_rotation(
            guards,
            shifts,
            shift_duration,
            start_date,
            roster_length,
            history,
            rules,
            expected,
            guard_allowed,
            list(rotation_order),
        )
        if result is not None:
            return result
    return None


def match_seeded_srr(
    guards: list[Guard],
    shifts: list,
    shift_duration: int,
    start_date: datetime,
    roster_length: int,
    history: dict,
    rules: dict,
    expected: list[list[str]],
) -> tuple[str, dict, dict] | None:
    return _match_rotation(
        guards,
        shifts,
        shift_duration,
        start_date,
        roster_length,
        history,
        rules,
        expected,
        build_guard_shift_constraints_lookup(guards),
        _srr_rotation_order(guards, history),
    )


def _match_rotation(
    guards: list[Guard],
    shifts: list,
    shift_duration: int,
    start_date: datetime,
    roster_length: int,
    history: dict,
    rules: dict,
    expected: list[list[str]],
    guard_allowed: dict,
    rotation_order: list[Guard],
) -> tuple[str, dict, dict] | None:
    for seed_idx in range(len(rotation_order)):
        roster_days = fresh_roster_days(start_date, roster_length)
        counts, srr_state = build_srr(
            guards,
            shifts,
            roster_days,
            history,
            guard_allowed,
            rules,
            srr_seed=(rotation_order, seed_idx),
        )
        if grid_matches(roster_days, shifts, expected):
            return _srr_result(start_date, roster_length, shift_duration, shifts, guards, counts, srr_state)
    return None


def _srr_result(
    start_date: datetime,
    roster_length: int,
    shift_duration: int,
    shifts: list,
    guards: list[Guard],
    counts: dict,
    srr_state: dict,
) -> tuple[str, dict, dict]:
    snap = continuity_snapshot(
        start_date,
        roster_length,
        ALG_SRR,
        shift_duration,
        shifts[0].start_time,
        guards,
        srr_state=srr_state,
    )
    return ALG_SRR, counts, snap


def _srr_rotation_order(guards: list[Guard], history: dict) -> list[Guard]:
    def hist_sort_key(guard: Guard) -> tuple:
        guard_history = get_guard_history(history, guard.name)
        return guard_history["total"], random.random()

    return sorted(guards, key=hist_sort_key)
