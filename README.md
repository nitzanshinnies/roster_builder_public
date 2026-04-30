# Roster Builder

A Python CLI tool that generates guard duty rosters with fair shift distribution.

Roster Builder is a lightweight Python tool for creating fair guard-duty and patrol schedules in seconds.
It supports configurable shift lengths, overnight patrol rosters, guard availability constraints,
Shabbat/holiday rules, rotation continuity between cycles, and automatic justice reports that track workload
balance over time. It outputs clean Hebrew RTL HTML rosters ready to share or print, while keeping all personal
config and history data local.

## Features

- Generates an HTML roster table (Hebrew RTL) with days as columns and shifts as rows
- Produces a justice/fairness report showing shift distribution per guard
- Supports configurable shift durations, roster lengths, and guard constraints
- Algorithm ensures even distribution and adequate rest periods

## Usage

```bash
python roster_builder.py --start-date "2026-03-09 06:00" --config config/example_config.json
```

For full CLI usage, config schema, constraints, history handling, and public-release notes, see
[`USAGE.md`](USAGE.md).

## Configuration

All arguments except `start-date` can be provided via a JSON config file. See `config/example_config.json`
for a safe sample. Keep real names and history in local ignored files.

## Output

Generated files are saved to the `output/` directory:
- `roster_<date>.html` — The roster table
- `justice_<date>.html` — Shift distribution summary
