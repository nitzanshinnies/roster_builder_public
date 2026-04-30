"""SRR slot assignment helpers."""

from models import Guard, RosterDay, Shift
from shift_constraints import GuardShiftConstraints, matches_specific_slot

from .dinner import dinner_state
from .srr_candidates import srr_candidate_allowed
from .srr_rotation import rotation_candidates
from .srr_state import SrrState


def assign_srr_slot(
    assigned_today: set[str],
    guard_allowed: dict[str, GuardShiftConstraints],
    guards: list[Guard],
    holiday_slots: set,
    roster_day: RosterDay,
    rotation_idx: int,
    rotation_order: list[Guard],
    shabbat_dinner_key: tuple[int, str] | None,
    shabbat_observers: set[str],
    shabbat_shift_keys: set[tuple[int, str]],
    shift: Shift,
    state: SrrState,
) -> int:
    current_dinner_state = dinner_state(roster_day, shift, shabbat_dinner_key, holiday_slots)
    specific_candidate = _specific_slot_candidate(
        guards,
        guard_allowed,
        roster_day,
        shift,
        state.current_total,
    )
    if specific_candidate is not None:
        _record_assignment(assigned_today, current_dinner_state, roster_day, shift, specific_candidate, state)
        return rotation_idx

    next_idx = _assign_from_rotation(
        assigned_today,
        current_dinner_state,
        guard_allowed,
        roster_day,
        rotation_idx,
        rotation_order,
        shabbat_observers,
        shabbat_shift_keys,
        shift,
        state,
        require_new_guard_today=True,
    )
    if next_idx is not None:
        return next_idx
    next_idx = _assign_from_rotation(
        assigned_today,
        current_dinner_state,
        guard_allowed,
        roster_day,
        rotation_idx,
        rotation_order,
        shabbat_observers,
        shabbat_shift_keys,
        shift,
        state,
        require_new_guard_today=False,
    )
    if next_idx is not None:
        return next_idx
    raise RuntimeError(
        f"No candidate for {roster_day.day_name_he} {roster_day.date} "
        f"shift {shift.label}. Constraints too restrictive."
    )


def _assign_from_rotation(
    assigned_today: set[str],
    dinner_state: tuple[bool, bool, bool],
    guard_allowed: dict[str, GuardShiftConstraints],
    roster_day: RosterDay,
    rotation_idx: int,
    rotation_order: list[Guard],
    shabbat_observers: set[str],
    shabbat_shift_keys: set[tuple[int, str]],
    shift: Shift,
    state: SrrState,
    *,
    require_new_guard_today: bool,
) -> int | None:
    for attempt, candidate in enumerate(rotation_candidates(rotation_order, rotation_idx)):
        if not srr_candidate_allowed(
            state.assigned_friday_shabbat_dinner,
            state.assigned_holiday_dinner,
            assigned_today,
            candidate,
            dinner_state,
            guard_allowed,
            require_new_guard_today,
            roster_day,
            shabbat_observers,
            shabbat_shift_keys,
            shift,
        ):
            continue
        _record_assignment(assigned_today, dinner_state, roster_day, shift, candidate, state)
        return (rotation_idx + attempt + 1) % len(rotation_order)
    return None


def _record_assignment(
    assigned_today: set[str],
    dinner_state: tuple[bool, bool, bool],
    roster_day: RosterDay,
    shift: Shift,
    candidate: Guard,
    state: SrrState,
) -> None:
    is_exclusive_dinner, is_sd, is_hd = dinner_state
    roster_day.assignments[shift.label] = candidate.name
    assigned_today.add(candidate.name)
    state.current_total[candidate.name] += 1
    state.current_shifts[candidate.name][shift.start_time] += 1
    if is_exclusive_dinner:
        state.friday_dinner_counts[candidate.name] += 1
    if is_sd:
        state.assigned_friday_shabbat_dinner.add(candidate.name)
    if is_hd:
        state.assigned_holiday_dinner.add(candidate.name)


def _specific_slot_candidate(
    guards: list[Guard],
    guard_allowed: dict[str, GuardShiftConstraints],
    roster_day: RosterDay,
    shift: Shift,
    current_total: dict[str, int],
) -> Guard | None:
    candidates = [
        guard
        for guard in guards
        if matches_specific_slot(guard_allowed[guard.name], roster_day.date, shift)
    ]
    if not candidates:
        return None
    guard_order = {guard.name: index for index, guard in enumerate(guards)}
    return min(candidates, key=lambda guard: (current_total[guard.name], guard_order[guard.name]))
