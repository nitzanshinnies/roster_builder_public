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
    thead_match = re.search(r"<thead>(.*?)</thead>", raw, re.DOTALL | re.IGNORECASE)
    if not thead_match:
        raise ValueError("No <thead> found")
    header_dates = re.findall(
        r'<span class="date">\((\d{2})/(\d{2})\)</span>',
        thead_match.group(1),
    )
    if not header_dates:
        raise ValueError("No column dates in header")
    return len(header_dates)


def _parse_shift_grid(raw: str, roster_length: int) -> tuple[list[list[str]], int]:
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", raw, re.DOTALL | re.IGNORECASE)
    if not tbody_match:
        raise ValueError("No <tbody> found")
    rows = re.findall(r"<tr>(.*?)</tr>", tbody_match.group(1), re.DOTALL | re.IGNORECASE)

    grid: list[list[str]] = []
    roster_start_hour = 6
    for table_row in rows:
        cells = re.findall(r"<td([^>]*)>(.*?)</td>", table_row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 2:
            continue
        first_attrs, first_inner = cells[0]
        if "shift-label" not in first_attrs:
            continue
        shift_text = _cell_text(first_inner)
        roster_start_hour = _detect_start_hour(shift_text, grid, roster_start_hour)
        names = [_cell_text(inner) for _, inner in cells[1 : 1 + roster_length]]
        if len(names) != roster_length:
            raise ValueError(f"Row has {len(names)} day cells, expected {roster_length}: {shift_text!r}")
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
