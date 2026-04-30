"""Configuration loading and validation for the roster builder."""

import json
from pathlib import Path

DEFAULT_HISTORY_FILE = "./data/justice_history.json"
DEFAULT_OUTPUT_DIR = "./output"


def load_config(path: str) -> dict:
    """Load and validate a JSON configuration file.

    Expected format:
    {
        "guards": ["name1", "name2", ...],
        "shift_duration_hours": 4,
        "roster_length_days": 7,
        "constraints": { "guard_name": ["06:00", "10:00"], ... }
    }
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    _validate_config(config)
    return config


def merge_args(cli_args: dict, config: dict | None) -> dict:
    """Merge CLI arguments with config file values. CLI args take precedence."""
    merged = {}

    # Start from config if available
    if config:
        merged.update(config)

    # Override with CLI args (only if explicitly provided / not None)
    cli_overrides = {
        "guards": cli_args.get("guards"),
        "shift_duration_hours": cli_args.get("shift_duration"),
        "roster_length_days": cli_args.get("roster_length"),
        "constraints": cli_args.get("constraints"),
    }

    for key, value in cli_overrides.items():
        if value is not None:
            merged[key] = value

    if cli_args.get("rotation_start") is not None:
        merged["rotation_start"] = cli_args["rotation_start"]

    if cli_args.get("patrol") is True:
        merged["patrol"] = True

    # CLI values are None unless explicitly passed, so config values can carry paths.
    merged["start_date"] = cli_args["start_date"]
    merged["output_dir"] = cli_args.get("output_dir") or merged.get("output_dir", DEFAULT_OUTPUT_DIR)
    merged["history_file"] = cli_args.get("history_file") or merged.get("history_file", DEFAULT_HISTORY_FILE)
    merged["commit"] = cli_args.get("commit", False)
    merged["algorithm"] = cli_args.get("algorithm", "srr")

    _validate_config(merged)
    return merged


def _validate_config(config: dict) -> None:
    """Validate configuration values."""
    if "guards" not in config or not config["guards"]:
        raise ValueError("Config must include a non-empty 'guards' list")

    if not isinstance(config["guards"], list):
        raise ValueError("'guards' must be a list of strings")

    if config.get("patrol"):
        length = config.get("roster_length_days", 14)
        if length < 1:
            raise ValueError(f"roster_length_days must be at least 1, got {length}")
        return

    duration = config.get("shift_duration_hours", 4)
    if 24 % duration != 0:
        raise ValueError(f"shift_duration_hours ({duration}) must evenly divide 24")

    length = config.get("roster_length_days", 7)
    if length < 1:
        raise ValueError(f"roster_length_days must be at least 1, got {length}")

    constraints = config.get("constraints", {})
    if not isinstance(constraints, dict):
        raise ValueError("'constraints' must be a dict of guard_name -> list of shift times")
