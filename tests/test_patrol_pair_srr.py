import unittest
from datetime import datetime, timedelta

from roster_builder_app.models import Guard, RosterDay, get_hebrew_day_name, patrol_shifts
from roster_builder_app.scheduling.patrol_pair_srr import (
    build_patrol_pair_srr,
    patrol_pair_assignments_for_day,
    patrol_pair_guard_order,
    patrol_guard_pairs,
)
from roster_builder_app.shift_constraints import build_guard_shift_constraints_lookup


def _days(start_date: datetime, count: int) -> list[RosterDay]:
    return [
        RosterDay(
            date=(start_date + timedelta(days=offset)).date(),
            day_name_he=get_hebrew_day_name((start_date + timedelta(days=offset)).date()),
        )
        for offset in range(count)
    ]


class PatrolPairSrrTests(unittest.TestCase):
    def test_pair_assignments_alternate_shifts_within_pair(self) -> None:
        guards = [Guard("A"), Guard("B"), Guard("C"), Guard("D")]
        pairs = patrol_guard_pairs(guards)

        self.assertEqual(
            patrol_pair_assignments_for_day(0, pairs, global_day_offset=0),
            (guards[0], guards[1]),
        )
        self.assertEqual(
            patrol_pair_assignments_for_day(1, pairs, global_day_offset=0),
            (guards[2], guards[3]),
        )
        self.assertEqual(
            patrol_pair_assignments_for_day(2, pairs, global_day_offset=0),
            (guards[1], guards[0]),
        )
        self.assertEqual(
            patrol_pair_assignments_for_day(3, pairs, global_day_offset=0),
            (guards[3], guards[2]),
        )

    def test_carryover_guard_is_moved_to_last_pair_slot(self) -> None:
        guards = [
            Guard("New1"),
            Guard("Carry"),
            Guard("New2"),
            Guard("New3"),
        ]

        ordered = patrol_pair_guard_order(guards, "Carry")

        self.assertEqual([guard.name for guard in ordered], ["New1", "New2", "New3", "Carry"])
        self.assertEqual(
            patrol_guard_pairs(ordered)[1],
            (ordered[2], ordered[3]),
        )

    def test_build_patrol_pair_srr_assigns_four_night_cycle(self) -> None:
        start_date = datetime(2026, 5, 26, 20, 30)
        shifts = patrol_shifts()
        roster_days = _days(start_date, 4)
        guards = [Guard("A"), Guard("B"), Guard("C"), Guard("D")]

        build_patrol_pair_srr(
            guards,
            shifts,
            roster_days,
            build_guard_shift_constraints_lookup(guards),
            global_day_offset=0,
        )

        expected = [
            ("A", "B"),
            ("C", "D"),
            ("B", "A"),
            ("D", "C"),
        ]
        for roster_day, (evening, morning) in zip(roster_days, expected):
            self.assertEqual(roster_day.assignments[shifts[0].label], evening)
            self.assertEqual(roster_day.assignments[shifts[1].label], morning)

    def test_global_day_offset_continues_pair_swap_from_previous_roster(self) -> None:
        guards = [Guard("A"), Guard("B"), Guard("C"), Guard("D")]
        pairs = patrol_guard_pairs(guards)

        self.assertEqual(
            patrol_pair_assignments_for_day(0, pairs, global_day_offset=14),
            (guards[1], guards[0]),
        )


if __name__ == "__main__":
    unittest.main()
