"""Simple round-robin scheduler."""

from roster_builder_app.models import Guard, RosterDay, Shift
from roster_builder_app.shift_constraints import (
    GuardShiftConstraints,
    coerce_guard_shift_constraints_lookup,
)

from .counts import build_counts_dict
from .rules import holiday_dinner_slots, shabbat_rules
from .srr_assignment import assign_srr_slot
from .srr_rotation import (
    regular_srr_rotation,
    rotation_order_list,
    srr_rotation_seed,
)
from .srr_state import srr_state as build_srr_state


def build_srr(
    guards: list[Guard],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    history: dict,
    guard_allowed: dict[str, GuardShiftConstraints | set[str] | None],
    rules: dict | None = None,
    srr_seed: tuple[list[Guard], int] | None = None,
    patrol: bool = False,
    rotation_start: str | None = None,
) -> tuple[dict, dict]:
    """Simple round-robin with constraints, one-per-day preference, and dinner accounting."""
    guard_allowed = coerce_guard_shift_constraints_lookup(guard_allowed)
    rotation_order, rotation_idx = srr_rotation_seed(
        guards,
        history,
        patrol,
        rotation_start,
        srr_seed,
    )
    rotation_order, rotation_idx = regular_srr_rotation(
        rotation_order,
        rotation_idx,
        guard_allowed,
    )

    shabbat_observers, shabbat_shift_keys, shabbat_dinner_key = shabbat_rules(rules)
    holiday_slots = holiday_dinner_slots(rules)
    state = build_srr_state(guards, shifts)

    for roster_day in roster_days:
        assigned_today: set[str] = set()
        for shift in shifts:
            rotation_idx = assign_srr_slot(
                assigned_today,
                guard_allowed,
                guards,
                holiday_slots,
                roster_day,
                rotation_idx,
                rotation_order,
                shabbat_dinner_key,
                shabbat_observers,
                shabbat_shift_keys,
                shift,
                state,
            )

    srr_state = {
        "rotation_order": [guard.name for guard in rotation_order],
        "next_rotation_index": rotation_idx,
    }
    return (
        build_counts_dict(
            guards,
            state.current_total,
            state.current_shifts,
            state.friday_dinner_counts,
        ),
        srr_state,
    )



