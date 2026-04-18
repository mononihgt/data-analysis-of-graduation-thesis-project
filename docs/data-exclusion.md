# Subject Exclusion Reference

## Current Excluded `SubNo`
- `1`
- `15`
- `17`

## Canonical Implementation
- The shared constant is `EXCLUDED_SUBNOS` in `scripts/analysis_common.py`.
- Scripts should reuse `filter_excluded_subjects()` or `filter_completed_subjects()` instead of writing inline filters.
- Treat this document as the human-readable reference; treat `scripts/analysis_common.py` as the executable source of truth.

## Maintenance Rule
- If the exclusion list changes, update this document and `scripts/analysis_common.py` together.
- Do not commit temporary debugging filters such as `raw = raw[raw['SubNo'] != ...]` in task scripts.
