# Architecture

## One-Line Summary
This is a script-first behavioral analysis repository: raw task files flow into Python analyses, which regenerate versioned outputs under task-specific result folders.

## Core Data Flow

```text
data/<TASK>_data/ -> scripts/<task>_<purpose>.py -> results/<analysis_name>/
```

## Source Of Truth By Concern
- Raw inputs: `data/`
- Shared filters, palettes, and coordinate constants: `scripts/analysis_common.py`
- Executable analyses: `scripts/`
- Regenerated figures, tables, and summaries: `results/`
- Durable rationale and interpretation constraints: `docs/`

## Directory Boundaries
- `data/`: readable by scripts, not hand-edited during routine analysis work.
- `scripts/`: analysis entry points and shared helpers; keep repeated logic centralized when it becomes cross-task.
- `results/`: generated artifacts only; changes should normally come from rerunning scripts.
- `docs/`: repository knowledge that must outlive a single script or conversation.

## Cross-Cutting Analysis Constraints
- Participant inclusion should go through the shared filters in `scripts/analysis_common.py`.
- Coordinate-based analyses should compare subjects in the unified 0–10 space, not directly in raw pixels.
- Screen-dependent task files must be rescaled using the relevant `squareSidePx` before cross-subject comparison; do not assume one global screen resolution.
- EP task day 3 and the tasks completed immediately afterward form one participant-specific screen-configuration block and should share the same scaling basis.
- EP/MR learned coordinates are the canonical face ground truth; see `docs/face-ground-truth.md`.
- PD odd/even recoding must happen before any condition-level aggregation or model fitting.
- PD village and distance effects are structurally confounded; see `docs/pdtask-main-effect.md`.

## Current Implemented Analysis
`scripts/pdtask_d_error_analysis.py` currently serves as the main executable analysis. It reads PD task data from `data/PDtask_data/`, applies the odd/even recoding, and writes descriptive outputs plus trial-level and subject-level summaries to `results/pdtask_d_error_analysis/`.

## Documentation Split
- Use `docs/development.md` for setup, validation, and change workflow.
- Use `docs/face-ground-truth.md` for canonical face coordinates.
- Use `docs/pdtask-main-effect.md` for the PD nested-design interpretation limit.
- Use `docs/analysis-roadmap.md` for planned analyses that are not yet fully implemented.
