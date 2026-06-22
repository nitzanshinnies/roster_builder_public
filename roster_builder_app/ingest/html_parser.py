"""Parse generated roster HTML files."""

import re
from datetime import date, datetime
from pathlib import Path

_TAG_RE = re.compile(r"<[^>]+>")


def parse_roster_html(path: Path) -> tuple[datetime, int, list[list[str]]]:
    """Return start date, roster length, and grid[shift_i][day_j]."""
    raw = path.read_text(encoding="utf-8")
    start_date = _parse_start_date(path, raw)
    roster_length = _parse_roster_length(raw)
    grid, roster_start_hour = _parse_shift_grid(raw, roster_length)
    start_datetime = datetime(
        start_date.year,
        start_date.month,
        start_date.day,
        roster_start_hour,
        0,
        0,
    )
    return start_datetime, roster_length, grid


def _cell_text(html_fragment: str) -> str:
    text = _TAG_RE.sub("", html_fragment)
    return " ".join(text.split())


def _parse_roster_length(raw: str) -> int:
    total = 0
    for thead_html in re.findall(r"<thead>(.*?)</thead>", raw, re.DOTALL | re.IGNORECASE):
        header_dates = re.findall(
            r'<span class="date">\((\d{2})/(\d{2})\)</span>',
            thead_html,
        )
        total += len(header_dates)
    if total == 0:
        raise ValueError("No column dates in header")
    return total


def _parse_shift_grid(raw: str, roster_length: int) -> tuple[list[list[str]], int]:
    tbody_parts = re.findall(r"<tbody>(.*?)</tbody>", raw, re.DOTALL | re.IGNORECASE)
    if not tbody_parts:
        raise ValueError("No <tbody> found")

    roster_start_hour = 6
    merged: list[list[str]] | None = None
    for tbody_html in tbody_parts:
        part, roster_start_hour = _parse_single_tbody(tbody_html, roster_start_hour)
        if merged is None:
            merged = part
            continue
        if len(part) != len(merged):
            raise ValueError("Roster tables have inconsistent shift row counts")
        for shift_index, names in enumerate(part):
            merged[shift_index].extend(names)

    assert merged is not None
    for row in merged:
        if len(row) != roster_length:
            raise ValueError(f"Row has {len(row)} day cells, expected {roster_length}")
    return merged, roster_start_hour


def _parse_single_tbody(
    tbody_html: str,
    roster_start_hour: int,
) -> tuple[list[list[str]], int]:
    rows = re.findall(r"<tr>(.*?)</tr>", tbody_html, re.DOTALL | re.IGNORECASE)
    grid: list[list[str]] = []
    for table_row in rows:
        cells = re.findall(r"<td([^>]*)>(.*?)</td>", table_row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 2:
            continue
        first_attrs, first_inner = cells[0]
        if "shift-label" not in first_attrs:
            continue
        shift_text = _cell_text(first_inner)
        roster_start_hour = _detect_start_hour(shift_text, grid, roster_start_hour)
        names = [_cell_text(inner) for _, inner in cells[1:]]
        grid.append(names)
    if not grid:
        raise ValueError("No shift rows parsed")
    return grid, roster_start_hour


def _parse_start_date(path: Path, raw: str) -> date:
    title_match = re.search(
        r"(?:רשימת שמירה|רשימת פטרולים)[^0-9]*(\d{2})/(\d{2})/(\d{4})",
        raw,
    )
    if not title_match:
        raise ValueError(f"Could not parse start date from title in {path}")
    day, month, year = (int(title_match.group(index)) for index in range(1, 4))
    return date(year, month, day)


def _detect_start_hour(shift_text: str, grid: list[list[str]], fallback: int) -> int:
    hour_match = re.search(r"(\d{2}:\d{2})", shift_text)
    if not hour_match or grid:
        return fallback
    hour, _minute = hour_match.group(1).split(":")
    return int(hour)
