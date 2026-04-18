# PD Task Nested-Design Constraint

## Key Takeaway
- Do not report independent main effects of village relationship and distance.
- Recode odd and even participants first, then analyze the unified `condition` factor (`same`, `near`, `far`, `unknown`).
- The cleanest default analysis is `Y ~ Condition + (1 | Subject)` or the subject-level analogue.

## Why The Main Effects Are Not Identifiable

### Conceptual Factors
- Village relationship:
  - same village
  - different village
- Distance:
  - nearest
  - near
  - far
  - unknown

### Observed Cells
- same village -> nearest only
- different village -> near / far / unknown

Missing cells are structural, not random:
- there are no same-village near / far / unknown trials
- there are no different-village nearest trials

Therefore distance is nested within village relationship, and the two effects are structurally confounded.

## Correct Design Label
- This is not a factorial design.
- The correct description is an unbalanced nested design, with distance nested within village relationship.

## What You Can Estimate

### Preferred Strategy: Single-Factor `condition`
Define a single analysis factor:
- `same`
- `near`
- `far`
- `unknown`

Recommended models:

```text
trial level:   Y ~ Condition + (1 | Subject)
subject level: subject_mean(Y) ~ Condition + Error(Subject / Condition)
```

When the model is stable, random condition slopes are also acceptable.

### Alternative Strategy: Decompose The Question
- Compare same-village vs different-village overall, while explicitly stating this is confounded with distance structure.
- Test distance effects only within different-village trials (`near`, `far`, `unknown`).

## What You Cannot Claim
- No independent main effect of village relationship.
- No independent main effect of distance across the full design.
- No interpretable village × distance interaction.
- Do not describe the design as factorial.

## Required Reporting Language
Use wording such as:
- distance is nested within village relationship
- nearest trials occur only in the same-village condition
- the two conceptual factors cannot be fully disentangled in the current design

Avoid wording such as:
- “main effect of village”
- “main effect of distance”
- “factorial ANOVA”

## Practical Implication For This Repository
- Recode odd and even participants before any condition summary or model.
- Use the EP/MR learned coordinates as ground truth for PD geometry work.
- Rescale recorded PD coordinates with the same participant's proc1 day-3 `squareSidePx`, then compare them in the shared 0–10 space.
- Do not use PD `F*X` / `F*Y` fields or outdated PD template constants as learning truth or scale references.
- When updating `scripts/proc4_pdtask_analysis.py`, keep the reporting language aligned with this document.

## Only Real Design Fix
The only full solution is a future fully crossed design in which same-village and different-village trials both contain all distance levels.
