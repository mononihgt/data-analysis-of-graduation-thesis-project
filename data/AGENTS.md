# Data Guidelines

## Scope
This directory contains raw task datasets and lightweight metadata about those datasets.

## Rules
- Do not edit raw source files unless the user explicitly requests a data-correction task.
- Keep source filenames unchanged so scripts and provenance remain stable.
- Store task datasets under `data/<TASK>_data/`.
- Keep documentation files in this directory small and metadata-focused; put methodology and interpretation rules in `docs/`.
- Treat recorded coordinate and bar-length fields as screen-specific measurements; downstream analyses must rescale them rather than treat them as universal truth coordinates.

## Canonical References
- `data/README.md`: local folder map only.
- `scripts/analysis_common.py`: canonical implementation of exclusion and inclusion filters.
