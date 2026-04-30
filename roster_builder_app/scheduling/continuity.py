"""Roster continuity snapshots across adjacent committed runs."""

from datetime import datetime, timedelta

from roster_builder_app.models import Guard


def continuity_matches(
    history: dict,
    start_date: datetime,
    guards: list[Guard],
    algorithm: str,
    shift_duration_hours: int,
    first_shift_start: str,
) -> dict | None:
    """Return saved continuity dict if this run should continue the previous roster."""
    raw = history.get("roster_continuity")
    if not isinstance(raw, dict):
        return None
    try:
        expected_next = datetime.fromisoformat(raw["next_roster_start"])
    except (KeyError, TypeError, ValueError):
        return None
    if expected_next != start_date:
        return None
    if raw.get("algorithm") != algorithm:
        return None
    if raw.get("shift_duration_hours") != shift_duration_hours:
        return None
    if raw.get("first_shift_start") != first_shift_start:
        return None
    saved_guards = raw.get("guards")
    if not isinstance(saved_guards, list):
        return None
    current_guard_names = set(guard_names_sorted(guards))
    if not current_guard_names.intersection(saved_guards):
        return None
    return raw


def continuity_snapshot(
    start_date: datetime,
    roster_length_days: int,
    algorithm: str,
    shift_duration_hours: int,
    first_shift_start: str,
    guards: list[Guard],
    srr_state: dict | None = None,
    arr_last_shift_end: dict[str, datetime | None] | None = None,
) -> dict:
    """Payload written to history and consumed by the next adjacent roster run."""
    snap: dict = {
        "next_roster_start": (start_date + timedelta(days=roster_length_days)).isoformat(),
        "algorithm": algorithm,
        "shift_duration_hours": shift_duration_hours,
        "first_shift_start": first_shift_start,
        "guards": guard_names_sorted(guards),
    }
    if srr_state is not None:
        snap["srr"] = srr_state
    if arr_last_shift_end is not None:
        snap["arr"] = {
            "last_shift_end": {
                name: dt.isoformat()
                for name, dt in arr_last_shift_end.items()
                if dt is not None
            }
        }
    return snap


def guard_names_sorted(guards: list[Guard]) -> list[str]:
    return sorted(guard.name for guard in guards)


def parse_arr_continuity(cont: dict | None, guards: list[Guard]) -> dict[str, datetime | None] | None:
    if not cont:
        return None
    block = cont.get("arr")
    if not isinstance(block, dict):
        return None
    raw = block.get("last_shift_end")
    if not isinstance(raw, dict):
        return None
    out: dict[str, datetime | None] = {guard.name: None for guard in guards}
    for guard in guards:
        iso = raw.get(guard.name)
        if isinstance(iso, str):
            try:
                out[guard.name] = datetime.fromisoformat(iso)
            except ValueError:
                out[guard.name] = None
    return out


def parse_srr_continuity(cont: dict | None, guards: list[Guard]) -> tuple[list[Guard], int] | None:
    if not cont:
        return None
    block = cont.get("srr")
    if not isinstance(block, dict):
        return None
    order_names = block.get("rotation_order")
    idx = block.get("next_rotation_index")
    if not isinstance(order_names, list) or not isinstance(idx, int):
        return None

    name_to_guard = {guard.name: guard for guard in guards}
    current_names = set(name_to_guard)
    carried_names = [name for name in order_names if name in current_names]
    added_names = sorted(name for name in current_names if name not in set(order_names))
    merged_names = carried_names + added_names
    if not merged_names:
        return None

    next_name = _next_continuity_guard_name(order_names, idx, current_names)
    next_idx = merged_names.index(next_name) if next_name is not None else 0
    return [name_to_guard[name] for name in merged_names], next_idx


def _next_continuity_guard_name(
    order_names: list[str],
    idx: int,
    current_names: set[str],
) -> str | None:
    for offset in range(len(order_names)):
        candidate_name = order_names[(idx + offset) % len(order_names)]
        if candidate_name in current_names:
            return candidate_name
    return None
