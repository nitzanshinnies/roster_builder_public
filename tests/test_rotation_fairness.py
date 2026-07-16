import unittest
from datetime import datetime, timedelta

from roster_builder_app.models import Guard, RosterDay, generate_shifts, get_hebrew_day_name, patrol_shifts
from roster_builder_app.scheduling.rotation_fairness import (
    carryover_guard_names,
    entering_guard_names,
    extract_last_assignments,
    resolve_patrol_pair_plan,
    resolve_srr_rotation_seed,
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


class RotationFairnessTests(unittest.TestCase):
    def test_carryover_guard_names_from_continuity(self) -> None:
        guards = [Guard("A"), Guard("B"), Guard("C")]
        continuity = {"guards": ["B", "C", "D"]}
        self.assertEqual(carryover_guard_names(guards, continuity), {"B", "C"})

    def test_patrol_pair_plan_balances_carryover_early_late_history(self) -> None:
        start = datetime(2026, 6, 9, 20, 30)
        shifts = patrol_shifts()
        roster_days = _days(start, 14)
        guards = [
            Guard("Patrol A"),
            Guard("Patrol B"),
            Guard("Patrol C"),
            Guard("Patrol D"),
        ]
        history = {
            "guards": {
                "Patrol A": {"total": 7, "shifts": {"20:30": 4, "02:30": 3}, "friday_dinner": 0},
                "Patrol D": {"total": 7, "shifts": {"20:30": 4, "02:30": 3}, "friday_dinner": 0},
            }
        }
        continuity = {
            "next_roster_start": start.isoformat(),
            "algorithm": "srr",
            "shift_duration_hours": 6,
            "first_shift_start": "20:30",
            "guards": ["Patrol A", "Patrol D", "Patrol B", "Patrol C"],
            "roster_length_days": 14,
            "srr": {
                "patrol_pair_mode": True,
                "next_patrol_day_offset": 28,
                "last_assignments": {
                    "Patrol A": {"date": "2026-06-07", "start_time": "20:30"},
                    "Patrol D": {"date": "2026-06-08", "start_time": "20:30"},
                },
            },
        }
        rules = {"carryover_guard": "Patrol D"}
        guard_allowed = build_guard_shift_constraints_lookup(guards)

        ordered, offset, carryover, report = resolve_patrol_pair_plan(
            guards,
            shifts,
            roster_days,
            guard_allowed,
            history,
            continuity,
            rules,
            roster_start=start,
            shift_duration_hours=6,
        )

        self.assertEqual(offset, 28)
        self.assertEqual(carryover, "Patrol D")
        self.assertEqual([guard.name for guard in ordered], [
            "Patrol B",
            "Patrol A",
            "Patrol C",
            "Patrol D",
        ])
        by_name = {row["name"]: row for row in report["carryovers"]}
        self.assertEqual(by_name["Patrol A"]["projected_spread"], 0)
        self.assertEqual(by_name["Patrol D"]["projected_spread"], 0)

    def test_patrol_pair_plan_puts_entering_guards_on_first_night_when_roster_changes(self) -> None:
        start = datetime(2026, 6, 23, 20, 30)
        shifts = patrol_shifts()
        roster_days = _days(start, 30)
        guards = [
            Guard("Patrol W"),
            Guard("Patrol X"),
            Guard("Patrol Y"),
            Guard("Patrol Z"),
        ]
        history = {
            "guards": {
                "Patrol Z": {"total": 18, "shifts": {"20:30": 8, "02:30": 10}, "friday_dinner": 0},
                "Patrol Y": {"total": 7, "shifts": {"20:30": 4, "02:30": 3}, "friday_dinner": 0},
            }
        }
        continuity = {
            "next_roster_start": start.isoformat(),
            "algorithm": "srr",
            "shift_duration_hours": 6,
            "first_shift_start": "20:30",
            "guards": ["Patrol Y", "Patrol B", "Patrol A", "Patrol Z"],
            "roster_length_days": 14,
            "srr": {
                "patrol_pair_mode": True,
                "next_patrol_day_offset": 42,
                "carryover_guard": "Patrol Z",
                "last_assignments": {
                    "Patrol Y": {"date": "2026-06-22", "start_time": "20:30"},
                    "Patrol Z": {"date": "2026-06-23", "start_time": "02:30"},
                },
            },
        }
        rules = {"carryover_guard": "Patrol Z"}
        guard_allowed = build_guard_shift_constraints_lookup(guards)

        ordered, offset, carryover, _report = resolve_patrol_pair_plan(
            guards,
            shifts,
            roster_days,
            guard_allowed,
            history,
            continuity,
            rules,
            roster_start=start,
            shift_duration_hours=6,
        )

        self.assertEqual(entering_guard_names(guards, continuity), {"Patrol W", "Patrol X"})
        self.assertEqual(carryover, "Patrol Z")
        self.assertEqual(offset % 2, 0)
        self.assertEqual({guard.name for guard in ordered[0:2]}, {"Patrol W", "Patrol X"})

        from roster_builder_app.scheduling.patrol_pair_srr import (
            patrol_guard_pairs,
            patrol_pair_assignments_for_day,
            patrol_pair_guard_order,
        )

        pair_order = patrol_pair_guard_order(ordered, carryover)
        evening_guard, morning_guard = patrol_pair_assignments_for_day(
            0,
            patrol_guard_pairs(pair_order),
            global_day_offset=offset,
        )
        self.assertIn(evening_guard.name, {"Patrol W", "Patrol X"})
        self.assertIn(morning_guard.name, {"Patrol W", "Patrol X"})
        self.assertNotIn(evening_guard.name, carryover_guard_names(guards, continuity))

    def test_guard_srr_seed_picks_fairer_rotation_index_for_carryover(self) -> None:
        start = datetime(2026, 6, 9, 6, 0)
        shift_duration = 4
        shifts = generate_shifts(start.hour, shift_duration)
        roster_days = _days(start, 7)
        guards = [Guard("A"), Guard("B"), Guard("C"), Guard("D")]
        history = {
            "guards": {
                "A": {
                    "total": 12,
                    "shifts": {"06:00": 4, "10:00": 1, "14:00": 1, "18:00": 1, "22:00": 1, "02:00": 4},
                    "friday_dinner": 0,
                }
            }
        }
        continuity = {
            "next_roster_start": start.isoformat(),
            "algorithm": "srr",
            "shift_duration_hours": shift_duration,
            "first_shift_start": shifts[0].start_time,
            "guards": ["A", "B", "C", "D"],
            "roster_length_days": 7,
            "srr": {
                "rotation_order": ["A", "B", "C", "D"],
                "next_rotation_index": 0,
                "last_assignments": {
                    "A": {"date": "2026-06-08", "start_time": "22:00"},
                },
            },
        }
        guard_allowed = build_guard_shift_constraints_lookup(guards)
        order, idx, report = resolve_srr_rotation_seed(
            guards,
            shifts,
            roster_days,
            guard_allowed,
            history,
            continuity,
            rules=None,
            patrol=False,
            rotation_start=None,
            roster_start=start,
            shift_duration_hours=shift_duration,
        )

        self.assertEqual([guard.name for guard in order], ["A", "B", "C", "D"])
        self.assertIn(idx, {0, 1})
        carryover_rows = {row["name"]: row for row in report["carryovers"]}
        self.assertIn("A", carryover_rows)
        self.assertGreaterEqual(carryover_rows["A"]["projected_spread"], 0)

    def test_extract_last_assignments_from_roster(self) -> None:
        from roster_builder_app.models import Roster

        start = datetime(2026, 6, 9, 20, 30)
        shifts = patrol_shifts()
        day = RosterDay(date=start.date(), day_name_he="שלישי")
        day.assignments = {
            shifts[0].label: "A",
            shifts[1].label: "B",
        }
        roster = Roster(days=[day], shifts=shifts, guards=[Guard("A"), Guard("B")], start_date=start)
        last = extract_last_assignments(roster, 6)
        self.assertEqual(last["A"]["start_time"], "20:30")
        self.assertEqual(last["B"]["start_time"], "02:30")


if __name__ == "__main__":
    unittest.main()
