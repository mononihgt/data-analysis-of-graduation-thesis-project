from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import numpy as np
import pandas as pd

from analysis_common import (
    completed_all_task_subject_ids,
    DATA_DIR,
    filter_completed_subjects,
    infer_date_from_path,
    infer_subno_from_path,
    mat_ret_to_df,
)


EP_DATA_DIR = DATA_DIR / "EPtask_data"
OUTPUT_DIR = ROOT / "results" / "eptask_square_side_audit"
PREFERRED_SUFFIX = {".mat": 0, ".xlsx": 1, ".csv": 2}
FACE_VALUES_0_TO_10 = {
    1: (2.416, 4.788),
    2: (2.789, 7.765),
    3: (6.426, 8.527),
    4: (8.817, 6.716),
    5: (4.894, 2.020),
    6: (7.659, 3.185),
}
NUMERIC_COLUMNS = ["SubNo", "face", "true_leftBar", "true_rightBar", "leftBarLength", "rightBarLength", "acc", "rt"]


def session_index_from_path(path: Path) -> int:
    match = re.search(r"\d{4}-\d{2}-\d{2}(?:-(\d+))?\.", path.name)
    if not match:
        return 0
    return int(match.group(1) or 0)


def select_preferred_files(paths: list[Path]) -> list[Path]:
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        by_stem[path.stem].append(path)
    selected = [
        sorted(stem_paths, key=lambda path: PREFERRED_SUFFIX.get(path.suffix, 99))[0]
        for stem_paths in by_stem.values()
    ]
    return sorted(
        selected,
        key=lambda path: (
            infer_subno_from_path(path) or -1,
            infer_date_from_path(path) or "",
            session_index_from_path(path),
            path.name,
        ),
    )


def read_ep_file(path: Path) -> pd.DataFrame:
    if path.suffix == ".mat":
        df = mat_ret_to_df(path)
    elif path.suffix == ".xlsx":
        df = pd.read_excel(path)
    elif path.suffix == ".csv":
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="gbk")
    else:
        raise ValueError(f"Unsupported EP file: {path}")

    df["source"] = path.name
    df["date"] = infer_date_from_path(path)
    df["session_index"] = session_index_from_path(path)
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    if "SubNo" not in df.columns:
        df["SubNo"] = infer_subno_from_path(path)
    return df


def load_ep_test_data() -> pd.DataFrame:
    paths = [
        path
        for path in EP_DATA_DIR.iterdir()
        if path.is_file() and path.name.startswith("EPtask-") and not path.name.startswith("EPtask_learning-")
    ]
    frames = [read_ep_file(path) for path in select_preferred_files(paths)]
    if not frames:
        raise FileNotFoundError(f"No EP test files found in {EP_DATA_DIR}")

    data = pd.concat(frames, ignore_index=True)
    data = data.dropna(subset=["SubNo", "date", "face", "true_leftBar", "true_rightBar"]).copy()
    data["SubNo"] = data["SubNo"].astype(int)
    data = filter_completed_subjects(data)
    data["face"] = data["face"].astype(int)
    data = data[data["face"].isin(FACE_VALUES_0_TO_10)].copy()
    return data.sort_values(["SubNo", "date", "session_index", "source"]).reset_index(drop=True)


def estimate_rows(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in data.itertuples(index=False):
        face_x, face_y = FACE_VALUES_0_TO_10[int(row.face)]
        square_x = float(row.true_leftBar) / (face_x / 10)
        square_y = float(row.true_rightBar) / (face_y / 10)
        rows.append(
            {
                "SubNo": int(row.SubNo),
                "date": row.date,
                "session_index": int(row.session_index),
                "source": row.source,
                "face": int(row.face),
                "axis": "left",
                "true_bar_px": float(row.true_leftBar),
                "face_value_0_to_10": face_x,
                "face_value_ratio": face_x / 10,
                "square_side_estimate": square_x,
            }
        )
        rows.append(
            {
                "SubNo": int(row.SubNo),
                "date": row.date,
                "session_index": int(row.session_index),
                "source": row.source,
                "face": int(row.face),
                "axis": "right",
                "true_bar_px": float(row.true_rightBar),
                "face_value_0_to_10": face_y,
                "face_value_ratio": face_y / 10,
                "square_side_estimate": square_y,
            }
        )
    return pd.DataFrame(rows)


def best_integer_square_side(group: pd.DataFrame) -> tuple[int, float, float]:
    observed = []
    ratios = []
    for face, face_df in group.groupby("face"):
        face_x, face_y = FACE_VALUES_0_TO_10[int(face)]
        truth = face_df[["true_leftBar", "true_rightBar"]].drop_duplicates()
        for values in truth.itertuples(index=False):
            observed.extend([float(values.true_leftBar), float(values.true_rightBar)])
            ratios.extend([face_x / 10, face_y / 10])

    observed_array = np.array(observed, dtype=float)
    ratio_array = np.array(ratios, dtype=float)
    if len(observed_array) == 0:
        return 0, np.nan, np.nan

    raw_estimate = float(np.dot(observed_array, ratio_array) / np.dot(ratio_array, ratio_array))
    candidates = np.arange(max(1, int(np.floor(raw_estimate)) - 5), int(np.ceil(raw_estimate)) + 6)
    predictions = np.rint(np.outer(candidates, ratio_array))
    errors = predictions - observed_array
    rmse_by_candidate = np.sqrt(np.mean(errors**2, axis=1))
    best_index = int(np.argmin(rmse_by_candidate))
    best_side = int(candidates[best_index])
    max_abs_error = float(np.max(np.abs(errors[best_index])))
    return best_side, float(rmse_by_candidate[best_index]), max_abs_error


def summarize_group(data: pd.DataFrame, estimates: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, group in data.groupby(group_columns, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_data = dict(zip(group_columns, keys))
        estimate_mask = np.ones(len(estimates), dtype=bool)
        for column, value in key_data.items():
            estimate_mask &= estimates[column].to_numpy() == value
        group_estimates = estimates.loc[estimate_mask, "square_side_estimate"].dropna()
        best_side, rmse_px, max_abs_error_px = best_integer_square_side(group)
        unique_faces = sorted(group["face"].dropna().astype(int).unique())
        rows.append(
            {
                **key_data,
                "n_files": int(group["source"].nunique()),
                "n_trials": int(len(group)),
                "n_faces": int(len(unique_faces)),
                "faces_observed": " ".join(map(str, unique_faces)),
                "square_side_median": float(group_estimates.median()) if len(group_estimates) else np.nan,
                "square_side_mean": float(group_estimates.mean()) if len(group_estimates) else np.nan,
                "square_side_sd": float(group_estimates.std(ddof=1)) if len(group_estimates) > 1 else 0.0,
                "square_side_min": float(group_estimates.min()) if len(group_estimates) else np.nan,
                "square_side_max": float(group_estimates.max()) if len(group_estimates) else np.nan,
                "best_integer_square_side": best_side,
                "best_integer_rmse_px": rmse_px,
                "best_integer_max_abs_error_px": max_abs_error_px,
                "estimated_tolerance_px": best_side * 0.05 if best_side else np.nan,
                "estimated_step_px": max(1, round(best_side * 0.005)) if best_side else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(group_columns).reset_index(drop=True)


def write_report(subject_date: pd.DataFrame, file_summary: pd.DataFrame) -> None:
    grouped_counts = subject_date["best_integer_square_side"].value_counts().sort_index()
    lines = [
        "EP task squareSidePx audit",
        "==========================",
        "",
        "Estimation rule:",
        "- EP source code computes `facebar = round((facevalue / 10) * squareSidePx)`.",
        "- This audit estimates `squareSidePx` from recorded `true_leftBar` / `true_rightBar` and the six EP face values.",
        "- `best_integer_square_side` is the integer square size whose rounded face coordinates best reproduce the recorded targets.",
        f"- Included subjects are restricted to completed-all-task participants: {list(completed_all_task_subject_ids())}.",
        "",
        "Subject-date counts by best integer squareSidePx:",
    ]
    for square_side, count in grouped_counts.items():
        lines.append(f"- {int(square_side)} px: {int(count)} subject-date rows")

    mixed_file_dates = (
        file_summary.groupby(["SubNo", "date"])["best_integer_square_side"]
        .nunique()
        .loc[lambda values: values > 1]
        .reset_index()
    )
    lines.extend(["", "Dates with multiple file-level squareSidePx estimates:"])
    if mixed_file_dates.empty:
        lines.append("- None")
    else:
        for row in mixed_file_dates.itertuples(index=False):
            lines.append(f"- SubNo {int(row.SubNo)}, {row.date}")

    lines.extend(
        [
            "",
            "Outputs:",
            "- `trial_axis_square_side_estimates.csv`: per trial-axis estimates.",
            "- `file_square_side_summary.csv`: per source file estimates.",
            "- `subject_date_square_side_summary.csv`: per subject-date estimates.",
        ]
    )
    (OUTPUT_DIR / "eptask_square_side_audit_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_ep_test_data()
    estimates = estimate_rows(data)
    file_summary = summarize_group(data, estimates, ["SubNo", "date", "source"])
    subject_date = summarize_group(data, estimates, ["SubNo", "date"])

    estimates.to_csv(OUTPUT_DIR / "trial_axis_square_side_estimates.csv", index=False)
    file_summary.to_csv(OUTPUT_DIR / "file_square_side_summary.csv", index=False)
    subject_date.to_csv(OUTPUT_DIR / "subject_date_square_side_summary.csv", index=False)
    write_report(subject_date, file_summary)

    print(f"Wrote {OUTPUT_DIR / 'subject_date_square_side_summary.csv'}")
    print(f"Subject-date rows: {len(subject_date)}")
    print(subject_date["best_integer_square_side"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
