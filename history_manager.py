"""Justice history persistence for cross-run fairness balancing."""

import json
from datetime import date
from pathlib import Path


def load_history(path: str) -> dict:
    """Load existing justice history, or return empty structure if not found.

    Returns:
        {
            "last_updated": "2026-03-15",
            "guards": {
                "guard_name": {
                    "total": 5,
                    "shifts": { "06:00": 1, "10:00": 1, ... }
                }
            }
        }
    """
    history_path = Path(path)
    if not history_path.exists():
        return {"last_updated": None, "guards": {}}

    with open(history_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_guard_history(history: dict, guard_name: str) -> dict:
    """Get a specific guard's historical counts.

    Returns:
        {
            "total": int,
            "shifts": {"06:00": int, ...},
            "friday_dinner": int,
        }
    """
    base = history.get("guards", {}).get(guard_name, {})
    return {
        "total": base.get("total", 0),
        "shifts": base.get("shifts", {}),
        "friday_dinner": base.get("friday_dinner", 0),
    }


def commit_history(
    path: str,
    current_counts: dict,
    existing_history: dict,
    roster_continuity: dict | None = None,
) -> None:
    """Merge current run's counts into history and persist.

    Args:
        path: path to justice_history.json
        current_counts: {guard_name: {"total": int, "shifts": {shift_start: int}}}
        existing_history: the loaded history dict
        roster_continuity: optional snapshot so the next roster run can continue
            round-robin / rest state from this committed period (see scheduler).
    """
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    guards = existing_history.get("guards", {})

    for guard_name, counts in current_counts.items():
        if guard_name not in guards:
            guards[guard_name] = {"total": 0, "shifts": {}, "friday_dinner": 0}

        guards[guard_name]["total"] += counts["total"]

        for shift_key, count in counts["shifts"].items():
            current = guards[guard_name]["shifts"].get(shift_key, 0)
            guards[guard_name]["shifts"][shift_key] = current + count

        # Friday-night (Shabbat dinner) justice variable
        fd = counts.get("friday_dinner", 0)
        guards[guard_name]["friday_dinner"] = guards[guard_name].get("friday_dinner", 0) + fd

    existing_history["guards"] = guards
    existing_history["last_updated"] = date.today().isoformat()

    if roster_continuity is not None:
        existing_history["roster_continuity"] = roster_continuity

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(existing_history, f, ensure_ascii=False, indent=2)
