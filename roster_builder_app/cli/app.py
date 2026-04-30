"""CLI application orchestration."""

from roster_builder_app.config_loader import merge_args
from roster_builder_app.history_manager import load_history
from roster_builder_app.scheduling.builder import build_roster

from .arguments import parse_args
from .configuration import (
    build_cli_args,
    build_guards,
    history_for_generation,
    load_optional_config,
    resolve_algorithm,
    resolve_shift_duration,
    resolve_start_date,
)
from .output import commit_or_explain, print_generation_summary, render_outputs, write_outputs


def main() -> None:
    args = parse_args()
    config = load_optional_config(args)
    cli_args = build_cli_args(args, config)
    start_date = resolve_start_date(cli_args)
    merged = merge_args(cli_args, config)
    guards = build_guards(merged)
    patrol = bool(merged.get("patrol"))
    shift_duration = resolve_shift_duration(merged, patrol)
    roster_length = merged.get("roster_length_days", 14 if patrol else 7)

    history_path = merged["history_file"]
    history_disk = load_history(history_path)
    history = history_for_generation(history_disk, patrol)
    algorithm = resolve_algorithm(merged.get("algorithm", "srr"), patrol)

    print_generation_summary(
        guards,
        history,
        algorithm,
        patrol,
        roster_length,
        shift_duration,
        start_date,
    )
    roster, current_counts, continuity_snapshot, continuity_applied = build_roster(
        guards=guards,
        shift_duration_hours=shift_duration,
        start_date=start_date,
        roster_length_days=roster_length,
        history=history,
        algorithm=algorithm,
        rules=merged,
        patrol=patrol,
        rotation_start=merged.get("rotation_start"),
    )
    if continuity_applied:
        print("   Continuity: using previous roster state (rotation / rest).")
        print()

    roster_html, justice_html = render_outputs(
        roster,
        current_counts,
        history,
        history_disk,
        patrol,
        shift_duration,
    )
    roster_path, justice_path = write_outputs(
        merged["output_dir"],
        start_date,
        roster_html,
        justice_html,
    )
    print(f"✅ Roster saved to: {roster_path}")
    print(f"✅ Justice table saved to: {justice_path}")
    commit_or_explain(merged, history_path, current_counts, history_disk, continuity_snapshot)
    print()
    print("Done!")
