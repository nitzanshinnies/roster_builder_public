import unittest
from datetime import date

from models import Guard, Shift
from shift_constraints import (
    build_guard_shift_constraints_lookup,
    is_guard_allowed_for_slot,
    is_specific_only_guard,
    matches_specific_slot,
    parse_guard_shift_constraints,
)


class ShiftConstraintTests(unittest.TestCase):
    def test_dated_constraint_matches_label_or_start_time(self) -> None:
        shift = Shift(start_time="20:30", end_time="02:30", label="20:30 – 02:30")
        constraints = parse_guard_shift_constraints(
            {
                "2026-05-02 20:30 - 02:30",
                "2026-05-04 20:30",
            }
        )

        self.assertTrue(matches_specific_slot(constraints, date(2026, 5, 2), shift))
        self.assertTrue(matches_specific_slot(constraints, date(2026, 5, 4), shift))
        self.assertFalse(matches_specific_slot(constraints, date(2026, 5, 3), shift))

    def test_lookup_builds_constraints_by_guard_name(self) -> None:
        guards = [
            Guard("A"),
            Guard("B", allowed_shifts=["06:00"]),
        ]

        lookup = build_guard_shift_constraints_lookup(guards)

        self.assertIsNone(lookup["A"].recurring_start_times)
        self.assertEqual(lookup["B"].recurring_start_times, {"06:00"})

    def test_specific_only_guard_is_not_allowed_elsewhere(self) -> None:
        shift = Shift(start_time="20:30", end_time="02:30", label="20:30 – 02:30")
        constraints = parse_guard_shift_constraints({"2026-05-02 20:30 – 02:30"})

        self.assertTrue(is_specific_only_guard(constraints))
        self.assertTrue(is_guard_allowed_for_slot(constraints, date(2026, 5, 2), shift))
        self.assertFalse(is_guard_allowed_for_slot(constraints, date(2026, 5, 3), shift))


if __name__ == "__main__":
    unittest.main()
