# Repository Guidelines

## Project Structure & Module Organization
This repository is script-first. Put reusable analysis code in `scripts/`, for example `scripts/pdtask_d_error_analysis.py`. Store raw task datasets under `data/<TASK>_data/` such as `data/PDtask_data/` and `data/CTtask_data/`. Keep methodology notes and design constraints in `docs/`. Generated tables, figures, and model summaries should go to `results/`. Dependency and environment metadata live in `pyproject.toml` and `uv.lock`.

## Build, Test, and Development Commands
Use the project virtualenv or `uv` to run analyses:

- `uv sync`: install the Python dependencies from `pyproject.toml` and `uv.lock`.
- `.venv/bin/python scripts/pdtask_d_error_analysis.py`: run the PD task analysis and write outputs to `results/pdtask_d_error_analysis/`.
- `uv run python scripts/pdtask_d_error_analysis.py`: equivalent command when `uv` is available.
- `.venv/bin/python -m compileall scripts`: quick syntax check for Python analysis scripts.

## Coding Style & Naming Conventions
Target Python 3.10+. Use 4-space indentation, `snake_case` for variables/functions, and small helper functions instead of long linear scripts. Prefer pandas-, seaborn-, and statsmodels-based workflows already declared in `pyproject.toml`. Name scripts by task and purpose, for example `pdtask_d_error_analysis.py`. Keep dataset filenames unchanged unless a data-management task explicitly requires a rename.

## Testing Guidelines
There is no dedicated automated test suite yet. Validate changes by rerunning the affected script end-to-end and checking the generated tables, figures, and model summaries in `results/`. If you add reusable Python modules, place tests in a new `tests/` directory and use `test_<module>.py` naming. For analysis changes, document the input files used and the verification steps in the PR.

## Commit & Pull Request Guidelines
This repository currently has no commit history, so use clear imperative commit messages such as `feat: add PD task mixed-model script` or `fix: correct nested-condition coding`. Keep each commit focused on one analysis change. PRs should include a short summary, affected datasets or scripts, validation steps, and screenshots only when a generated figure changed materially.

## Data & Output Hygiene
Do not edit raw source files in `data/` unless the task explicitly requires data correction. Treat `docs/how to analysis main effect.md` as the design constraint for PD task inference: do not report independent main effects when the structure is nested and confounded. Regenerate outputs in `results/` when needed, and record assumptions, filtering rules, and model choices in code comments or `docs/`.
