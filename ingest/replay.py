"""Replay parsed roster grids to recover continuity state."""

import random
from datetime import datetime

from models import Guard, generate_shifts

from .arr_match import match_seeded_arr
from .srr_match import match_any_srr_permutation, match_seeded_srr


def resolve_build_state(
    guards: list[Guard],
    shift_duration: int,
    start_date: datetime,
    roster_length: int,
    history: dict,
    rules: dict,
    expected: list[list[str]],
) -> tuple[str, dict, dict]:
    """Return (algorithm, current_counts, continuity_snapshot)."""
    random.seed(int(start_date.timestamp()))
    shifts = generate_shifts(start_date.hour, shift_duration)

    result = match_seeded_srr(
        guards,
        shifts,
        shift_duration,
        start_date,
        roster_length,
        history,
        rules,
        expected,
    )
    if result is not None:
        return result

    result = match_seeded_arr(
        guards,
        shifts,
        shift_duration,
        start_date,
        roster_length,
        history,
        rules,
        expected,
    )
    if result is not None:
        return result

    result = match_any_srr_permutation(
        guards,
        shifts,
        shift_duration,
        start_date,
        roster_length,
        history,
        rules,
        expected,
    )
    if result is not None:
        return result

    raise ValueError(
        "Could not match HTML to SRR or ARR using current history and config. "
        "Check algorithm, config guards, or history snapshot used when the HTML was built."
    )
