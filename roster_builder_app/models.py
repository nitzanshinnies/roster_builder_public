"""Data models for the roster builder."""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta


# Hebrew day names (Sunday=0 in isoweekday is 7, Monday=1)
HEBREW_DAY_NAMES = {
    1: "שני",
    2: "שלישי",
    3: "רביעי",
    4: "חמישי",
    5: "שישי",
    6: "שבת",
    7: "ראשון",
}


@dataclass
class Guard:
    """A guard with optional shift constraints."""
    name: str
    allowed_shifts: list[str] | None = None  # None = all shifts allowed


@dataclass
class Shift:
    """A shift time slot definition."""
    start_time: str   # "06:00"
    end_time: str     # "10:00"
    label: str        # "06:00 – 10:00"

    def __hash__(self):
        return hash(self.label)

    def __eq__(self, other):
        if not isinstance(other, Shift):
            return False
        return self.label == other.label


@dataclass
class RosterDay:
    """A single day in the roster with guard assignments per shift."""
    date: date
    day_name_he: str                          # "שני", "שלישי", etc.
    assignments: dict[str, str] = field(default_factory=dict)  # shift_label -> guard_name


@dataclass
class Roster:
    """The complete roster."""
    days: list[RosterDay]
    shifts: list[Shift]       # ordered shift definitions
    guards: list[Guard]
    start_date: datetime


def patrol_shifts() -> list[Shift]:
    """Two overnight patrol slots: 20:30–02:30, then 02:30–08:30 (next morning)."""
    return [
        Shift(start_time="20:30", end_time="02:30", label="20:30 – 02:30"),
        Shift(start_time="02:30", end_time="08:30", label="02:30 – 08:30"),
    ]


PATROL_SHIFT_DURATION_HOURS = 6


def generate_shifts(start_hour: int, duration_hours: int) -> list[Shift]:
    """Generate shift definitions for a day.

    A day starts at start_hour and contains 24/duration_hours shifts.
    E.g. start_hour=6, duration=4 produces:
      06:00–10:00, 10:00–14:00, 14:00–18:00, 18:00–22:00, 22:00–02:00, 02:00–06:00
    """
    if 24 % duration_hours != 0:
        raise ValueError(f"Shift duration {duration_hours} does not divide evenly into 24 hours")

    shifts = []
    num_shifts = 24 // duration_hours
    for i in range(num_shifts):
        hour = (start_hour + i * duration_hours) % 24
        end_hour = (hour + duration_hours) % 24
        start_str = f"{hour:02d}:00"
        end_str = f"{end_hour:02d}:00"
        label = f"{start_str} – {end_str}"
        shifts.append(Shift(start_time=start_str, end_time=end_str, label=label))
    return shifts


def get_hebrew_day_name(d: date) -> str:
    """Return the Hebrew day name for a given date."""
    return HEBREW_DAY_NAMES[d.isoweekday()]
