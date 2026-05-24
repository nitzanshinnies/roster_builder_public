# Roster Builder Usage Guide

Roster Builder is a Python CLI tool for generating guard-duty rosters as Hebrew RTL HTML tables.
It also produces a justice report that summarizes assignment counts per guard.

The project supports two roster types:

- Standard guard roster: configurable 24-hour coverage split into equal shifts.
- Patrol roster: fixed overnight patrol shifts, `20:30-02:30` and `02:30-08:30`.

## Quick Start

Run a standard roster:

```bash
python roster_builder.py \
  --config config/default_config.json \
  --start-date "2026-03-09 06:00"
```

Run a patrol roster:

```bash
python roster_builder.py \
  --config config/patrol_config.json \
  --patrol \
  --start-date "2026-04-12 20:30"
```

Generated files are written to `output/`:

- `roster_<YYYY-MM-DD>.html`: the roster table.
- `justice_<YYYY-MM-DD>.html`: assignment-count summary.

`output/` is ignored by git, so generated HTML files are local artifacts unless you explicitly copy or
publish them elsewhere.

## Requirements

The project uses only the Python standard library.

Recommended runtime:

```bash
python --version
```

Use Python 3.10 or newer. The code uses modern type-hint syntax such as `list[str]`.

## Main CLI Options

```bash
python roster_builder.py [options]
```

Common options:

- `--config <path>`: JSON config file. Example: `config/default_config.json`.
- `--guards "A,B,C"`: comma-separated guard names. Overrides `guards` from config.
- `--shift-duration <hours>`: standard roster shift length. Must divide evenly into 24.
- `--start-date "YYYY-MM-DD HH:MM"`: first roster slot date/time.
- `--roster-length <days>`: number of roster days to generate.
- `--constraints '<json>'`: JSON guard constraints from the command line.
- `--output-dir <path>`: output directory. Defaults to `./output`.
- `--history-file <path>`: justice history file. Defaults to `./data/justice_history.json`.
- `--algorithm srr|arr`: scheduling algorithm. Defaults to `srr`.
- `--patrol`: use the fixed patrol shifts.
- `--rotation-start <guard>`: guard to lead the SRR rotation.
- `--commit`: write this run into the history file.

Config-level `history_file` and `output_dir` values are used unless the corresponding CLI option is
provided.

## Config File Structure

A config file is a JSON object. Minimal standard-roster example:

```json
{
  "guards": ["Guard A", "Guard B", "Guard C", "Guard D"],
  "shift_duration_hours": 4,
  "roster_length_days": 7,
  "constraints": {}
}
```

Minimal patrol example:

```json
{
  "patrol": true,
  "guards": ["Guard A", "Guard B", "Guard C", "Guard D"],
  "rotation_start": "Guard A",
  "roster_length_days": 14,
  "start_date": "2026-04-12 20:30",
  "algorithm": "srr",
  "history_file": "data/patrol_justice_history.json",
  "constraints": {}
}
```

## Config Fields

### `guards`

Required list of guard names.

```json
{
  "guards": ["Guard A", "Guard B", "Guard C"]
}
```

The order matters for patrol/SRR when `rotation_start` is used. For standard SRR without a seed, the
scheduler may sort guards by historical totals first.

### `shift_duration_hours`

Standard roster shift duration. It must divide evenly into 24.

Examples:

- `4`: creates six shifts per day.
- `6`: creates four shifts per day.
- `8`: creates three shifts per day.

This field is ignored in patrol mode, where shifts are fixed at six hours.

### `roster_length_days`

Number of days to generate.

```json
{
  "roster_length_days": 7
}
```

### `start_date`

Optional config-level start date/time.

```json
{
  "start_date": "2026-03-09 06:00"
}
```

You can also pass `--start-date` from the CLI. CLI values take precedence.

### `algorithm`

Supported algorithms:

- `srr`: Simple Round-Robin.
- `arr`: Advanced Round-Robin.

Patrol mode always uses SRR. If `--patrol` is used with `arr`, the CLI falls back to `srr`.

### `patrol`

Set to `true` to generate an overnight patrol roster.

Patrol mode uses these shifts:

- `20:30-02:30`
- `02:30-08:30`

Patrol assignment ignores justice history for scheduling, but the justice report can still display and
commit patrol counts when requested.

When exactly **four** guards are configured, patrol mode uses **pair rotation**:

- Guards `1` and `2` form one pair; guards `3` and `4` form the other (list order matters).
- Each night, one pair works both shifts.
- On that pair's next night, evening and morning roles swap between the two guards.

Optional pair-mode fields:

```json
{
  "carryover_guard": "Guard D",
  "patrol_day_offset": 14
}
```

- `carryover_guard`: moves the named guard to the last pair slot (continuity from the previous roster).
- `patrol_day_offset`: global day counter so pair/swap phase continues across adjacent rosters.

Example four-guard patrol config: `config/example_patrol_pair_config.json`.

### `rotation_start`

Optional guard name used to rotate the SRR order so this guard appears first.

```json
{
  "rotation_start": "Guard A"
}
```

This is useful for continuing an existing manual rotation.

### `history_file`

Path to the JSON file that stores cumulative justice counts and roster continuity.

```json
{
  "history_file": "data/justice_history.json"
}
```

For patrol rosters, prefer a separate history file:

```json
{
  "history_file": "data/patrol_justice_history.json"
}
```

When running from the CLI, `--history-file` overrides this config value.

## Constraints

Constraints restrict which shifts a guard may receive.

The structure is:

```json
{
  "constraints": {
    "Guard A": ["06:00", "10:00"],
    "Guard B": ["2026-05-04 14:00 - 18:00"]
  }
}
```

If a guard has no entry in `constraints`, that guard is eligible for all shifts.

### Recurring Shift Constraints

Use a shift start time to allow a guard only on that recurring shift type:

```json
{
  "constraints": {
    "Guard A": ["06:00", "10:00", "14:00"]
  }
}
```

This means Guard A may be assigned only to shifts that start at `06:00`, `10:00`, or `14:00`.

### Dated Shift Constraints

Use `YYYY-MM-DD` plus a shift name to allow a guard only on exact dated slots:

```json
{
  "constraints": {
    "Guard E": [
      "2026-05-02 20:30 - 02:30",
      "2026-05-04 20:30 - 02:30"
    ]
  }
}
```

The parser accepts the generated shift label style with an en dash too:

```json
{
  "constraints": {
    "Guard E": ["2026-05-02 20:30 – 02:30"]
  }
}
```

Dated constraints can also use just the shift start time:

```json
{
  "constraints": {
    "Guard E": ["2026-05-02 20:30"]
  }
}
```

### Excluded Shift Slots

Prefix a dated slot with `!` to block a guard from that exact shift only:

```json
{
  "constraints": {
    "Guard B": ["!2026-05-14 02:30 – 08:30"]
  }
}
```

The guard remains eligible for all other shifts unless additional allow-list constraints are set.

### SRR Behavior With Dated Constraints

In SRR, a guard who has only dated constraints is treated as an insert into the normal cycle.

Example regular cycle:

```text
A B C D A B C D
```

If Guard E is constrained to a slot in the middle, the result is:

```text
A B E C D A B C
```

The regular cycle resumes after the inserted guard. Guard E does not consume the next regular guard's
turn.

### ARR Behavior With Dated Constraints

ARR has no fixed cycle. Dated constraints affect eligibility only:

- The guard is eligible for the matching dated slot.
- If the guard has only dated constraints, they are not eligible elsewhere.
- ARR chooses among eligible guards using its scoring rules.

## Shabbat And Holiday Rules

Standard rosters can define guards who should not receive Shabbat shifts.

```json
{
  "shabbat_observers": ["Guard A"],
  "shabbat_shifts": [
    { "weekday": 5, "start_time": "18:00" },
    { "weekday": 5, "start_time": "22:00" },
    { "weekday": 6, "start_time": "02:00" },
    { "weekday": 6, "start_time": "06:00" },
    { "weekday": 6, "start_time": "10:00" },
    { "weekday": 6, "start_time": "14:00" }
  ],
  "shabbat_dinner_shift": { "weekday": 5, "start_time": "18:00" }
}
```

`weekday` follows `datetime.date.isoweekday()`:

- Monday: `1`
- Tuesday: `2`
- Wednesday: `3`
- Thursday: `4`
- Friday: `5`
- Saturday: `6`
- Sunday: `7`

Holiday dinner shifts can also be marked:

```json
{
  "holiday_dinner_shifts": [
    { "date": "2026-04-01", "start_time": "18:00" }
  ]
}
```

Dinner shifts are counted separately in the justice report and are used to avoid assigning the same
guard to both configured dinner categories in one roster.

## Algorithms

### SRR: Simple Round-Robin

SRR cycles through guards in a fixed order.

It also enforces:

- guard shift constraints;
- Shabbat observer rules;
- one assignment per guard per day when possible;
- special handling for dated exact-slot constraints.

When `--commit` is used, SRR writes a continuity snapshot so the next adjacent roster can resume the
cycle.

### ARR: Advanced Round-Robin

ARR scores eligible guards for every slot.

It balances:

- current roster assignment totals;
- historical assignment totals;
- shift-type variety;
- rest time between shifts;
- Shabbat/holiday dinner fairness.

ARR enforces shift constraints and Shabbat rules. It may relax same-day assignment or rest constraints
if no candidate is otherwise available, but it does not relax shift constraints or Shabbat observer
rules.

## History And Commit Mode

By default, roster generation is a preview:

```bash
python roster_builder.py --config config/default_config.json --start-date "2026-03-09 06:00"
```

Preview mode writes HTML files but does not update history.

Use `--commit` to update the selected history file:

```bash
python roster_builder.py \
  --config config/default_config.json \
  --start-date "2026-03-09 06:00" \
  --commit
```

Commit mode updates:

- cumulative guard totals;
- per-shift assignment counts;
- Friday dinner counts;
- roster continuity metadata.

For patrol:

```bash
python roster_builder.py \
  --config config/patrol_config.json \
  --patrol \
  --history-file data/patrol_justice_history.json \
  --start-date "2026-04-30 20:30" \
  --commit
```

## Importing Existing HTML Into History

If a roster was generated or edited but not committed, `python -m roster_builder_app.ingest_cli` can parse a roster HTML
file and update history:

```bash
python -m roster_builder_app.ingest_cli output/roster_2026-03-09.html \
  --config config/default_config.json \
  --history-file data/justice_history.json
```

Dry run:

```bash
python -m roster_builder_app.ingest_cli output/roster_2026-03-09.html \
  --config config/default_config.json \
  --history-file data/justice_history.json \
  --dry-run
```

## Public Repository Checklist

Before making the repository public:

- Replace real guard names in `config/*.json` with sample names if they are private.
- Review `data/*.json`; history files may contain real names and assignment history.
- Confirm generated `output/` files are not committed.
- Consider adding a license file.
- Consider replacing Hebrew sample data with anonymous examples while keeping Hebrew UI support.

## Troubleshooting

### `ValueError: shift_duration_hours must evenly divide 24`

Use a shift duration such as `4`, `6`, `8`, or `12`.

### A constrained guard is never assigned

Check that the constraint matches the actual shift start or generated shift label.

For patrol, use:

```text
20:30
02:30
2026-05-02 20:30 - 02:30
```

For standard four-hour shifts starting at `06:00`, use:

```text
06:00
10:00
14:00
18:00
22:00
02:00
```

### The wrong history file was updated

Check the effective config and any CLI override. If `--history-file` is omitted, the config value is used;
if neither is set, the default is `./data/justice_history.json`.

### The generated roster differs after rerunning

Generation is deterministic for a given start timestamp and input data. Differences usually come from:

- changed guard list;
- changed constraints;
- changed history file;
- different `--rotation-start`;
- using `--commit` before rerunning.

