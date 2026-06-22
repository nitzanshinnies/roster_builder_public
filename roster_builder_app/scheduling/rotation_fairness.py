"""Historical fairness helpers for SRR rotation and patrol pair seeding."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from roster_builder_app.history_manager import get_guard_history
from roster_builder_app.models import Guard, Roster, RosterDay, Shift

from .patrol_pair_srr import (
    PATROL_PAIR_GUARD_COUNT,
    build_patrol_pair_srr,
    patrol_guard_pairs,
    patrol_pair_assignments_for_day,
    patrol_pair_guard_order,
)
from .srr import build_srr
from .srr_rotation import srr_rotation_seed
from .continuity import parse_srr_continuity
from .time_utils import shift_datetime

MIN_PATROL_BOUNDARY_REST_HOURS = 36
MIN_GUARD_BOUNDARY_REST_HOURS = 8
CARRYOVER_GUARD_FIRST_NIGHT_PENALTY = 10_000.0
ENTERING_PAIR_NOT_FIRST_NIGHT_PENALTY = 5_000.0


def carryover_guard_names(guards: list[Guard], continuity: dict | None) -> set[str]:
    if not continuity:
        return set()
    saved = continuity.get("guards")
    if not isinstance(saved, list):
        return set()
    current = {guard.name for guard in guards}
    return current & set(saved)


def entering_guard_names(guards: list[Guard], continuity: dict | None) -> set[str]:
    """Guards joining this roster who were not on the previous committed roster."""
    if not continuity:
        return set()
    saved = continuity.get("guards")
    if not isinstance(saved, list):
        return set()
    current = {guard.name for guard in guards}
    return current - set(saved)


def parse_last_assignments(continuity: dict | None) -> dict[str, tuple[date, str]]:
    if not continuity:
        return {}
    block = continuity.get("srr")
    if not isinstance(block, dict):
        return {}
    raw = block.get("last_assignments")
    if not isinstance(raw, dict):
        return {}
    parsed: dict[str, tuple[date, str]] = {}
    for name, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        raw_date = payload.get("date")
        start_time = payload.get("start_time")
        if not isinstance(raw_date, str) or not isinstance(start_time, str):
            continue
        try:
            parsed[name] = (date.fromisoformat(raw_date), start_time)
        except ValueError:
            continue
    return parsed


def extract_last_assignments(roster: Roster, shift_duration_hours: int) -> dict[str, dict[str, str]]:
    """Last chronological slot per guard in a committed roster."""
    first_shift = roster.shifts[0].start_time
    latest_end: dict[str, datetime] = {}
    records: dict[str, dict[str, str]] = {}
    for day_offset, roster_day in enumerate(roster.days):
        for shift in roster.shifts:
            guard_name = roster_day.assignments.get(shift.label)
            if not guard_name:
                continue
            slot_start = shift_datetime(
                roster.start_date,
                day_offset,
                shift.start_time,
                first_shift,
            )
            slot_end = slot_start + timedelta(hours=shift_duration_hours)
            if guard_name not in latest_end or slot_end > latest_end[guard_name]:
                latest_end[guard_name] = slot_end
                records[guard_name] = {
                    "date": roster_day.date.isoformat(),
                    "start_time": shift.start_time,
                }
    return records


def resolve_patrol_pair_plan(
    guards: list[Guard],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    guard_allowed: dict,
    history: dict,
    continuity: dict | None,
    rules: dict | None,
    *,
    roster_start: datetime,
    shift_duration_hours: int,
) -> tuple[list[Guard], int, str | None, dict]:
    """Pick pair order and day offset to balance carryover early/late history."""
    rules = rules or {}
    carryovers = carryover_guard_names(guards, continuity)
    entering = entering_guard_names(guards, continuity)
    carryover_guard = _resolve_carryover_guard(guards, continuity, rules, carryovers)
    base_offset = _base_patrol_day_offset(continuity, rules)
    offset_candidates = _patrol_offset_candidates(base_offset, len(roster_days), rules)
    config_names = [guard.name for guard in guards]
    name_orders = _patrol_pair_name_orders(config_names, entering=entering)
    best_score = None
    best: tuple[list[str], int] | None = None

    for name_order in name_orders:
        for offset in offset_candidates:
            score = _score_patrol_pair_candidate(
                guards,
                name_order,
                shifts,
                roster_days,
                guard_allowed,
                history,
                carryovers,
                entering,
                carryover_guard,
                offset,
                continuity,
                roster_start,
                shift_duration_hours,
            )
            if best_score is None or score < best_score:
                best_score = score
                best = (name_order, offset)

    assert best is not None
    name_order, offset = best
    ordered = _guards_in_name_order(guards, name_order)
    report = build_carryover_fairness_report(
        guards,
        history,
        carryovers,
        _simulate_patrol_pair_counts(
            ordered,
            shifts,
            roster_days,
            guard_allowed,
            offset,
            carryover_guard,
        ),
        shift_keys=[shift.start_time for shift in shifts],
    )
    return ordered, offset, carryover_guard, report


def resolve_srr_rotation_seed(
    guards: list[Guard],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    guard_allowed: dict,
    history: dict,
    continuity: dict | None,
    rules: dict | None,
    *,
    patrol: bool,
    rotation_start: str | None,
    roster_start: datetime,
    shift_duration_hours: int,
) -> tuple[list[Guard], int, dict]:
    """Pick rotation index (and optional phase bump) for carryover shift-type balance."""
    carryovers = carryover_guard_names(guards, continuity)
    base_seed = (
        parse_srr_continuity(continuity, guards)
        if continuity
        else srr_rotation_seed(guards, history, patrol, rotation_start, None)
    )
    if not carryovers:
        return (*base_seed, {})

    rotation_order, rotation_idx = base_seed
    if not rotation_order:
        return (*base_seed, {})

    candidates = _srr_seed_candidates(rotation_order, rotation_idx)
    best_score = None
    best_seed = base_seed
    best_counts: dict | None = None

    for seed in candidates:
        days_copy = _copy_roster_days(roster_days)
        counts, _ = build_srr(
            guards,
            shifts,
            days_copy,
            history,
            guard_allowed,
            rules,
            srr_seed=seed,
            patrol=patrol,
            rotation_start=rotation_start,
        )
        score = _score_guard_srr_candidate(
            counts,
            history,
            carryovers,
            shifts,
            continuity,
            _first_slots_from_days(days_copy, shifts),
            roster_start,
            shift_duration_hours,
        )
        if best_score is None or score < best_score:
            best_score = score
            best_seed = seed
            best_counts = counts

    report = build_carryover_fairness_report(
        guards,
        history,
        carryovers,
        best_counts or {},
        shift_keys=[shift.start_time for shift in shifts],
    )
    return best_seed[0], best_seed[1], report


def build_carryover_fairness_report(
    guards: list[Guard],
    history: dict,
    carryovers: set[str],
    period_counts: dict,
    *,
    shift_keys: list[str],
) -> dict:
    rows = []
    for guard in guards:
        if guard.name not in carryovers:
            continue
        hist = get_guard_history(history, guard.name)
        period = period_counts.get(guard.name, {})
        projected = _combine_shift_counts(hist["shifts"], period.get("shifts", {}))
        rows.append(
            {
                "name": guard.name,
                "historical_shifts": dict(hist["shifts"]),
                "period_shifts": dict(period.get("shifts", {})),
                "projected_shifts": projected,
                "projected_spread": _shift_count_spread(projected, shift_keys),
            }
        )
    return {"carryovers": rows}


def _resolve_carryover_guard(
    guards: list[Guard],
    continuity: dict | None,
    rules: dict,
    carryovers: set[str],
) -> str | None:
    configured = rules.get("carryover_guard")
    if isinstance(configured, str) and configured in {guard.name for guard in guards}:
        return configured
    last = parse_last_assignments(continuity)
    if not last:
        return None
    current_carryovers = [name for name in last if name in carryovers]
    if len(current_carryovers) == 1:
        return current_carryovers[0]
    return None


def _patrol_offset_candidates(base_offset: int, roster_length_days: int, rules: dict) -> list[int]:
    force_offset = rules.get("force_patrol_day_offset")
    if isinstance(force_offset, int):
        return [force_offset]
    if roster_length_days % 2 != 0:
        return [base_offset]
    pair0_night = base_offset if base_offset % 2 == 0 else base_offset + 1
    pair1_night = base_offset if base_offset % 2 == 1 else base_offset + 1
    if pair0_night == pair1_night:
        return [pair0_night]
    return [pair0_night, pair1_night]


def _base_patrol_day_offset(continuity: dict | None, rules: dict) -> int:
    if continuity:
        block = continuity.get("srr")
        if isinstance(block, dict):
            saved = block.get("next_patrol_day_offset")
            if isinstance(saved, int):
                return saved
    config_offset = rules.get("patrol_day_offset")
    if isinstance(config_offset, int):
        return config_offset
    return 0


def _patrol_pair_name_orders(names: list[str], *, entering: set[str] | None = None) -> list[list[str]]:
    if len(names) != PATROL_PAIR_GUARD_COUNT:
        return [list(names)]
    orders: list[list[str]] = []
    for swap_first_pair in (False, True):
        for swap_second_pair in (False, True):
            order = list(names)
            if swap_first_pair:
                order[0], order[1] = order[1], order[0]
            if swap_second_pair:
                order[2], order[3] = order[3], order[2]
            if order not in orders:
                orders.append(order)
    if entering and len(entering) == 2:
        preferred = [order for order in orders if set(order[0:2]) == entering]
        if preferred:
            return preferred
    return orders


def _guards_in_name_order(guards: list[Guard], names: list[str]) -> list[Guard]:
    lookup = {guard.name: guard for guard in guards}
    return [lookup[name] for name in names]


def _copy_roster_days(roster_days: list[RosterDay]) -> list[RosterDay]:
    return [
        RosterDay(date=day.date, day_name_he=day.day_name_he)
        for day in roster_days
    ]


def _simulate_patrol_pair_counts(
    guards: list[Guard],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    guard_allowed: dict,
    global_day_offset: int,
    carryover_guard: str | None,
) -> dict:
    days_copy = _copy_roster_days(roster_days)
    counts, _ = build_patrol_pair_srr(
        guards,
        shifts,
        days_copy,
        guard_allowed,
        global_day_offset=global_day_offset,
        carryover_guard=carryover_guard,
    )
    return counts


def _score_patrol_pair_candidate(
    guards: list[Guard],
    name_order: list[str],
    shifts: list[Shift],
    roster_days: list[RosterDay],
    guard_allowed: dict,
    history: dict,
    carryovers: set[str],
    entering: set[str],
    carryover_guard: str | None,
    global_day_offset: int,
    continuity: dict | None,
    roster_start: datetime,
    shift_duration_hours: int,
) -> float:
    ordered = _guards_in_name_order(guards, name_order)
    days_copy = _copy_roster_days(roster_days)
    counts, _ = build_patrol_pair_srr(
        ordered,
        shifts,
        days_copy,
        guard_allowed,
        global_day_offset=global_day_offset,
        carryover_guard=carryover_guard,
    )
    shift_keys = [shift.start_time for shift in shifts]
    score = _carryover_shift_balance_score(counts, history, carryovers, shift_keys)
    score += _boundary_rest_penalty(
        carryovers,
        continuity,
        _first_slots_from_days(days_copy, shifts),
        roster_start,
        shifts[0].start_time,
        shift_duration_hours,
        MIN_PATROL_BOUNDARY_REST_HOURS,
    )
    score += _entering_guards_first_night_penalty(
        ordered,
        carryovers,
        entering,
        carryover_guard,
        global_day_offset,
    )
    return score


def _entering_guards_first_night_penalty(
    guards: list[Guard],
    carryovers: set[str],
    entering: set[str],
    carryover_guard: str | None,
    global_day_offset: int,
) -> float:
    """Prefer the entering pair on night 0 so carryovers rest across the roster boundary."""
    if not carryovers or len(entering) != 2 or len(guards) != PATROL_PAIR_GUARD_COUNT:
        return 0.0

    ordered = patrol_pair_guard_order(guards, carryover_guard)
    pairs = patrol_guard_pairs(ordered)
    evening_guard, morning_guard = patrol_pair_assignments_for_day(
        0,
        pairs,
        global_day_offset=global_day_offset,
    )
    penalty = 0.0
    if global_day_offset % 2 != 0:
        penalty += ENTERING_PAIR_NOT_FIRST_NIGHT_PENALTY
    if {guard.name for guard in ordered[0:2]} != entering:
        penalty += ENTERING_PAIR_NOT_FIRST_NIGHT_PENALTY
    if evening_guard.name in carryovers:
        penalty += CARRYOVER_GUARD_FIRST_NIGHT_PENALTY
    if morning_guard.name in carryovers:
        penalty += CARRYOVER_GUARD_FIRST_NIGHT_PENALTY * 0.5
    return penalty


def _score_guard_srr_candidate(
    period_counts: dict,
    history: dict,
    carryovers: set[str],
    shifts: list[Shift],
    continuity: dict | None,
    first_slots: dict[str, tuple[date, str]],
    roster_start: datetime,
    shift_duration_hours: int,
) -> float:
    shift_keys = [shift.start_time for shift in shifts]
    score = _carryover_shift_balance_score(period_counts, history, carryovers, shift_keys)
    score += _boundary_rest_penalty(
        carryovers,
        continuity,
        first_slots,
        roster_start,
        shifts[0].start_time,
        shift_duration_hours,
        MIN_GUARD_BOUNDARY_REST_HOURS,
    )
    return score


def _carryover_shift_balance_score(
    period_counts: dict,
    history: dict,
    carryovers: set[str],
    shift_keys: list[str],
) -> float:
    if not carryovers:
        return 0.0
    score = 0.0
    for name in carryovers:
        hist = get_guard_history(history, name)
        period = period_counts.get(name, {})
        projected = _combine_shift_counts(hist["shifts"], period.get("shifts", {}))
        if len(shift_keys) == 2:
            left = projected.get(shift_keys[0], 0)
            right = projected.get(shift_keys[1], 0)
            score += abs(left - right)
        else:
            score += _shift_count_spread(projected, shift_keys)
    return score


def _combine_shift_counts(historical: dict, period: dict) -> dict[str, int]:
    combined: dict[str, int] = {}
    for key in set(historical) | set(period):
        combined[key] = historical.get(key, 0) + period.get(key, 0)
    return combined


def _shift_count_spread(counts: dict[str, int], shift_keys: list[str]) -> int:
    values = [counts.get(key, 0) for key in shift_keys]
    if not values:
        return 0
    return max(values) - min(values)


def _srr_seed_candidates(
    rotation_order: list[Guard],
    rotation_idx: int,
) -> list[tuple[list[Guard], int]]:
    size = len(rotation_order)
    if size == 0:
        return [(rotation_order, rotation_idx)]
    return [
        (rotation_order, rotation_idx),
        (rotation_order, (rotation_idx + 1) % size),
    ]


def _first_slots_from_days(
    roster_days: list[RosterDay],
    shifts: list[Shift],
) -> dict[str, tuple[date, str]]:
    first: dict[str, tuple[date, str]] = {}
    for roster_day in roster_days:
        for shift in shifts:
            guard_name = roster_day.assignments.get(shift.label)
            if guard_name and guard_name not in first:
                first[guard_name] = (roster_day.date, shift.start_time)
    return first


def _boundary_rest_penalty(
    carryovers: set[str],
    continuity: dict | None,
    first_slots: dict[str, tuple[date, str]],
    roster_start: datetime,
    first_shift_start: str,
    shift_duration_hours: int,
    min_rest_hours: float,
) -> float:
    last_assignments = parse_last_assignments(continuity)
    if not last_assignments:
        return 0.0

    previous_start = _previous_roster_start(continuity, roster_start)
    if previous_start is None:
        return 0.0

    penalty = 0.0
    for name in carryovers:
        if name not in last_assignments or name not in first_slots:
            continue
        last_date, last_start_time = last_assignments[name]
        first_date, first_start_time = first_slots[name]
        last_day_offset = (last_date - previous_start.date()).days
        first_day_offset = (first_date - roster_start.date()).days
        last_start = shift_datetime(previous_start, last_day_offset, last_start_time, first_shift_start)
        last_end = last_start + timedelta(hours=shift_duration_hours)
        first_start = shift_datetime(roster_start, first_day_offset, first_start_time, first_shift_start)
        rest_hours = (first_start - last_end).total_seconds() / 3600
        if rest_hours < min_rest_hours:
            penalty += (min_rest_hours - rest_hours) * 100
    return penalty


def _previous_roster_start(continuity: dict | None, roster_start: datetime) -> datetime | None:
    if not continuity:
        return None
    raw = continuity.get("next_roster_start")
    if not isinstance(raw, str):
        return None
    try:
        expected_next = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if expected_next != roster_start:
        return None
    length = continuity.get("roster_length_days")
    if not isinstance(length, int) or length < 1:
        return None
    return roster_start - timedelta(days=length)
