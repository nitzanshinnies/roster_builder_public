"""CLI output, rendering, and persistence helpers."""

from datetime import datetime
from pathlib import Path

from roster_builder_app.history_manager import commit_history
from roster_builder_app.models import Guard, Roster
from roster_builder_app.rendering.justice_html import render_justice_html
from roster_builder_app.rendering.roster_html import render_roster_html

from .arguments import START_DATE_FORMAT


def commit_or_explain(
    merged: dict,
    history_path: str,
    current_counts: dict,
    history_disk: dict,
    continuity_snapshot: dict,
) -> None:
    if merged["commit"]:
        commit_history(
            history_path,
            current_counts,
            history_disk,
            roster_continuity=continuity_snapshot,
        )
        print(f"✅ Justice history committed to: {history_path}")
        return
    print("ℹ️  Run with --commit to save counts and next-week roster continuity to history.")


def print_generation_summary(
    guards: list[Guard],
    history: dict,
    algorithm: str,
    patrol: bool,
    roster_length: int,
    shift_duration: int,
    start_date: datetime,
) -> None:
    alg_name = "Simple Round-Robin" if algorithm == "srr" else "Advanced Round-Robin"
    print("📋 Generating roster:")
    print(f"   Guards: {len(guards)}")
    if patrol:
        print(f"   Mode: patrol (20:30-02:30, 02:30-08:30), {shift_duration}h per shift")
        if len(guards) == 4:
            print("   Patrol pair rotation: 4 guards, alternating shifts within pairs")
    else:
        print(f"   Shift duration: {shift_duration}h")
    print(f"   Start: {start_date.strftime(START_DATE_FORMAT)}")
    print(f"   Days: {roster_length}")
    print(f"   Algorithm: {alg_name} ({algorithm})")
    if patrol:
        print("   History: used for carryover shift-type fairness when continuity matches")
    else:
        print(f"   History: {'loaded' if history.get('last_updated') else 'none'}")
    print()


def print_carryover_fairness_report(fairness_report: dict) -> None:
    rows = fairness_report.get("carryovers") if fairness_report else None
    if not rows:
        return
    print("   Carryover fairness (projected shift-type balance):")
    for row in rows:
        projected = row.get("projected_shifts", {})
        spread = row.get("projected_spread", 0)
        print(f"      {row['name']}: projected {projected} (spread {spread})")
    print()


def render_outputs(
    roster: Roster,
    current_counts: dict,
    history: dict,
    history_disk: dict,
    patrol: bool,
    shift_duration: int,
) -> tuple[str, str]:
    roster_html = render_roster_html(roster, patrol=patrol)
    justice_render_history = history if patrol else history_disk
    justice_html = render_justice_html(
        roster,
        current_counts,
        justice_render_history,
        shift_duration,
    )
    return roster_html, justice_html


def write_outputs(
    output_dir_raw: str,
    start_date: datetime,
    roster_html: str,
    justice_html: str,
) -> tuple[Path, Path]:
    output_dir = Path(output_dir_raw)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = start_date.strftime("%Y-%m-%d")
    roster_path = output_dir / f"roster_{date_str}.html"
    justice_path = output_dir / f"justice_{date_str}.html"

    roster_path.write_text(roster_html, encoding="utf-8")
    justice_path.write_text(justice_html, encoding="utf-8")
    return roster_path, justice_path
