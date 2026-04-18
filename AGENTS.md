# Repository Guidelines

## Purpose
This repository is the system of record for thesis-related behavioral data analysis: raw inputs, executable scripts, generated outputs, and the design constraints that govern interpretation.

## Quick Map
- `README.md`: user-facing repository overview.
- `docs/README.md`: documentation index and reading order.
- `data/`: raw task datasets and local metadata; raw files are not edited unless the user explicitly asks for data correction.
- `scripts/`: executable Python analyses and shared helpers such as `scripts/analysis_common.py`.
- `results/`: regenerated figures, tables, and statistical summaries grouped by analysis name.
- `docs/`: durable workflow notes, architecture rules, and task-specific interpretation constraints.

Scoped `AGENTS.md` files in subdirectories override this file for their own tree.

## Critical Analysis Rules
- Use the shared participant filters in `scripts/analysis_common.py`; do not hardcode ad hoc subject lists in analysis scripts.
- Treat `EXCLUDED_SUBNOS` and `filter_completed_subjects()` in `scripts/analysis_common.py` as the canonical implementation of current inclusion and exclusion rules.
- Normalize coordinate-based analyses into the shared 0–10 space before cross-subject summaries, plots, or inferential tests; 400×400 and raw pixel spaces are intermediate representations only.
- Different participants and different dates can use different screen configurations; infer and apply the relevant `squareSidePx` instead of assuming one global pixel template.
- Within a participant, EP task day 3 and all tasks completed immediately afterward share the same screen configuration / `squareSidePx` block and should be rescaled consistently.
- Use the learned EP/MR face coordinates as the psychological ground truth; do not treat the outdated PD template coordinates as true locations.
- For PD analyses, recode odd and even participants before any condition summary or model:
  - odd `SubNo`: `AB -> near`, `AC -> far`
  - even `SubNo`: `AC -> near`, `AB -> far`
- Do not report independent PD main effects for village relationship and distance; the design is nested and structurally confounded. See `docs/pdtask-main-effect.md`.

## Directory Rules
- `data/`: keep source filenames stable and store task datasets under `data/<TASK>_data/`.
- `scripts/`: prefer small helpers, explicit inputs, and shared utilities over repeated inline logic.
- `results/`: write generated outputs only under `results/<analysis_name>/`.
- `docs/`: keep durable rationale here, not buried in script comments or chat context.

## Common Commands
- `uv sync`
- `scripts/verify.sh`
- `.venv/bin/python -m compileall scripts`
- `.venv/bin/python scripts/pdtask_d_error_analysis.py`
- `uv run python scripts/pdtask_d_error_analysis.py`

## Coding Style
- Target Python 3.10+.
- Use 4-space indentation and `snake_case`.
- Match the existing pandas / seaborn / scipy / statsmodels workflow.
- Name analysis entry points by task and purpose, for example `pdtask_d_error_analysis.py`.

## Validation
- For documentation-only changes, run `scripts/verify.sh`.
- For script changes, rerun the affected analysis end to end and inspect the regenerated files under `results/`.
- There is no full automated test suite yet, so be explicit about what was and was not verified.

## Canonical Docs
- `docs/README.md`: documentation index and reading path.
- `docs/architecture.md`: repository shape, boundaries, and shared sources of truth.
- `docs/development.md`: setup, validation, and change workflow.
- `docs/face-ground-truth.md`: canonical face coordinates and how to use them.
- `docs/pdtask-main-effect.md`: PD nested-design inference constraint.
- `docs/analysis-roadmap.md`: pending analysis and figure requirements by task.
- `docs/data-exclusion.md`: current exclusion reference and maintenance rules.
