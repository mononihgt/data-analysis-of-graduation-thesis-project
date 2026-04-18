# Documentation Map

## Start Here
- `architecture.md`: repository shape, boundaries, and shared sources of truth.
- `development.md`: setup, validation, and change workflow.
- `face-ground-truth.md`: canonical face coordinates and coordinate usage rules.
- `pdtask-main-effect.md`: PD nested-design interpretation constraint.

## Read By Question
- “How is the repository organized?” -> `architecture.md`
- “How do I run or verify work?” -> `development.md`
- “Which face coordinates count as ground truth?” -> `face-ground-truth.md`
- “Why can’t PD report separate main effects?” -> `pdtask-main-effect.md`
- “What analyses and figures are still planned?” -> `analysis-roadmap.md`
- “Which participants are excluded?” -> `data-exclusion.md`

## Critical Rules To Keep In Mind
- Use shared participant filters from `scripts/analysis_common.py`.
- Normalize coordinate analyses into the shared 0–10 space before cross-subject plots, summaries, or inferential tests.
- Do not assume a single global screen resolution; infer the relevant `squareSidePx` for each participant/date block.
- EP task day 3 and all tasks completed immediately afterward share the same participant-specific screen configuration / `squareSidePx`.
- Use the learned EP/MR face coordinates as canonical truth.
- Recode PD odd/even participants before condition-level summaries.
- Do not report independent PD main effects for village relationship and distance.

## Script Entry Points
- `scripts/run_all_analysis.py`: 并行运行 `proc1`–`proc6`，并把日志写到 `results/run_all_analysis/`
- `scripts/proc1_eptask_learning_analysis.py`
- `scripts/proc2_sptask_rt_analysis.py`
- `scripts/proc3_djtask_accuracy_analysis.py`
- `scripts/proc4_pdtask_analysis.py`
- `scripts/proc5_cttask_position_analysis.py`
- `scripts/proc6_mrtask_reconstruction_analysis.py`

## Maintenance Notes
- Keep canonical workflow docs linked from `README.md` and root `AGENTS.md`.
- Prefer adding a focused new doc over bloating an unrelated one.
- When a rule becomes implementation-critical, mirror it in `scripts/analysis_common.py` or another deterministic check where possible.
