# Data Analysis Repository

This repository stores thesis-related behavioral task analyses, raw datasets, shared analysis rules, and regenerated outputs.

## Quick Start
This project targets Python 3.10+.

```bash
uv sync
scripts/verify.sh
```

Use `.venv/bin/python` directly when the local environment already exists.

## Repository Structure
- `data/`: raw task datasets and local metadata.
- `scripts/`: executable analyses plus shared helpers in `scripts/analysis_common.py`.
- `results/`: generated figures, tables, and model summaries.
- `docs/`: architecture notes, workflow docs, design constraints, and analysis backlog.
- `AGENTS.md`: repository rules for agent or scripted changes.
- `pyproject.toml`, `uv.lock`: dependency metadata.

Current task data folders include `PDtask_data`, `CTtask_data`, `DJtask_data`, `EPtask_data`, `MRtask_data`, and `SPtask1_data`.

## Core Workflow
```bash
scripts/verify.sh
.venv/bin/python scripts/run_all_analysis.py
.venv/bin/python scripts/proc4_pdtask_analysis.py
uv run python scripts/proc4_pdtask_analysis.py
```

To rerun all task analyses together, use `scripts/run_all_analysis.py`. It runs `proc1`–`proc6` in parallel and writes per-script logs under `results/run_all_analysis/`.

Task analysis entry points follow the MATLAB experiment `proc` order:
- `scripts/run_all_analysis.py`
- `scripts/proc1_eptask_learning_analysis.py`
- `scripts/proc2_sptask_rt_analysis.py`
- `scripts/proc3_djtask_accuracy_analysis.py`
- `scripts/proc4_pdtask_analysis.py`
- `scripts/proc5_cttask_position_analysis.py`
- `scripts/proc6_mrtask_reconstruction_analysis.py`

Each script writes outputs to the matching `results/procN_.../` directory.

## Critical Analysis Constraints
- Use the shared participant filters in `scripts/analysis_common.py`; do not maintain per-script inclusion lists.
- Normalize coordinate analyses into the shared 0–10 space before cross-subject plots, summaries, or inferential tests.
- Do not assume a single global screen resolution; infer the task-relevant `squareSidePx` for each participant/date block.
- Treat EP task day 3 and all later tasks completed immediately afterward as one shared screen-configuration block within each participant.
- Use the learned EP/MR face coordinates as ground truth.
- For PD, load `squareSidePx` from the same participant's proc1 day-3 output; PD template coordinates and PD-program hardcoded face positions are erroneous legacy values, not scaling aids.
- Recode PD `AB` and `AC` labels by participant parity before summaries or modeling:
  - odd `SubNo`: `AB -> near`, `AC -> far`
  - even `SubNo`: `AC -> near`, `AB -> far`
- Do not report independent PD main effects for village relationship and distance; see `docs/pdtask-main-effect.md`.

## Documentation Map
- `docs/README.md`: documentation index and recommended reading order.
- `docs/architecture.md`: repository boundaries and shared sources of truth.
- `docs/development.md`: setup, validation, and change workflow.
- `docs/face-ground-truth.md`: canonical face coordinates and coordinate usage rules.
- `docs/pdtask-main-effect.md`: PD nested-design interpretation constraint.
- `docs/analysis-roadmap.md`: task-by-task pending analysis and figure requirements.
- `docs/data-exclusion.md`: current exclusion reference.
- `data/README.md`: raw data folder map.
