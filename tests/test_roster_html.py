import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from roster_builder_app.ingest.html_parser import parse_roster_html
from roster_builder_app.models import Guard, Roster, RosterDay, get_hebrew_day_name, patrol_shifts
from roster_builder_app.rendering.roster_html import render_roster_html, roster_table_count


def _roster_for_days(day_count: int, *, patrol: bool = True) -> Roster:
    start = datetime(2026, 6, 23, 20, 30)
    shifts = patrol_shifts()
    guards = [Guard("A"), Guard("B")]
    days: list[RosterDay] = []
    for offset in range(day_count):
        day_date = (start + timedelta(days=offset)).date()
        roster_day = RosterDay(date=day_date, day_name_he=get_hebrew_day_name(day_date))
        for shift in shifts:
            roster_day.assignments[shift.label] = guards[offset % 2].name
        days.append(roster_day)
    return Roster(days=days, shifts=shifts, guards=guards, start_date=start)


class RosterHtmlTests(unittest.TestCase):
    def test_roster_table_count(self) -> None:
        self.assertEqual(roster_table_count(14), 1)
        self.assertEqual(roster_table_count(15), 2)
        self.assertEqual(roster_table_count(30), 3)

    def test_single_table_when_at_most_14_days(self) -> None:
        html = render_roster_html(_roster_for_days(14))
        self.assertEqual(html.count("<table>"), 1)
        self.assertEqual(html.count("<h1>"), 1)
        self.assertIn("23/06/2026 עד 06/07/2026", html)

    def test_splits_into_multiple_tables_when_longer_than_14_days(self) -> None:
        html = render_roster_html(_roster_for_days(30))
        self.assertEqual(html.count("<table>"), 3)
        self.assertEqual(html.count("<h1>"), 3)
        self.assertIn("23/06/2026 עד 06/07/2026", html)
        self.assertIn("07/07/2026 עד 20/07/2026", html)
        self.assertIn("21/07/2026 עד 22/07/2026", html)

    def test_each_table_has_at_most_14_day_columns(self) -> None:
        html = render_roster_html(_roster_for_days(30))
        for thead in html.split("<thead>")[1:]:
            header_block = thead.split("</thead>", 1)[0]
            self.assertLessEqual(header_block.count('class="date"'), 14)

    def test_parse_roster_html_reads_split_tables(self) -> None:
        roster = _roster_for_days(30)
        html = render_roster_html(roster)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "roster.html"
            path.write_text(html, encoding="utf-8")
            start, length, grid = parse_roster_html(path)
        self.assertEqual(length, 30)
        self.assertEqual(start.date(), roster.start_date.date())
        self.assertEqual(len(grid), len(roster.shifts))
        self.assertEqual(len(grid[0]), 30)


if __name__ == "__main__":
    unittest.main()
