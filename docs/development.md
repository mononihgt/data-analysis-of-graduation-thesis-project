# Development Workflow

## Setup

```bash
uv sync
```

If the local virtual environment already exists, use `.venv/bin/python` directly.

## Minimum Verification

```bash
scripts/verify.sh
```

The quick check currently compiles Python files under `scripts/`.

## Validation Matrix
- Documentation-only change: run `scripts/verify.sh`.
- Script refactor with no intended behavior change: run `scripts/verify.sh`, then review the diff carefully.
- Analysis behavior change: rerun the affected script, inspect regenerated files under `results/`, and state what was validated.

## Common Analysis Commands

```bash
.venv/bin/python scripts/run_all_analysis.py
.venv/bin/python scripts/run_all_analysis.py --jobs 3
.venv/bin/python scripts/proc4_pdtask_analysis.py
uv run python scripts/proc4_pdtask_analysis.py
```

`scripts/run_all_analysis.py` runs `proc1`–`proc6` in parallel. It writes one log file per script under `results/run_all_analysis/`.

## Adding Or Updating Analyses
1. Create or update a task script in `scripts/` using the experiment `proc` prefix, for example `proc4_pdtask_analysis.py`.
2. Reuse shared helpers from `scripts/analysis_common.py` for filters, recoding, plotting style, and shared coordinates.
3. For coordinate-based tasks, infer the participant/date-relevant `squareSidePx` before comparing subjects; EP task day 3 and the later tasks from that same session share one scaling block, and PD should reuse that proc1 day-3 value rather than any PD-specific template.
4. Output coordinate-based plots and inferential tests in the shared 0–10 space rather than in raw pixels or 400×400 coordinates.
5. Write outputs under `results/<analysis_name>/`.
6. Record durable interpretation constraints or workflow changes in `docs/`.
7. Update `docs/README.md`, `README.md`, and root `AGENTS.md` when a new canonical doc is added.

## Documentation Expectations
- Put architecture and workflow information in `docs/`, not in large script headers.
- Put statistical interpretation constraints in focused docs such as `docs/pdtask-main-effect.md`.
- Keep backlog-style requests in `docs/analysis-roadmap.md` instead of scattering them across chat context or ad hoc notes.
