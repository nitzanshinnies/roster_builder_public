"""Roster table HTML rendering."""

from roster_builder_app.models import Roster

from .html_page import html_document
from .styles import ROSTER_STYLE


def render_roster_html(roster: Roster, patrol: bool = False) -> str:
    """Render the roster as an RTL Hebrew HTML table."""
    roster_title = "רשימת פטרולים" if patrol else "רשימת שמירה"
    days = roster.days
    title = f"{roster_title} – {days[0].date:%d/%m} עד {days[-1].date:%d/%m}"
    body = "\n".join(
        [
            f'    <h1>{roster_title} – {days[0].date:%d/%m/%Y} עד {days[-1].date:%d/%m/%Y}</h1>',
            "    <table>",
            _roster_head(roster),
            _roster_body(roster),
            "    </table>",
            "",
        ]
    )
    return html_document(title, ROSTER_STYLE, body)


def _roster_body(roster: Roster) -> str:
    rows = ["        <tbody>"]
    for shift in roster.shifts:
        shift_display = f"{shift.start_time}<br>–<br>{shift.end_time}"
        rows.append("            <tr>")
        rows.append(f'                <td class="shift-label">{shift_display}</td>')
        for day in roster.days:
            guard_name = day.assignments.get(shift.label, "")
            rows.append(f"                <td>{guard_name}</td>")
        rows.append("            </tr>")
    rows.append("        </tbody>")
    return "\n".join(rows)


def _roster_head(roster: Roster) -> str:
    rows = [
        "        <thead>",
        "            <tr>",
        "                <th>משמרת</th>",
    ]
    for day in roster.days:
        rows.append(f'                <th>{day.day_name_he}<span class="date">({day.date:%d/%m})</span></th>')
    rows.extend(
        [
            "            </tr>",
            "        </thead>",
        ]
    )
    return "\n".join(rows)
