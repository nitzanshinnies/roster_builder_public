"""Patrol SRR for four guards: fixed pairs with alternating evening/morning roles."""

from roster_builder_app.models import Guard, RosterDay, Shift
from roster_builder_app.shift_constraints import (
    GuardShiftConstraints,
    coerce_guard_shift_constraints_lookup,
    is_guard_allowed_for_slot,
)

from .counts import build_counts_dict
from .srr_assignment import _record_assignment, _specific_slot_candidate
from .srr_state import SrrState, srr_state as build_srr_state

PATROL_PAIR_GUARD_COUNT = 4


def build_patrol_pair_srr(
    guards: list[Guard],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    guard_allowed: dict[str, GuardShiftConstraints | set[str] | None],
    *,
    global_day_offset: int = 0,
    carryover_guard: str | None = None,
) -> tuple[dict, dict]:
    """Assign patrol nights as two fixed pairs with within-pair shift rotation."""
    if len(guards) != PATROL_PAIR_GUARD_COUNT:
        raise ValueError(
            f"Patrol pair mode requires exactly {PATROL_PAIR_GUARD_COUNT} guards, got {len(guards)}"
        )
    if len(shifts) != 2:
        raise ValueError("Patrol pair mode requires exactly two shifts per night")

    ordered_guards = patrol_pair_guard_order(guards, carryover_guard)
    guard_allowed = coerce_guard_shift_constraints_lookup(guard_allowed)
    pairs = patrol_guard_pairs(ordered_guards)
    state = build_srr_state(ordered_guards, shifts)
    evening_shift, morning_shift = shifts

    for day_offset, roster_day in enumerate(roster_days):
        assigned_today: set[str] = set()
        evening_guard, morning_guard = patrol_pair_assignments_for_day(
            day_offset,
            pairs,
            global_day_offset=global_day_offset,
        )
        _assign_patrol_shift(
            assigned_today,
            evening_guard,
            evening_shift,
            guard_allowed,
            ordered_guards,
            roster_day,
            state,
        )
        _assign_patrol_shift(
            assigned_today,
            morning_guard,
            morning_shift,
            guard_allowed,
            ordered_guards,
            roster_day,
            state,
        )

    next_patrol_day_offset = global_day_offset + len(roster_days)
    srr_state = {
        "patrol_pair_mode": True,
        "previous_patrol_day_offset": global_day_offset,
        "rotation_order": [guard.name for guard in ordered_guards],
        "next_patrol_day_offset": next_patrol_day_offset,
    }
    return (
        build_counts_dict(
            ordered_guards,
            state.current_total,
            state.current_shifts,
            state.friday_dinner_counts,
        ),
        srr_state,
    )


def patrol_guard_pairs(guards: list[Guard]) -> list[tuple[Guard, Guard]]:
    return [(guards[0], guards[1]), (guards[2], guards[3])]


def patrol_pair_guard_order(guards: list[Guard], carryover_guard: str | None) -> list[Guard]:
    if not carryover_guard:
        return list(guards)
    names = [guard.name for guard in guards]
    if carryover_guard not in names:
        return list(guards)
    others = [guard for guard in guards if guard.name != carryover_guard]
    carryover = next(guard for guard in guards if guard.name == carryover_guard)
    return others + [carryover]


def patrol_pair_assignments_for_day(
    day_offset: int,
    pairs: list[tuple[Guard, Guard]],
    *,
    global_day_offset: int = 0,
) -> tuple[Guard, Guard]:
    """Return ``(evening_guard, morning_guard)`` for one patrol night."""
    absolute_day = global_day_offset + day_offset
    pair_idx = absolute_day % 2
    swapped = (absolute_day // 2) % 2 == 1
    first, second = pairs[pair_idx]
    if swapped:
        return second, first
    return first, second


def parse_patrol_pair_seed(
    continuity: dict | None,
    guards: list[Guard],
    rules: dict | None,
) -> tuple[int, str | None]:
    """Resolve patrol pair day offset and carryover guard from continuity or config."""
    carryover_guard = (rules or {}).get("carryover_guard")
    config_offset = (rules or {}).get("patrol_day_offset")
    global_day_offset = config_offset if isinstance(config_offset, int) else 0

    if continuity is None:
        return global_day_offset, carryover_guard

    block = continuity.get("srr")
    if not isinstance(block, dict) or not block.get("patrol_pair_mode"):
        return global_day_offset, carryover_guard

    saved_offset = block.get("next_patrol_day_offset")
    if isinstance(saved_offset, int):
        global_day_offset = saved_offset

    saved_carryover = block.get("carryover_guard")
    if isinstance(saved_carryover, str):
        carryover_guard = saved_carryover

    return global_day_offset, carryover_guard


def _assign_patrol_shift(
    assigned_today: set[str],
    default_guard: Guard,
    shift: Shift,
    guard_allowed: dict[str, GuardShiftConstraints],
    guards: list[Guard],
    roster_day: RosterDay,
    state: SrrState,
) -> None:
    specific_candidate = _specific_slot_candidate(
        guards,
        guard_allowed,
        roster_day,
        shift,
        state.current_total,
    )
    candidate = specific_candidate if specific_candidate is not None else default_guard
    if not is_guard_allowed_for_slot(guard_allowed[candidate.name], roster_day.date, shift):
        raise RuntimeError(
            f"Guard {candidate.name} is not allowed for {roster_day.date} shift {shift.label}"
        )
    dinner_state = (False, False, False)
    _record_assignment(assigned_today, dinner_state, roster_day, shift, candidate, state)
