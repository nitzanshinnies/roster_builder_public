"""Guard shift-constraint parsing and slot-eligibility helpers."""

from dataclasses import dataclass
from datetime import date

from models import Guard, Shift


@dataclass(frozen=True)
class GuardShiftConstraints:
    """Shift constraints split into recurring shift starts and exact dated slots."""

    recurring_start_times: set[str] | None
    specific_slots: set[tuple[date, str]]


def build_guard_shift_constraints_lookup(guards: list[Guard]) -> dict[str, GuardShiftConstraints]:
    return {
        guard.name: parse_guard_shift_constraints(guard.allowed_shifts)
        for guard in guards
    }


def coerce_guard_shift_constraints_lookup(
    guard_allowed: dict[str, GuardShiftConstraints | set[str] | None],
) -> dict[str, GuardShiftConstraints]:
    return {
        name: (
            value
            if isinstance(value, GuardShiftConstraints)
            else parse_guard_shift_constraints(value)
        )
        for name, value in guard_allowed.items()
    }


def is_guard_allowed_for_slot(
    constraints: GuardShiftConstraints,
    roster_day_date: date,
    shift: Shift,
) -> bool:
    if matches_specific_slot(constraints, roster_day_date, shift):
        return True
    if constraints.recurring_start_times is None:
        return True
    return shift.start_time in constraints.recurring_start_times


def is_specific_only_guard(constraints: GuardShiftConstraints) -> bool:
    return constraints.recurring_start_times == set() and bool(constraints.specific_slots)


def matches_specific_slot(
    constraints: GuardShiftConstraints,
    roster_day_date: date,
    shift: Shift,
) -> bool:
    shift_names = _slot_shift_names(shift)
    return any(
        slot_date == roster_day_date and shift_name in shift_names
        for slot_date, shift_name in constraints.specific_slots
    )


def parse_guard_shift_constraints(allowed_shifts: list[str] | set[str] | None) -> GuardShiftConstraints:
    if allowed_shifts is None:
        return GuardShiftConstraints(recurring_start_times=None, specific_slots=set())

    recurring_start_times: set[str] = set()
    specific_slots: set[tuple[date, str]] = set()
    for raw in allowed_shifts:
        value = str(raw).strip()
        if not value:
            continue
        specific_slot = _specific_shift_slot(value)
        if specific_slot is not None:
            specific_slots.add(specific_slot)
            continue
        recurring_start_times.add(value)

    return GuardShiftConstraints(
        recurring_start_times=recurring_start_times,
        specific_slots=specific_slots,
    )


def _normalize_shift_name(value: str) -> str:
    """Normalize shift names so config may use either en dash or hyphen separators."""
    return " ".join(value.replace("—", "-").replace("–", "-").split())


def _slot_shift_names(shift: Shift) -> set[str]:
    return {
        _normalize_shift_name(shift.label),
        _normalize_shift_name(shift.start_time),
    }


def _specific_shift_slot(value: str) -> tuple[date, str] | None:
    """Parse ``YYYY-MM-DD <shift name>`` constraints; old time-only entries stay recurring."""
    raw = value.strip()
    if len(raw) <= 10:
        return None
    try:
        slot_date = date.fromisoformat(raw[:10])
    except ValueError:
        return None
    shift_name = raw[10:].strip()
    if not shift_name:
        return None
    return slot_date, _normalize_shift_name(shift_name)
