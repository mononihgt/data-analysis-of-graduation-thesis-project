# Documentation Guidelines

## Scope
This directory stores durable repository knowledge: architecture, workflow, task constraints, shared reference values, and the analysis backlog.

## Expected Document Layout
- `docs/README.md`: index, reading order, and document map.
- `architecture.md`: repository shape, boundaries, and sources of truth.
- `development.md`: setup, validation, and change workflow.
- task-specific notes such as `pdtask-main-effect.md`.
- shared references such as `face-ground-truth.md`.
- backlog or planning docs such as `analysis-roadmap.md`.

## Writing Rules
- Use lowercase kebab-case filenames.
- Front-load the key takeaway or decision before detailed explanation.
- Prefer cross-references to canonical docs instead of repeating the same rule in multiple files.
- Keep implementation details in scripts and put durable interpretation rules in docs.
- When documenting coordinate-based tasks, state the canonical truth in shared 0–10 space and treat raw pixels / 400×400 values as derived representations only.
- When documenting screen scaling, note that screen configuration can vary by participant and date, but EP task day 3 and the later tasks from that same session share one `squareSidePx` block.
- When a doc introduces or changes a canonical workflow, update `docs/README.md`, `README.md`, and root `AGENTS.md`.
