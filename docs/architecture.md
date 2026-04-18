# Architecture

## Repository Shape
This is an analysis-script-first repository. The core flow is:

```text
data/<TASK>_data/ -> scripts/<task>_<purpose>.py -> results/<analysis_name>/
```

## Boundaries
- `data/` stores source task datasets. Analysis code may read from it but should not mutate raw files.
- `scripts/` contains executable analyses and small helper commands.
- `results/` contains generated outputs that can be regenerated from scripts and data.
- `docs/` records design constraints, workflow notes, and interpretation rules.

## Current Analysis
The current executable analysis is `scripts/pdtask_d_error_analysis.py`. It reads PD task files from `data/PDtask_data/`, applies the odd/even participant condition recoding, and writes descriptive outputs plus both trial-level MixedLM and subject-level repeated-measures outputs to `results/pdtask_d_error_analysis/`.

## PD Task Modeling Constraint
Distance and village relationship are nested and structurally confounded in the current PD task design. See `docs/pdtask-main-effect.md` before changing model formulas or report language.
