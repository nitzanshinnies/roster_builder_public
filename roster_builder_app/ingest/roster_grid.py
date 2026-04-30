"""Roster grid replay utilities."""

from datetime import datetime, timedelta

from roster_builder_app.models import RosterDay, get_hebrew_day_name


def fresh_roster_days(start_date: datetime, roster_length: int) -> list[RosterDay]:
    days = []
    for day_offset in range(roster_length):
        day_date = (start_date + timedelta(days=day_offset)).date()
        days.append(RosterDay(date=day_date, day_name_he=get_hebrew_day_name(day_date)))
    return days


def grid_matches(roster_days: list[RosterDay], shifts: list, expected: list[list[str]]) -> bool:
    for shift_index, shift in enumerate(shifts):
        row = expected[shift_index]
        for day_index, roster_day in enumerate(roster_days):
            if roster_day.assignments.get(shift.label) != row[day_index]:
                return False
    return True
