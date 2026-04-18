# Development Workflow

## Setup
Install dependencies from the lockfile:

```bash
uv sync
```

Use `.venv/bin/python` directly when the local virtual environment already exists.

## Quick Verification
Run the repository quick check:

```bash
scripts/verify.sh
```

The quick check currently compiles Python files under `scripts/`.

## Analysis Verification
For analysis changes, rerun the affected script and inspect the regenerated files under `results/`.

For the PD task:

```bash
.venv/bin/python scripts/pdtask_d_error_analysis.py
```

or:

```bash
uv run python scripts/pdtask_d_error_analysis.py
```

## Adding Analyses
- Put task-specific scripts in `scripts/` using `<task>_<purpose>.py` naming.
- Write generated outputs to `results/<analysis_name>/`.
- Record analysis assumptions, filtering rules, and model choices in code and relevant docs.
- Add or update a focused doc when a statistical constraint affects interpretation.
