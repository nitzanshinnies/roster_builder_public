"""SRR mutable scheduling state."""

from dataclasses import dataclass

from models import Guard, Shift


@dataclass
class SrrState:
    assigned_friday_shabbat_dinner: set[str]
    assigned_holiday_dinner: set[str]
    current_shifts: dict[str, dict[str, int]]
    current_total: dict[str, int]
    friday_dinner_counts: dict[str, int]


def srr_state(guards: list[Guard], shifts: list[Shift]) -> SrrState:
    return SrrState(
        assigned_friday_shabbat_dinner=set(),
        assigned_holiday_dinner=set(),
        current_shifts={guard.name: {shift.start_time: 0 for shift in shifts} for guard in guards},
        current_total={guard.name: 0 for guard in guards},
        friday_dinner_counts={guard.name: 0 for guard in guards},
    )
