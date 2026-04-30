import unittest
from datetime import datetime, timedelta

from models import Guard, RosterDay, generate_shifts, get_hebrew_day_name, patrol_shifts
from scheduling.srr import build_srr
from shift_constraints import build_guard_shift_constraints_lookup


def _days(start_date: datetime, count: int) -> list[RosterDay]:
    return [
        RosterDay(
            date=(start_date + timedelta(days=offset)).date(),
            day_name_he=get_hebrew_day_name((start_date + timedelta(days=offset)).date()),
        )
        for offset in range(count)
    ]


def _assignments_by_slot(roster_days: list[RosterDay], shifts) -> list[str]:
    return [
        roster_day.assignments[shift.label]
        for roster_day in roster_days
        for shift in shifts
    ]


class SrrSpecificShiftTests(unittest.TestCase):
    def test_guard_specific_shift_is_inserted_without_advancing_regular_cycle(self) -> None:
        start_date = datetime(2026, 5, 4, 6, 0)
        shifts = generate_shifts(start_date.hour, 4)
        roster_days = _days(start_date, 1)
        guards = [
            Guard("A"),
            Guard("B"),
            Guard("C"),
            Guard("D"),
            Guard("E", allowed_shifts=["2026-05-04 14:00 – 18:00"]),
        ]

        build_srr(
            guards,
            shifts,
            roster_days,
            history={},
            guard_allowed=build_guard_shift_constraints_lookup(guards),
            srr_seed=(guards, 0),
        )

        self.assertEqual(_assignments_by_slot(roster_days, shifts), ["A", "B", "E", "C", "D", "A"])

    def test_patrol_specific_shift_is_inserted_without_advancing_regular_cycle(self) -> None:
        start_date = datetime(2026, 5, 1, 20, 30)
        shifts = patrol_shifts()
        roster_days = _days(start_date, 3)
        guards = [
            Guard("A"),
            Guard("B"),
            Guard("C"),
            Guard("D"),
            Guard("E", allowed_shifts=["2026-05-02 20:30 – 02:30"]),
        ]

        build_srr(
            guards,
            shifts,
            roster_days,
            history={},
            guard_allowed=build_guard_shift_constraints_lookup(guards),
            srr_seed=(guards, 0),
            patrol=True,
        )

        self.assertEqual(_assignments_by_slot(roster_days, shifts), ["A", "B", "E", "C", "D", "A"])


if __name__ == "__main__":
    unittest.main()
