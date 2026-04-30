"""Config and CLI option resolution."""

import argparse
import json
import sys
from datetime import datetime, timedelta

from roster_builder_app.config_loader import load_config
from roster_builder_app.models import Guard, PATROL_SHIFT_DURATION_HOURS

from .arguments import START_DATE_FORMAT


def build_cli_args(args: argparse.Namespace, config: dict | None) -> dict:
    cli_args = {
        "start_date": args.start_date,
        "output_dir": args.output_dir,
        "history_file": args.history_file,
        "commit": args.commit,
        "algorithm": args.algorithm,
        "patrol": True if args.patrol else None,
        "rotation_start": args.rotation_start,
    }
    if config and config.get("start_date") and not args.start_date:
        cli_args["start_date"] = config["start_date"]
    if args.guards:
        cli_args["guards"] = [guard.strip() for guard in args.guards.split(",")]
    if args.shift_duration:
        cli_args["shift_duration"] = args.shift_duration
    if args.roster_length:
        cli_args["roster_length"] = args.roster_length
    if args.constraints:
        cli_args["constraints"] = json.loads(args.constraints)
    return cli_args


def build_guards(merged: dict) -> list[Guard]:
    constraints = merged.get("constraints", {})
    return [
        Guard(name=name, allowed_shifts=constraints.get(name))
        for name in merged["guards"]
    ]


def history_for_generation(history_disk: dict, patrol: bool) -> dict:
    if patrol:
        return {"last_updated": None, "guards": {}}
    return history_disk


def load_optional_config(args: argparse.Namespace) -> dict | None:
    if not args.config:
        return None
    return load_config(args.config)


def resolve_algorithm(algorithm: str, patrol: bool) -> str:
    if patrol and algorithm != "srr":
        print("ℹ️  Patrol mode uses SRR only; using srr.")
        return "srr"
    return algorithm


def resolve_shift_duration(merged: dict, patrol: bool) -> int:
    if patrol:
        return PATROL_SHIFT_DURATION_HOURS
    return merged.get("shift_duration_hours", 4)


def resolve_start_date(cli_args: dict) -> datetime:
    if cli_args["start_date"]:
        start_date = datetime.strptime(cli_args["start_date"], START_DATE_FORMAT)
        if start_date.date() < datetime.now().date():
            print(f"❌ Error: Cannot base a roster on a past date ({start_date:%Y-%m-%d}).")
            sys.exit(1)
        return start_date

    start_date = _default_start_date()
    cli_args["start_date"] = start_date.strftime(START_DATE_FORMAT)
    return start_date


def _default_start_date(now: datetime | None = None) -> datetime:
    current = now or datetime.now()
    days_ahead = -current.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return current.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
