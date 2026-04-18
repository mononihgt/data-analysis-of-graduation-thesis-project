# Script Guidelines

## Scope
This directory contains executable analysis scripts and small helper commands.

## Conventions
- Target Python 3.10+.
- Use 4-space indentation and `snake_case` for functions, variables, and filenames.
- Prefer small helper functions with explicit inputs over long top-level procedural blocks.
- Keep task analyses self-contained unless shared utilities are introduced intentionally.
- Use the shared completed-subject filter in `scripts/analysis_common.py` for participant inclusion; do not hardcode per-script inclusion lists.
- For coordinate-based tasks, normalize raw pixel coordinates with the task-relevant `squareSidePx` and analyze them in the shared 0–10 coordinate space.
- Read raw inputs from `data/<TASK>_data/` and write outputs to `results/<analysis_name>/`.

## Validation
Run `scripts/verify.sh` after script edits. For behavior changes, rerun the affected analysis end to end and inspect generated outputs.
