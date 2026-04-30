"""Dinner-shift state helpers."""

from roster_builder_app.models import RosterDay, Shift

from .rules import is_exclusive_dinner_slot, is_holiday_dinner_only, is_shabbat_dinner_only


def dinner_state(
    roster_day: RosterDay,
    shift: Shift,
    shabbat_dinner_key: tuple[int, str] | None,
    holiday_slots: set,
) -> tuple[bool, bool, bool]:
    return (
        is_exclusive_dinner_slot(
            roster_day.date,
            shift.start_time,
            shabbat_dinner_key,
            holiday_slots,
        ),
        is_shabbat_dinner_only(roster_day.date, shift.start_time, shabbat_dinner_key),
        is_holiday_dinner_only(roster_day.date, shift.start_time, holiday_slots),
    )
