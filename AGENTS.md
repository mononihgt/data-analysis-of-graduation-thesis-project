# Repository Guidelines

## Purpose
This repository contains behavioral task data analyses for the thesis project. Treat the repository as the system of record for analysis code, design constraints, generated outputs, and verification commands.

## Directory Map
- `data/`: raw task datasets plus local data-handling rules; do not edit raw files without an explicit data-correction task.
- `scripts/`: executable Python analysis scripts and lightweight helper commands.
- `docs/`: methodology notes, architecture notes, development workflow, and analysis rationale.
- `results/`: generated tables, figures, and model summaries grouped by analysis name.
- `pyproject.toml`, `uv.lock`: Python dependency and environment metadata.

Scoped `AGENTS.md` files in major subdirectories add local rules. Follow the most specific applicable file before editing.

## Commands
- `uv sync`: install dependencies from `pyproject.toml` and `uv.lock`.
- `scripts/verify.sh`: run the repository quick check.
- `.venv/bin/python -m compileall scripts`: run the quick Python syntax check directly.
- `.venv/bin/python scripts/pdtask_d_error_analysis.py`: regenerate PD task outputs in `results/pdtask_d_error_analysis/`.
- `uv run python scripts/pdtask_d_error_analysis.py`: run the same analysis through `uv`.

## Hard Rules
- Keep raw dataset filenames unchanged unless the user explicitly requests a data-management rename.
- Keep generated artifacts under `results/<analysis_name>/`; do not mix generated outputs into `docs/` or `scripts/`.
- Analysis inclusion should be restricted to participants who completed the full experiment battery; repository scripts should use the shared completed-subject filter from `scripts/analysis_common.py` instead of ad hoc subject lists.
- Different participants and different dates can use different screen resolutions. EP task day 3 and all later tasks are run on the same screen setup for a given participant/date block; coordinate-based analyses must infer the relevant `squareSidePx` and rescale responses accordingly before cross-subject comparison.
- All coordinate-based analyses should use a unified 0–10 coordinate system for plotting, descriptive summaries, and inferential tests; treat pixel or 400×400 task coordinates as intermediate representations only.
- Do not report independent PD task main effects when distance and village relationship are nested and confounded.
- Apply the odd/even participant recoding before any PD task condition summary or model.

## PD Task Design
For odd-numbered participants, instructions define `AB` as closer than `AC`. For even-numbered participants, instructions define `AC` as closer than `AB`.

Keep these labels distinct:
- `raw_condition`: direct source village-pair label (`same`, `AB`, `AC`, `BC`).
- `condition`: analysis-ready recoding (`same`, `near`, `far`, `unknown`).

Do not interpret `AB` and `AC` as fixed distance categories across all participants without first applying the recoding rule.
- PD analyses must treat the EP/MR learned face coordinates as the psychological ground truth.
- Do not use the PD task source-code face template as the true face layout for plotting, true-distance calculation, or Varignon true centers.
- If PD task files contain face coordinates generated from the outdated PD template, use them only to infer screen/square scaling and normalize recorded responses before comparing against the EP/MR learned truth.

## Coding Style
- Target Python 3.10+ with 4-space indentation and `snake_case` names.
- Prefer small helper functions over long linear scripts.
- Match the pandas, seaborn, scipy, and statsmodels workflow already used here.
- Name analysis scripts by task and purpose, for example `pdtask_d_error_analysis.py`.

## Validation
There is no dedicated automated test suite yet. For structural or documentation changes, run `scripts/verify.sh`. For analysis changes, rerun the affected script end to end and inspect regenerated outputs in `results/`.

## Deeper Docs
- `docs/architecture.md`: repository architecture and data flow.
- `docs/development.md`: setup, validation, and change workflow.
- `docs/pdtask-main-effect.md`: PD task nested-design inference constraint.
