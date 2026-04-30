#!/usr/bin/env python3
"""Load a published roster HTML into justice history."""

import argparse
import sys
from pathlib import Path

from config_loader import load_config
from history_manager import commit_history, load_history
from ingest.html_parser import parse_roster_html
from ingest.replay import resolve_build_state
from models import Guard
from scheduling.builder import ALG_ARR


def _build_guards(config: dict) -> list[Guard]:
    constraints = config.get("constraints", {})
    return [
        Guard(name=name, allowed_shifts=constraints.get(name))
        for name in config["guards"]
    ]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_path", type=Path, help="Path to roster_YYYY-MM-DD.html")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/example_config.json"),
        help="Config JSON (guards, rules)",
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=Path("data/justice_history.json"),
        help="Justice history to update",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and match only")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.html_path.is_file():
        print(f"❌ Not a file: {args.html_path}", file=sys.stderr)
        sys.exit(1)

    start_date, roster_length, grid = parse_roster_html(args.html_path)
    config = load_config(str(args.config))
    merged = {**config, "shift_duration_hours": config.get("shift_duration_hours", 4)}
    history_path = str(args.history_file.resolve())
    history = load_history(history_path)

    algorithm, current_counts, snap = resolve_build_state(
        _build_guards(merged),
        merged["shift_duration_hours"],
        start_date,
        roster_length,
        history,
        merged,
        grid,
    )
    _print_match_summary(args.html_path, start_date, roster_length, algorithm, snap)
    if args.dry_run:
        print("   (dry-run: no file written)")
        return

    commit_history(history_path, current_counts, history, roster_continuity=snap)
    print(f"✅ Updated {history_path} (counts + roster_continuity)")


def _print_match_summary(
    html_path: Path,
    start_date,
    roster_length: int,
    algorithm: str,
    snap: dict,
) -> None:
    print(f"📥 Parsed: {html_path.name}")
    print(f"   Start: {start_date.isoformat()}  ({roster_length} days)")
    print(f"   Matched algorithm: {algorithm}")
    print(f"   Next roster continuity → {snap['next_roster_start']}")
    if algorithm == ALG_ARR:
        print("   Note: continuity is for ARR — use --algorithm arr on the next roster run.")


if __name__ == "__main__":
    main()
