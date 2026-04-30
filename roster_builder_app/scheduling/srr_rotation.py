"""SRR rotation ordering helpers."""

import random

from roster_builder_app.history_manager import get_guard_history
from roster_builder_app.models import Guard
from roster_builder_app.shift_constraints import GuardShiftConstraints, is_specific_only_guard


def regular_srr_rotation(
    rotation_order: list[Guard],
    rotation_idx: int,
    guard_allowed: dict[str, GuardShiftConstraints],
) -> tuple[list[Guard], int]:
    """Remove exact-slot-only guards from the normal cycle while preserving the next regular guard."""
    if not rotation_order:
        return [], 0

    regular_order = [
        guard
        for guard in rotation_order
        if not is_specific_only_guard(guard_allowed[guard.name])
    ]
    if len(regular_order) == len(rotation_order):
        return rotation_order, rotation_idx
    if not regular_order:
        return [], 0

    next_regular_name = next_regular_guard_name(rotation_order, rotation_idx, regular_order)
    if next_regular_name is None:
        return regular_order, 0
    regular_names = [guard.name for guard in regular_order]
    return regular_order, regular_names.index(next_regular_name)


def rotation_candidates(rotation_order: list[Guard], rotation_idx: int) -> list[Guard]:
    return [
        rotation_order[(rotation_idx + attempt) % len(rotation_order)]
        for attempt in range(len(rotation_order))
    ]


def rotation_order_list(guards: list[Guard], rotation_start: str | None) -> list[Guard]:
    """Place ``rotation_start`` first; keep relative order of the rest."""
    if not rotation_start:
        return list(guards)
    names = [guard.name for guard in guards]
    if rotation_start not in names:
        return list(guards)
    index = names.index(rotation_start)
    return guards[index:] + guards[:index]


def srr_rotation_seed(
    guards: list[Guard],
    history: dict,
    patrol: bool,
    rotation_start: str | None,
    srr_seed: tuple[list[Guard], int] | None,
) -> tuple[list[Guard], int]:
    if srr_seed is not None:
        return srr_seed
    if patrol:
        return rotation_order_list(guards, rotation_start), 0

    def hist_sort_key(guard: Guard) -> tuple:
        guard_history = get_guard_history(history, guard.name)
        return guard_history["total"], random.random()

    return sorted(guards, key=hist_sort_key), 0


def next_regular_guard_name(
    rotation_order: list[Guard],
    rotation_idx: int,
    regular_order: list[Guard],
) -> str | None:
    regular_names = {guard.name for guard in regular_order}
    for candidate in rotation_candidates(rotation_order, rotation_idx):
        if candidate.name in regular_names:
            return candidate.name
    return None
