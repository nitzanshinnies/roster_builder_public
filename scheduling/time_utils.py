"""Datetime helpers for roster slots."""

from datetime import datetime, timedelta


def hhmm_parts(t: str) -> tuple[int, int]:
    parts = t.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return hour, minute


def shift_datetime(
    roster_anchor: datetime,
    day_offset: int,
    shift_start_time: str,
    first_shift_time: str,
) -> datetime:
    """Calculate datetime for a shift slot."""
    hour, minute = hhmm_parts(shift_start_time)
    first_hour, first_minute = hhmm_parts(first_shift_time)
    slot = roster_anchor + timedelta(days=day_offset)
    if (hour, minute) < (first_hour, first_minute):
        slot += timedelta(days=1)
    return slot.replace(hour=hour, minute=minute, second=0, microsecond=0)
