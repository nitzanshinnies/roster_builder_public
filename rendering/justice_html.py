"""Justice table HTML rendering."""

from models import Roster
from scheduling.counts import compute_min_rest_per_guard

from .html_page import html_document
from .justice_counts import build_cumulative_counts, has_history_counts, highlight_class, total_range
from .styles import JUSTICE_STYLE


def render_justice_html(
    roster: Roster,
    current_counts: dict,
    history: dict,
    shift_duration_hours: int,
) -> str:
    """Render the justice/fairness table as an RTL Hebrew HTML page."""
    min_rest = compute_min_rest_per_guard(roster, shift_duration_hours)
    body_parts = [
        "    <h1>טבלת צדק</h1>",
        f"    <h2>תקופה: {roster.days[0].date:%d/%m/%Y} – {roster.days[-1].date:%d/%m/%Y}</h2>",
        _current_table(roster, current_counts, min_rest),
    ]
    if has_history_counts(roster.guards, history):
        cumulative = build_cumulative_counts(roster.guards, roster.shifts, current_counts, history)
        body_parts.append(_cumulative_table(roster, cumulative))
    body_parts.append("")
    title = f"טבלת צדק – {roster.days[0].date:%d/%m} עד {roster.days[-1].date:%d/%m}"
    return html_document(title, JUSTICE_STYLE, "\n".join(body_parts))


def _cumulative_table(roster: Roster, cumulative: dict) -> str:
    rows = [
        "    <h2>מצטבר (כולל היסטוריה)</h2>",
        "    <table>",
        _justice_header(roster, include_min_rest=False),
        "        <tbody>",
    ]
    max_total, min_total = total_range([cumulative[guard.name] for guard in roster.guards])
    for guard in roster.guards:
        cum = cumulative[guard.name]
        rows.extend(_guard_count_cells(roster, guard.name, cum, max_total, min_total))
    rows.extend(["        </tbody>", "    </table>"])
    return "\n".join(rows)


def _current_table(roster: Roster, current_counts: dict, min_rest: dict) -> str:
    rows = [
        "    <table>",
        _justice_header(roster, include_min_rest=True),
        "        <tbody>",
    ]
    max_total, min_total = total_range([current_counts[guard.name] for guard in roster.guards])
    for guard in roster.guards:
        curr = current_counts[guard.name]
        rows.extend(_guard_count_cells(roster, guard.name, curr, max_total, min_total))
        rows.append(_min_rest_cell(min_rest.get(guard.name)))
        rows.append("            </tr>")
    rows.extend(["        </tbody>", "    </table>"])
    return "\n".join(rows)


def _guard_count_cells(
    roster: Roster,
    guard_name: str,
    counts: dict,
    max_total: int,
    min_total: int,
) -> list[str]:
    rows = ["            <tr>", f'                <td class="guard-name">{guard_name}</td>']
    for shift in roster.shifts:
        rows.append(f'                <td>{counts["shifts"].get(shift.start_time, 0)}</td>')
    rows.append(f'                <td>{counts.get("friday_dinner", 0)}</td>')
    total = counts["total"]
    total_class = highlight_class(total, max_total, min_total)
    rows.append(f'                <td class="total"><span{total_class}>{total}</span></td>')
    return rows


def _justice_header(roster: Roster, *, include_min_rest: bool) -> str:
    rows = [
        "        <thead>",
        "            <tr>",
        "                <th>שומר</th>",
    ]
    for shift in roster.shifts:
        rows.append(f"                <th>{shift.start_time}</th>")
    rows.append("                <th>שישי ערב</th>")
    rows.append("                <th>סה״כ</th>")
    if include_min_rest:
        rows.append("                <th>מנוחה מינימלית (שעות)</th>")
    rows.extend(["            </tr>", "        </thead>"])
    return "\n".join(rows)


def _min_rest_cell(rest_val: float | None) -> str:
    if rest_val is None:
        return '                <td class="min-rest">—</td>'
    rest_class = "rest-ok" if rest_val >= 8 else "rest-warn"
    return f'                <td class="min-rest {rest_class}">{rest_val:.0f}</td>'
