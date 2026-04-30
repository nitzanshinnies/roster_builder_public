"""CLI argument parsing."""

import argparse

from config_loader import DEFAULT_HISTORY_FILE, DEFAULT_OUTPUT_DIR

START_DATE_FORMAT = "%Y-%m-%d %H:%M"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate guard duty rosters with fair shift distribution."
    )
    parser.add_argument("--config", type=str, help="Path to JSON config file with guards.")
    parser.add_argument("--guards", type=str, help="Comma-separated guard names.")
    parser.add_argument("--shift-duration", type=int, help="Shift duration in hours.")
    parser.add_argument(
        "--start-date",
        type=str,
        help='Start date/time in "YYYY-MM-DD HH:MM" format.',
    )
    parser.add_argument("--roster-length", type=int, help="Number of days to generate.")
    parser.add_argument(
        "--constraints",
        type=str,
        help='JSON constraints: {"guard_name": ["06:00", "10:00"]}',
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Output directory for generated files. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--history-file",
        type=str,
        default=None,
        help=f"Path to justice history file. Default: {DEFAULT_HISTORY_FILE}",
    )
    parser.add_argument("--commit", action="store_true", help="Commit counts to history.")
    parser.add_argument(
        "--algorithm",
        type=str,
        choices=["srr", "arr"],
        default="srr",
        help="Algorithm: srr or arr. Default: srr.",
    )
    parser.add_argument(
        "--patrol",
        action="store_true",
        help="Overnight patrol mode (20:30-08:30, two shifts).",
    )
    parser.add_argument(
        "--rotation-start",
        type=str,
        default=None,
        help="Guard name to lead the rotation.",
    )
    return parser.parse_args()
