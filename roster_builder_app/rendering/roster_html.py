"""Roster table HTML rendering."""

from roster_builder_app.models import Roster, RosterDay, Shift

from .html_page import html_document
from .styles import ROSTER_STYLE

ROSTER_TABLE_MAX_DAYS = 14


def roster_table_count(day_count: int) -> int:
    """Number of HTML tables needed when each holds at most 14 days."""
    if day_count <= 0:
        return 0
    if day_count <= ROSTER_TABLE_MAX_DAYS:
        return 1
    return (day_count + ROSTER_TABLE_MAX_DAYS - 1) // ROSTER_TABLE_MAX_DAYS


def _roster_day_chunks(days: list[RosterDay]) -> list[list[RosterDay]]:
    if not days:
        return []
    return [
        days[start : start + ROSTER_TABLE_MAX_DAYS]
        for start in range(0, len(days), ROSTER_TABLE_MAX_DAYS)
    ]


def render_roster_html(roster: Roster, patrol: bool = False) -> str:
    """Render the roster as an RTL Hebrew HTML table (split every 14 days)."""
    roster_title = "רשימת פטרולים" if patrol else "רשימת שמירה"
    days = roster.days
    doc_title = f"{roster_title} – {days[0].date:%d/%m} עד {days[-1].date:%d/%m}"
    body_parts: list[str] = []
    for index, day_chunk in enumerate(_roster_day_chunks(days)):
        chunk_title = f"{roster_title} – {day_chunk[0].date:%d/%m/%Y} עד {day_chunk[-1].date:%d/%m/%Y}"
        if index > 0:
            body_parts.append("")
        body_parts.extend(
            [
                f"    <h1>{chunk_title}</h1>",
                "    <table>",
                _roster_head(day_chunk),
                _roster_body(roster.shifts, day_chunk),
                "    </table>",
            ]
        )
    return html_document(doc_title, ROSTER_STYLE, "\n".join(body_parts) + "\n")


def _roster_body(shifts: list[Shift], days: list[RosterDay]) -> str:
    rows = ["        <tbody>"]
    for shift in shifts:
        shift_display = f"{shift.start_time}<br>–<br>{shift.end_time}"
        rows.append("            <tr>")
        rows.append(f'                <td class="shift-label">{shift_display}</td>')
        for day in days:
            guard_name = day.assignments.get(shift.label, "")
            rows.append(f"                <td>{guard_name}</td>")
        rows.append("            </tr>")
    rows.append("        </tbody>")
    return "\n".join(rows)


def _roster_head(days: list[RosterDay]) -> str:
    rows = [
        "        <thead>",
        "            <tr>",
        "                <th>משמרת</th>",
    ]
    for day in days:
        rows.append(f'                <th>{day.day_name_he}<span class="date">({day.date:%d/%m})</span></th>')
    rows.extend(
        [
            "            </tr>",
            "        </thead>",
        ]
    )
    return "\n".join(rows)
