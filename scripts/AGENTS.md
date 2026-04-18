# Script Guidelines

## Scope
This directory contains executable analysis scripts and small helper commands.

## Shared Sources Of Truth
- Reuse `scripts/analysis_common.py` for participant filters, PD condition recoding, plotting defaults, and shared coordinate constants.
- Keep task-specific logic in task scripts; move repeated helpers into shared utilities intentionally.

## Conventions
- Target Python 3.10+.
- Use 4-space indentation and `snake_case` for functions, variables, and filenames.
- Prefer small helper functions with explicit inputs over long top-level procedural blocks.
- Keep task analyses self-contained unless shared utilities are introduced intentionally.
- Use the shared completed-subject filter in `scripts/analysis_common.py` for participant inclusion; do not hardcode per-script inclusion lists.
- For coordinate-based tasks, infer the task-relevant `squareSidePx` for each participant/date block; do not assume one global screen resolution.
- EP task day 3 and all tasks completed immediately afterward share the same participant-specific screen configuration / `squareSidePx` block.
- Normalize raw pixel coordinates with the relevant `squareSidePx` and analyze them in the shared 0–10 coordinate space.
- Keep one Python entry point per task, named with the experiment `proc` prefix such as `proc4_pdtask_analysis.py`.
- Read raw inputs from `data/<TASK>_data/` and write outputs to `results/<analysis_name>/`.

## Validation
Run `scripts/verify.sh` after script edits. For behavior changes, rerun the affected analysis end to end and inspect generated outputs.
