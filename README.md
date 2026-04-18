# Data Analysis Repository

This repository contains task-specific behavioral data analyses, source datasets, analysis notes, and generated outputs for the thesis project.

## Repository Structure
- `data/`: raw task datasets and data-specific handling notes.
- `scripts/`: executable analysis scripts and helper commands.
- `docs/`: architecture, development workflow, methodology notes, and design constraints.
- `results/`: generated tables, figures, and model summaries.
- `AGENTS.md`: repository map and rules for future agent work.
- `pyproject.toml`, `uv.lock`: Python dependency metadata.

Current task data folders include `PDtask_data`, `CTtask_data`, `DJtask_data`, `EPtask_data`, `MRtask_data`, and `SPtask1_data`.

## Environment Setup
This project targets Python 3.10+.

```bash
uv sync
```

If you prefer the local virtual environment directly, use `.venv/bin/python`.

## Common Commands
```bash
scripts/verify.sh
.venv/bin/python scripts/pdtask_d_error_analysis.py
uv run python scripts/pdtask_d_error_analysis.py
```

The PD task script writes outputs to `results/pdtask_d_error_analysis/`.

## PD Task Design Note
For the PD task, the instruction manipulation differs by participant parity:

- odd-numbered participants are instructed that `AB` is closer than `AC`
- even-numbered participants are instructed that `AC` is closer than `AB`

This information is conveyed through the experiment instructions rather than directly encoded in the raw village-pair labels. PD analyses must relabel raw condition codes before condition-level summaries or modeling.

In the current workflow:

- `raw_condition` refers to the original pair label from the source data: `same`, `AB`, `AC`, `BC`
- `condition` refers to the analysis-ready recoding: `same`, `near`, `far`, `unknown`

Do not interpret `AB` and `AC` as fixed distance categories across all participants without applying the odd/even recoding rule first.

## Analysis Constraint
For PD task inference, follow `docs/pdtask-main-effect.md`. The key principle is that distance and village relationship are structurally confounded in the current design, so independent main effects should not be reported.

## More Documentation
- `docs/architecture.md`: analysis data flow and repository boundaries.
- `docs/development.md`: setup, validation, and change workflow.
- `data/README.md`: raw data folder map.
