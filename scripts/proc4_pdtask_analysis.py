from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from analysis_common import (
    BAR_DOT_ALPHA,
    BAR_DOT_COLOR,
    BAR_DOT_EDGE_COLOR,
    BAR_EDGE_COLOR,
    BAR_LINEWIDTH,
    BAR_WIDTH,
    CONDITION_PALETTE,
    DATA_DIR as RAW_DATA_DIR,
    FACE_TRUE_RAW,
    PD_RECORDED_FACE_TRUE_400,
    RESULTS_DIR,
    TASK_PALETTE,
    add_true_face_points_0_to_10,
    bar_error_kw,
    bar_scatter_kw,
    coerce_numeric,
    completed_all_task_subject_ids,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    jittered_x,
    load_task_tables,
    paired_test_report,
    pixels_to_true_space,
    raw_pair_condition,
    recode_distance_condition,
    reset_proc_output_dir,
    save_figure,
    setup_true_space_axis,
)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from scipy import stats


DATA_DIR = RAW_DATA_DIR / "PDtask_data"
OUTPUT_DIR = RESULTS_DIR / "proc4_pdtask_analysis"
SUBJECT_FIG_DIR = OUTPUT_DIR / "figures_subject"
GROUP_FIG_DIR = OUTPUT_DIR / "figures_group"

CONDITION_ORDER = ["same", "near", "far", "unknown"]
RAW_QUADRILATERALS = {
    "AB": (1, 2, 3, 4),
    "AC": (1, 2, 5, 6),
    "BC": (3, 4, 5, 6),
}
MATCH_KEY_MAP = {
    frozenset({(1, 2), (3, 4)}): ("AB", "same_edges"),
    frozenset({(1, 4), (2, 3)}): ("AB", "cross_edges"),
    frozenset({(1, 2), (5, 6)}): ("AC", "same_edges"),
    frozenset({(1, 5), (2, 6)}): ("AC", "cross_edges"),
    frozenset({(3, 4), (5, 6)}): ("BC", "same_edges"),
    frozenset({(3, 5), (4, 6)}): ("BC", "cross_edges"),
}
ESTIMATE_ORDER = ["same_edges", "cross_edges"]
ESTIMATE_COLORS = {
    "same_edges": TASK_PALETTE["green"],
    "cross_edges": TASK_PALETTE["blue"],
}
ESTIMATE_MARKERS = {
    "same_edges": "o",
    "cross_edges": "s",
}

LANG = {
    "en": {
        "subject_prefix": "Subject",
        "group_title": "All subjects",
        "title_suffix": "PD midpoint analysis",
        "same_edges": "Same-village edges",
        "cross_edges": "Cross-village edges",
        "matched_trials": "Matched trials",
        "subject_estimate": "Subject median",
        "group_estimate": "Group median",
        "true_center": "True midpoint-of-midpoints",
        "pair_note": {
            "AB": "AB quadrilateral",
            "AC": "AC quadrilateral",
            "BC": "BC quadrilateral",
        },
        "condition_xlabel": "Condition",
        "condition_ylabel": "D error (0-10)",
        "condition_title": "PD distance error by recoded condition",
        "condition_ticklabels": ["same", "near", "far", "unknown"],
    },
    "zh": {
        "subject_prefix": "被试",
        "group_title": "所有被试",
        "title_suffix": "PD 中点分析",
        "same_edges": "同村庄对边",
        "cross_edges": "跨村庄对边",
        "matched_trials": "匹配试次",
        "subject_estimate": "被试中位数",
        "group_estimate": "总体中位数",
        "true_center": "真实对边中点的中点",
        "pair_note": {
            "AB": "AB 四边形",
            "AC": "AC 四边形",
            "BC": "BC 四边形",
        },
        "condition_xlabel": "条件",
        "condition_ylabel": "D 误差（0-10）",
        "condition_title": "PD 任务重编码条件下的 D 误差",
        "condition_ticklabels": ["同村庄", "近", "远", "未知"],
    },
}


@dataclass
class SquareSideInference:
    sub_no: int
    source_date: str
    raw_estimate: float
    square_side_px: int
    scale_to_template_400: float
    rmse_px: float
    max_abs_error_px: float


def order_polygon(points: np.ndarray) -> np.ndarray:
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    return points[np.argsort(angles)]


def recorded_face_vector() -> np.ndarray:
    return np.array([coord for face in range(1, 7) for coord in PD_RECORDED_FACE_TRUE_400[face]], dtype=float)


def face_coordinate_template(subject_df: pd.DataFrame) -> dict[int, tuple[float, float]]:
    coords: dict[int, tuple[float, float]] = {}
    for face in range(1, 7):
        face_coords: list[tuple[float, float]] = []
        for prefix in ["F1", "F2"]:
            face_coords.extend(
                map(
                    tuple,
                    subject_df.loc[
                        subject_df[prefix] == face,
                        [f"{prefix}X", f"{prefix}Y"],
                    ]
                    .dropna()
                    .to_numpy(),
                )
            )
        if not face_coords:
            raise ValueError(f"Missing recorded face coordinates for subject {int(subject_df['SubNo'].iloc[0])}, face {face}")
        coords[face] = tuple(np.median(np.array(face_coords, dtype=float), axis=0))
    return coords


def infer_square_side(subject_df: pd.DataFrame) -> SquareSideInference:
    recorded_template = face_coordinate_template(subject_df)
    observed_vector = np.array([coord for face in range(1, 7) for coord in recorded_template[face]], dtype=float)
    template_vector = recorded_face_vector()

    raw_estimate = float(400.0 * np.dot(observed_vector, template_vector) / np.dot(template_vector, template_vector))
    candidate_sides = np.arange(max(1, int(np.floor(raw_estimate)) - 5), int(np.ceil(raw_estimate)) + 6)
    predicted = np.outer(candidate_sides / 400.0, template_vector)
    errors = predicted - observed_vector
    rmse_by_candidate = np.sqrt(np.mean(errors**2, axis=1))
    best_index = int(np.argmin(rmse_by_candidate))
    square_side_px = int(candidate_sides[best_index])
    source_date = str(subject_df["source_date"].dropna().iloc[0])
    return SquareSideInference(
        sub_no=int(subject_df["SubNo"].iloc[0]),
        source_date=source_date,
        raw_estimate=raw_estimate,
        square_side_px=square_side_px,
        scale_to_template_400=400.0 / square_side_px,
        rmse_px=float(rmse_by_candidate[best_index]),
        max_abs_error_px=float(np.max(np.abs(errors[best_index]))),
    )


def learned_pair_distance(face_a: int, face_b: int) -> float:
    x_a, y_a = FACE_TRUE_RAW[int(face_a)]
    x_b, y_b = FACE_TRUE_RAW[int(face_b)]
    return float(np.hypot(x_a - x_b, y_a - y_b))


def true_center_for_pair(raw_village_pair: str) -> tuple[float, float]:
    points = np.array([FACE_TRUE_RAW[face] for face in RAW_QUADRILATERALS[raw_village_pair]], dtype=float)
    center = points.mean(axis=0)
    return float(center[0]), float(center[1])


def load_pd_trials() -> pd.DataFrame:
    df = load_task_tables(DATA_DIR, "PDtask-")
    numeric_columns = [
        "SubNo",
        "F1",
        "F2",
        "F1V",
        "F2V",
        "F1X",
        "F1Y",
        "F2X",
        "F2Y",
        "D",
        "MidX",
        "MidY",
        "Mtask",
        "DX",
        "DY",
        "ans_D",
        "MX",
        "MY",
        "MMX",
        "MMY",
    ]
    df = coerce_numeric(df, numeric_columns)
    missing_d = df["D"].isna()
    if missing_d.any():
        df.loc[missing_d, "D"] = np.hypot(
            df.loc[missing_d, "F1X"] - df.loc[missing_d, "F2X"],
            df.loc[missing_d, "F1Y"] - df.loc[missing_d, "F2Y"],
        )

    df = df.dropna(subset=["SubNo", "F1", "F2", "F1V", "F2V"]).copy()
    df["SubNo"] = df["SubNo"].astype(int)
    df["F1"] = df["F1"].astype(int)
    df["F2"] = df["F2"].astype(int)
    df["F1V"] = df["F1V"].astype(int)
    df["F2V"] = df["F2V"].astype(int)
    df = filter_excluded_subjects(df)
    df = filter_completed_subjects(df)
    df["source_date"] = df["source"].str.extract(r"(\d{4}-\d{2}-\d{2})")
    df["trial_index"] = df.groupby(["SubNo", "source"], sort=False).cumcount() + 1
    return df


def prepare_trials(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scale_rows = []
    for (_, _), subject_df in raw_df.groupby(["SubNo", "source_date"], sort=True):
        inference = infer_square_side(subject_df)
        scale_rows.append(
            {
                "SubNo": inference.sub_no,
                "source_date": inference.source_date,
                "raw_estimate": inference.raw_estimate,
                "square_side_px": inference.square_side_px,
                "scale_to_template_400": inference.scale_to_template_400,
                "rmse_px": inference.rmse_px,
                "max_abs_error_px": inference.max_abs_error_px,
            }
        )
    scale_df = pd.DataFrame(scale_rows).sort_values(["SubNo", "source_date"]).reset_index(drop=True)

    df = raw_df.merge(scale_df, on=["SubNo", "source_date"], how="left", validate="many_to_one")
    coord_columns = ["F1X", "F1Y", "F2X", "F2Y", "MidX", "MidY", "MX", "MY", "MMX", "MMY", "DX", "DY", "D", "ans_D"]
    for column in coord_columns:
        df[f"{column}_0to10"] = pixels_to_true_space(df[column], df["square_side_px"])

    df["raw_condition"] = [raw_pair_condition(a, b) for a, b in zip(df["F1V"], df["F2V"])]
    df = df.dropna(subset=["raw_condition"]).copy()
    df["condition"] = [recode_distance_condition(sub_no, cond) for sub_no, cond in zip(df["SubNo"], df["raw_condition"])]
    df["relationship"] = np.where(df["condition"] == "same", "same", "different")
    df["distance_nested"] = df["condition"].where(df["condition"] != "same")
    df["learned_D_0to10"] = [learned_pair_distance(face_a, face_b) for face_a, face_b in zip(df["F1"], df["F2"])]
    df["d_error_0to10"] = df["ans_D_0to10"] - df["learned_D_0to10"]
    df["pair_label"] = [f"{min(face_a, face_b)}-{max(face_a, face_b)}" for face_a, face_b in zip(df["F1"], df["F2"])]
    return df, scale_df


def subject_cell_means(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return (
        df.groupby(["SubNo", *columns], as_index=False)["d_error_0to10"]
        .agg(d_error_0to10="mean", n_trials="size")
        .sort_values(["SubNo", *columns])
    )


def paired_contrast_rows(
    data: pd.DataFrame,
    within: str,
    comparisons: list[tuple[str, str, str]],
    scope: str,
) -> pd.DataFrame:
    wide = data.pivot(index="SubNo", columns=within, values="d_error_0to10")
    rows = []
    for contrast_label, a_label, b_label in comparisons:
        if a_label not in wide.columns or b_label not in wide.columns:
            rows.append(
                {
                    "scope": scope,
                    "contrast": contrast_label,
                    "n_subjects": 0,
                    "method": "not available",
                    "mean_diff": np.nan,
                    "sd_diff": np.nan,
                    "normality_shapiro_p": np.nan,
                    "statistic": np.nan,
                    "p_value": np.nan,
                }
            )
            continue
        result = paired_test_report(wide[a_label], wide[b_label], a_label, b_label)
        rows.append(
            {
                "scope": scope,
                "contrast": contrast_label,
                "n_subjects": result["n_subjects"],
                "method": result["method"],
                "mean_diff": result["mean_difference"],
                "sd_diff": result["sd_difference"],
                "normality_shapiro_p": result["normality_shapiro_p"],
                "statistic": result["statistic"],
                "p_value": result["p_value"],
            }
        )
    return pd.DataFrame(rows)


def summarize_d_error(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    subject_condition = subject_cell_means(df, ["condition"])
    relationship_means = subject_cell_means(df, ["relationship"])
    distance_nested_means = subject_cell_means(df[df["relationship"] == "different"].copy(), ["distance_nested"])
    trial_summary = (
        df.groupby("condition", as_index=False)["d_error_0to10"]
        .agg(n_trials="size", mean="mean", sd="std")
        .assign(se=lambda x: x["sd"] / np.sqrt(x["n_trials"]))
    )
    subject_summary = (
        subject_condition.groupby("condition", as_index=False)["d_error_0to10"]
        .agg(n_subjects="size", mean="mean", sd="std")
        .assign(se=lambda x: x["sd"] / np.sqrt(x["n_subjects"]))
    )
    planned_contrasts = pd.concat(
        [
            paired_contrast_rows(
                relationship_means,
                "relationship",
                [("different - same", "different", "same")],
                "relationship",
            ),
            paired_contrast_rows(
                distance_nested_means,
                "distance_nested",
                [
                    ("far - near", "far", "near"),
                    ("unknown - near", "unknown", "near"),
                    ("unknown - far", "unknown", "far"),
                ],
                "nested_distance",
            ),
            paired_contrast_rows(
                subject_condition,
                "condition",
                [
                    ("near - same", "near", "same"),
                    ("far - same", "far", "same"),
                    ("unknown - same", "unknown", "same"),
                    ("far - near", "far", "near"),
                    ("unknown - near", "unknown", "near"),
                    ("unknown - far", "unknown", "far"),
                ],
                "condition",
            ),
        ],
        ignore_index=True,
    )
    return {
        "subject_condition": subject_condition,
        "relationship_means": relationship_means,
        "distance_nested_means": distance_nested_means,
        "trial_summary": trial_summary,
        "subject_summary": subject_summary,
        "planned_contrasts": planned_contrasts,
    }


def save_condition_figure(subject_condition: pd.DataFrame, labels: str) -> None:
    label_map = LANG[labels]
    GROUP_FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    summary = (
        subject_condition.groupby("condition")["d_error_0to10"]
        .agg(n_subjects="count", mean="mean", sd="std")
        .reindex(CONDITION_ORDER)
        .reset_index()
    )
    summary["se"] = summary["sd"] / np.sqrt(summary["n_subjects"])
    positions = np.arange(len(CONDITION_ORDER))
    ax.bar(
        positions,
        summary["mean"].fillna(0).to_numpy(dtype=float),
        yerr=summary["se"].fillna(0).to_numpy(dtype=float),
        color=[CONDITION_PALETTE[condition] for condition in CONDITION_ORDER],
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_LINEWIDTH,
        width=BAR_WIDTH,
        error_kw=bar_error_kw(),
        zorder=2,
    )
    rng = np.random.default_rng(20260418)
    for position, condition in zip(positions, CONDITION_ORDER):
        values = subject_condition.loc[subject_condition["condition"] == condition, "d_error_0to10"].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            continue
        ax.scatter(
            jittered_x(position, len(values), rng),
            values,
            **bar_scatter_kw(),
            zorder=3,
        )
    ax.axhline(0.0, color="#111827", linewidth=0.9, linestyle="--", alpha=0.7)
    ax.set_xlabel(label_map["condition_xlabel"])
    ax.set_ylabel(label_map["condition_ylabel"])
    ax.set_xticks(range(len(CONDITION_ORDER)), labels=label_map["condition_ticklabels"])
    ax.set_title(label_map["condition_title"])
    plt.tight_layout()
    save_figure(fig, GROUP_FIG_DIR, f"d_error_condition_{labels}")


def save_subject_condition_figure(trial_df: pd.DataFrame, subject_condition: pd.DataFrame, sub_no: int, labels: str) -> None:
    label_map = LANG[labels]
    subject_trials = trial_df.loc[trial_df["SubNo"] == sub_no].copy()
    subject_means = subject_condition.loc[subject_condition["SubNo"] == sub_no].copy()
    if subject_trials.empty or subject_means.empty:
        return

    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    sns.barplot(
        data=subject_means,
        x="condition",
        y="d_error_0to10",
        order=CONDITION_ORDER,
        estimator="mean",
        errorbar=None,
        hue="condition",
        palette={condition: CONDITION_PALETTE[condition] for condition in CONDITION_ORDER},
        legend=False,
        width=BAR_WIDTH,
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_LINEWIDTH,
        ax=ax,
    )
    sns.stripplot(
        data=subject_trials,
        x="condition",
        y="d_error_0to10",
        order=CONDITION_ORDER,
        color=BAR_DOT_COLOR,
        jitter=0.12,
        size=4.2,
        alpha=BAR_DOT_ALPHA,
        edgecolor=BAR_DOT_EDGE_COLOR,
        linewidth=0.35,
        ax=ax,
    )
    ax.axhline(0.0, color="#111827", linewidth=0.9, linestyle="--", alpha=0.7)
    ax.set_xlabel(label_map["condition_xlabel"])
    ax.set_ylabel(label_map["condition_ylabel"])
    ax.set_xticks(range(len(CONDITION_ORDER)), labels=label_map["condition_ticklabels"])
    ax.set_title(f"{label_map['subject_prefix']} {sub_no:02d} · {label_map['condition_title']}")
    plt.tight_layout()
    save_figure(fig, SUBJECT_FIG_DIR, f"sub-{sub_no:02d}_d_error_condition_{labels}")


def save_subject_condition_figures(trial_df: pd.DataFrame, subject_condition: pd.DataFrame) -> None:
    SUBJECT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for sub_no in sorted(subject_condition["SubNo"].unique()):
        for labels in ["zh", "en"]:
            save_subject_condition_figure(trial_df, subject_condition, int(sub_no), labels)


def build_varignon_matches(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (_, source_date), subject_df in df.groupby(["SubNo", "source_date"], sort=True):
        subject_df = subject_df.sort_values(["source", "trial_index"]).reset_index(drop=True)
        for row_index in range(1, len(subject_df)):
            previous = subject_df.iloc[row_index - 1]
            current = subject_df.iloc[row_index]
            if previous["Mtask"] != 1 or current["Mtask"] != 2:
                continue

            pair_set = frozenset(
                {
                    tuple(sorted((int(previous["F1"]), int(previous["F2"])))),
                    tuple(sorted((int(current["F1"]), int(current["F2"])))),
                }
            )
            mapped = MATCH_KEY_MAP.get(pair_set)
            if mapped is None or pd.isna(current["MMX_0to10"]) or pd.isna(current["MMY_0to10"]):
                continue

            raw_village_pair, estimate_type = mapped
            pair_condition = recode_distance_condition(int(current["SubNo"]), raw_village_pair)
            true_center_x, true_center_y = true_center_for_pair(raw_village_pair)
            derived_center_x = float(np.nanmean([previous["MX_0to10"], current["MX_0to10"]]))
            derived_center_y = float(np.nanmean([previous["MY_0to10"], current["MY_0to10"]]))
            rows.append(
                {
                    "SubNo": int(current["SubNo"]),
                    "source_date": source_date,
                    "prev_trial_index": int(previous["trial_index"]),
                    "trial_index": int(current["trial_index"]),
                    "raw_village_pair": raw_village_pair,
                    "pair_condition": pair_condition,
                    "estimate_type": estimate_type,
                    "prev_pair_label": f"{min(previous['F1'], previous['F2'])}-{max(previous['F1'], previous['F2'])}",
                    "current_pair_label": f"{min(current['F1'], current['F2'])}-{max(current['F1'], current['F2'])}",
                    "center_x_0to10": float(current["MMX_0to10"]),
                    "center_y_0to10": float(current["MMY_0to10"]),
                    "prev_mid_x_0to10": float(previous["MX_0to10"]),
                    "prev_mid_y_0to10": float(previous["MY_0to10"]),
                    "current_mid_x_0to10": float(current["MX_0to10"]),
                    "current_mid_y_0to10": float(current["MY_0to10"]),
                    "derived_center_x_0to10": derived_center_x,
                    "derived_center_y_0to10": derived_center_y,
                    "true_center_x": true_center_x,
                    "true_center_y": true_center_y,
                    "distance_to_true": float(
                        np.hypot(current["MMX_0to10"] - true_center_x, current["MMY_0to10"] - true_center_y)
                    ),
                    "distance_to_derived": float(
                        np.hypot(current["MMX_0to10"] - derived_center_x, current["MMY_0to10"] - derived_center_y)
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["SubNo", "raw_village_pair", "estimate_type", "trial_index"]).reset_index(
        drop=True
    )


def aggregate_subject_centers(match_df: pd.DataFrame) -> pd.DataFrame:
    if match_df.empty:
        return pd.DataFrame()
    return (
        match_df.groupby(["SubNo", "raw_village_pair", "pair_condition", "estimate_type"], as_index=False)
        .agg(
            n_matches=("trial_index", "size"),
            center_x_0to10=("center_x_0to10", "median"),
            center_y_0to10=("center_y_0to10", "median"),
            distance_to_true=("distance_to_true", "median"),
            distance_to_derived=("distance_to_derived", "median"),
            true_center_x=("true_center_x", "first"),
            true_center_y=("true_center_y", "first"),
        )
        .sort_values(["SubNo", "raw_village_pair", "estimate_type"])
        .reset_index(drop=True)
    )


def summarize_group_centers(subject_centers: pd.DataFrame) -> pd.DataFrame:
    if subject_centers.empty:
        return pd.DataFrame()
    return (
        subject_centers.groupby(["raw_village_pair", "pair_condition", "estimate_type"], as_index=False)
        .agg(
            n_subjects=("SubNo", "size"),
            mean_center_x_0to10=("center_x_0to10", "mean"),
            mean_center_y_0to10=("center_y_0to10", "mean"),
            median_center_x_0to10=("center_x_0to10", "median"),
            median_center_y_0to10=("center_y_0to10", "median"),
            mean_distance_to_true=("distance_to_true", "mean"),
            median_distance_to_true=("distance_to_true", "median"),
        )
        .sort_values(["raw_village_pair", "estimate_type"])
        .reset_index(drop=True)
    )


def safe_paired_test(values_a: pd.Series, values_b: pd.Series, label_a: str, label_b: str) -> dict[str, float | str | int]:
    paired = pd.concat([values_a.rename(label_a), values_b.rename(label_b)], axis=1).dropna()
    if paired.empty:
        return {
            "comparison": f"{label_a} - {label_b}",
            "n_subjects": 0,
            "method": "not available",
            "mean_difference": np.nan,
            "sd_difference": np.nan,
            "normality_shapiro_p": np.nan,
            "statistic": np.nan,
            "p_value": np.nan,
        }
    diff = paired[label_a] - paired[label_b]
    if np.allclose(diff.to_numpy(), 0.0):
        return {
            "comparison": f"{label_a} - {label_b}",
            "n_subjects": int(len(paired)),
            "method": "all differences zero",
            "mean_difference": 0.0,
            "sd_difference": 0.0,
            "normality_shapiro_p": np.nan,
            "statistic": 0.0,
            "p_value": 1.0,
        }
    return paired_test_report(paired[label_a], paired[label_b], label_a, label_b)


def paired_axis_tests(subject_centers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if subject_centers.empty:
        return pd.DataFrame(), pd.DataFrame()

    wide = (
        subject_centers.pivot_table(
            index=["SubNo", "raw_village_pair", "pair_condition"],
            columns="estimate_type",
            values=["center_x_0to10", "center_y_0to10", "distance_to_true"],
        )
        .sort_index()
        .reset_index()
    )
    wide.columns = ["_".join(col).strip("_") for col in wide.columns.to_flat_index()]
    wide["center_distance"] = np.hypot(
        wide["center_x_0to10_cross_edges"] - wide["center_x_0to10_same_edges"],
        wide["center_y_0to10_cross_edges"] - wide["center_y_0to10_same_edges"],
    )

    rows = []
    distance_rows = []
    for scope_name, group_column in [("raw_village_pair", "raw_village_pair"), ("pair_condition", "pair_condition")]:
        for group_value, group_df in wide.groupby(group_column, sort=False):
            for metric in ["center_x_0to10", "center_y_0to10", "distance_to_true"]:
                result = safe_paired_test(
                    group_df[f"{metric}_cross_edges"],
                    group_df[f"{metric}_same_edges"],
                    "cross_edges",
                    "same_edges",
                )
                result.update({"scope": scope_name, "group": group_value, "metric": metric})
                rows.append(result)
            distance_rows.append(
                {
                    "scope": scope_name,
                    "group": group_value,
                    "n_subjects": int(group_df.shape[0]),
                    "mean_center_distance": float(group_df["center_distance"].mean()),
                    "median_center_distance": float(group_df["center_distance"].median()),
                    "sd_center_distance": float(group_df["center_distance"].std(ddof=1)),
                }
            )

    return pd.DataFrame(rows), pd.DataFrame(distance_rows)


def sign_flip_vector_test(differences: np.ndarray, *, n_permutations: int = 20000, seed: int = 20260418) -> dict[str, float | int | str]:
    differences = np.asarray(differences, dtype=float)
    differences = differences[~np.isnan(differences).any(axis=1)]
    n_subjects = int(differences.shape[0])
    if n_subjects == 0:
        return {
            "method": "not available",
            "n_subjects": 0,
            "observed_mean_norm": np.nan,
            "mean_dx": np.nan,
            "mean_dy": np.nan,
            "p_value": np.nan,
            "n_permutations": 0,
        }
    observed_mean = differences.mean(axis=0)
    observed_norm = float(np.linalg.norm(observed_mean))
    if np.allclose(differences, 0.0):
        return {
            "method": "sign-flip exact",
            "n_subjects": n_subjects,
            "observed_mean_norm": 0.0,
            "mean_dx": 0.0,
            "mean_dy": 0.0,
            "p_value": 1.0,
            "n_permutations": 1,
        }

    if n_subjects <= 14:
        sign_matrix = 1 - 2 * (((np.arange(2**n_subjects)[:, None]) >> np.arange(n_subjects)) & 1)
        method = "sign-flip exact"
    else:
        rng = np.random.default_rng(seed)
        sign_matrix = rng.choice([-1, 1], size=(n_permutations, n_subjects))
        method = "sign-flip Monte Carlo"

    permuted_means = (sign_matrix[:, :, None] * differences[None, :, :]).mean(axis=1)
    permuted_norms = np.linalg.norm(permuted_means, axis=1)
    p_value = float((np.count_nonzero(permuted_norms >= observed_norm) + 1) / (len(permuted_norms) + 1))
    return {
        "method": method,
        "n_subjects": n_subjects,
        "observed_mean_norm": observed_norm,
        "mean_dx": float(observed_mean[0]),
        "mean_dy": float(observed_mean[1]),
        "p_value": p_value,
        "n_permutations": int(len(permuted_norms)),
    }


def near_varignon_tests(subject_centers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if subject_centers.empty:
        return pd.DataFrame(), pd.DataFrame()

    near = subject_centers.loc[subject_centers["pair_condition"] == "near"].copy()
    wide = (
        near.pivot_table(
            index="SubNo",
            columns="estimate_type",
            values=["center_x_0to10", "center_y_0to10", "distance_to_true"],
        )
        .sort_index()
        .reset_index()
    )
    if wide.empty:
        return pd.DataFrame(), pd.DataFrame()

    wide.columns = ["_".join(col).strip("_") for col in wide.columns.to_flat_index()]
    differences = wide[
        [
            "center_x_0to10_cross_edges",
            "center_y_0to10_cross_edges",
        ]
    ].to_numpy() - wide[
        [
            "center_x_0to10_same_edges",
            "center_y_0to10_same_edges",
        ]
    ].to_numpy()
    sign_flip_df = pd.DataFrame([sign_flip_vector_test(differences)])
    axis_tests = pd.DataFrame(
        [
            safe_paired_test(wide["center_x_0to10_cross_edges"], wide["center_x_0to10_same_edges"], "cross_edges", "same_edges")
            | {"metric": "center_x_0to10"},
            safe_paired_test(wide["center_y_0to10_cross_edges"], wide["center_y_0to10_same_edges"], "cross_edges", "same_edges")
            | {"metric": "center_y_0to10"},
            safe_paired_test(wide["distance_to_true_cross_edges"], wide["distance_to_true_same_edges"], "cross_edges", "same_edges")
            | {"metric": "distance_to_true"},
        ]
    )
    return sign_flip_df, axis_tests


def draw_background(ax: plt.Axes, raw_village_pair: str, labels: str) -> None:
    quadrilateral_points = np.array([FACE_TRUE_RAW[face] for face in RAW_QUADRILATERALS[raw_village_pair]], dtype=float)
    polygon = Polygon(
        order_polygon(quadrilateral_points),
        closed=True,
        facecolor="#D1D5DB",
        edgecolor="#4B5563",
        linewidth=1.2,
        alpha=0.24,
        zorder=1,
    )
    ax.add_patch(polygon)
    add_true_face_points_0_to_10(ax, labels=labels, size=54, marker="X", zorder=5)
    true_x, true_y = true_center_for_pair(raw_village_pair)
    ax.scatter(
        true_x,
        true_y,
        s=120,
        marker="P",
        color="#111827",
        edgecolor="white",
        linewidth=0.8,
        zorder=7,
    )
    ax.text(
        true_x + 0.15,
        true_y - 0.22,
        LANG[labels]["true_center"],
        fontsize=8,
        color="#111827",
        zorder=8,
    )
    setup_true_space_axis(ax, labels=labels)


def figure_title(sub_no: int | None, raw_village_pair: str, labels: str) -> str:
    label_map = LANG[labels]
    pair_note = label_map["pair_note"][raw_village_pair]
    if sub_no is None:
        return f"{label_map['group_title']} · {pair_note} · {label_map['title_suffix']}"
    return f"{label_map['subject_prefix']} {sub_no:02d} · {pair_note} · {label_map['title_suffix']}"


def legend_handles(labels: str, include_group: bool) -> list[Line2D]:
    handles = [
        Line2D(
            [0],
            [0],
            marker="P",
            color="none",
            markerfacecolor="#111827",
            markeredgecolor="white",
            markersize=9,
            label=LANG[labels]["true_center"],
        )
    ]
    for estimate_type in ESTIMATE_ORDER:
        handles.append(
            Line2D(
                [0],
                [0],
                marker=ESTIMATE_MARKERS[estimate_type],
                color="none",
                markerfacecolor=ESTIMATE_COLORS[estimate_type],
                markeredgecolor="#1F2933",
                markersize=8,
                alpha=0.8,
                label=f"{LANG[labels][estimate_type]} · {LANG[labels]['matched_trials']}",
            )
        )
        handles.append(
            Line2D(
                [0],
                [0],
                marker=ESTIMATE_MARKERS[estimate_type],
                color="none",
                markerfacecolor=ESTIMATE_COLORS[estimate_type],
                markeredgecolor="#111827",
                markersize=10,
                label=f"{LANG[labels][estimate_type]} · {LANG[labels]['subject_estimate']}",
            )
        )
        if include_group:
            handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="D",
                    color="none",
                    markerfacecolor=ESTIMATE_COLORS[estimate_type],
                    markeredgecolor="#111827",
                    markersize=10,
                    label=f"{LANG[labels][estimate_type]} · {LANG[labels]['group_estimate']}",
                )
            )
    return handles


def plot_subject_figure(raw_village_pair: str, trial_points: pd.DataFrame, subject_points: pd.DataFrame, sub_no: int, labels: str) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 6.1))
    draw_background(ax, raw_village_pair, labels)

    for estimate_type in ESTIMATE_ORDER:
        trial_subset = trial_points.loc[trial_points["estimate_type"] == estimate_type]
        subject_subset = subject_points.loc[subject_points["estimate_type"] == estimate_type]
        ax.scatter(
            trial_subset["center_x_0to10"],
            trial_subset["center_y_0to10"],
            s=42,
            marker=ESTIMATE_MARKERS[estimate_type],
            color=ESTIMATE_COLORS[estimate_type],
            edgecolor="#1F2933",
            linewidth=0.5,
            alpha=0.35,
            zorder=3,
        )
        ax.scatter(
            subject_subset["center_x_0to10"],
            subject_subset["center_y_0to10"],
            s=98,
            marker=ESTIMATE_MARKERS[estimate_type],
            color=ESTIMATE_COLORS[estimate_type],
            edgecolor="#111827",
            linewidth=1.0,
            alpha=0.95,
            zorder=6,
        )

    ax.set_title(figure_title(sub_no, raw_village_pair, labels))
    ax.legend(handles=legend_handles(labels, include_group=False), loc="upper left", fontsize=8)
    save_figure(fig, SUBJECT_FIG_DIR, f"sub-{sub_no:02d}_{raw_village_pair.lower()}_{labels}")


def plot_group_figure(raw_village_pair: str, subject_points: pd.DataFrame, labels: str) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 6.2))
    draw_background(ax, raw_village_pair, labels)

    for estimate_type in ESTIMATE_ORDER:
        subset = subject_points.loc[subject_points["estimate_type"] == estimate_type]
        ax.scatter(
            subset["center_x_0to10"],
            subset["center_y_0to10"],
            s=62,
            marker=ESTIMATE_MARKERS[estimate_type],
            color=ESTIMATE_COLORS[estimate_type],
            edgecolor="#1F2933",
            linewidth=0.6,
            alpha=0.62,
            zorder=4,
        )
        if not subset.empty:
            ax.scatter(
                subset["center_x_0to10"].median(),
                subset["center_y_0to10"].median(),
                s=118,
                marker="D",
                color=ESTIMATE_COLORS[estimate_type],
                edgecolor="#111827",
                linewidth=1.0,
                zorder=6,
            )

    ax.set_title(figure_title(None, raw_village_pair, labels))
    ax.legend(handles=legend_handles(labels, include_group=True), loc="upper left", fontsize=8)
    save_figure(fig, GROUP_FIG_DIR, f"group_{raw_village_pair.lower()}_{labels}")


def save_varignon_figures(match_df: pd.DataFrame, subject_centers: pd.DataFrame) -> None:
    SUBJECT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    GROUP_FIG_DIR.mkdir(parents=True, exist_ok=True)

    for (sub_no, raw_village_pair), subject_trials in match_df.groupby(["SubNo", "raw_village_pair"], sort=True):
        subject_points = subject_centers.loc[
            (subject_centers["SubNo"] == sub_no) & (subject_centers["raw_village_pair"] == raw_village_pair)
        ]
        for labels in ["zh", "en"]:
            plot_subject_figure(raw_village_pair, subject_trials, subject_points, int(sub_no), labels)

    for raw_village_pair, pair_points in subject_centers.groupby("raw_village_pair", sort=True):
        for labels in ["zh", "en"]:
            plot_group_figure(raw_village_pair, pair_points, labels)


def save_tables(
    scale_df: pd.DataFrame,
    trial_df: pd.DataFrame,
    d_error_outputs: dict[str, pd.DataFrame],
    match_df: pd.DataFrame,
    subject_centers: pd.DataFrame,
    group_summary: pd.DataFrame,
    axis_tests: pd.DataFrame,
    center_distance_summary: pd.DataFrame,
    near_sign_flip: pd.DataFrame,
    near_axis_tests: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scale_df.to_csv(OUTPUT_DIR / "subject_square_side_inference.csv", index=False)
    trial_df.to_csv(OUTPUT_DIR / "normalized_pd_trials.csv", index=False)
    d_error_outputs["subject_condition"].to_csv(OUTPUT_DIR / "d_error_subject_condition_means.csv", index=False)
    d_error_outputs["relationship_means"].to_csv(OUTPUT_DIR / "d_error_subject_relationship_means.csv", index=False)
    d_error_outputs["distance_nested_means"].to_csv(OUTPUT_DIR / "d_error_subject_distance_nested_means.csv", index=False)
    d_error_outputs["trial_summary"].to_csv(OUTPUT_DIR / "d_error_trial_summary.csv", index=False)
    d_error_outputs["subject_summary"].to_csv(OUTPUT_DIR / "d_error_subject_summary.csv", index=False)
    d_error_outputs["planned_contrasts"].to_csv(OUTPUT_DIR / "d_error_planned_contrasts.csv", index=False)
    match_df.to_csv(OUTPUT_DIR / "varignon_trial_matches.csv", index=False)
    subject_centers.to_csv(OUTPUT_DIR / "varignon_subject_centers.csv", index=False)
    group_summary.to_csv(OUTPUT_DIR / "varignon_group_summary.csv", index=False)
    axis_tests.to_csv(OUTPUT_DIR / "varignon_axis_paired_tests.csv", index=False)
    center_distance_summary.to_csv(OUTPUT_DIR / "varignon_center_distance_summary.csv", index=False)
    near_sign_flip.to_csv(OUTPUT_DIR / "varignon_near_signflip_test.csv", index=False)
    near_axis_tests.to_csv(OUTPUT_DIR / "varignon_near_axis_tests.csv", index=False)


def write_report(
    scale_df: pd.DataFrame,
    d_error_outputs: dict[str, pd.DataFrame],
    match_df: pd.DataFrame,
    subject_centers: pd.DataFrame,
    axis_tests: pd.DataFrame,
    center_distance_summary: pd.DataFrame,
    near_sign_flip: pd.DataFrame,
    near_axis_tests: pd.DataFrame,
) -> None:
    lines = [
        "proc4 PD task analysis",
        "======================",
        "",
        "Design note",
        "-----------",
        "Odd/even recoding is applied before every summary and statistical test:",
        "- odd SubNo: AB -> near, AC -> far",
        "- even SubNo: AC -> near, AB -> far",
        "- BC remains the structurally nested different-village unknown condition",
        "The PD task is treated as a nested design; no independent village or distance main effect is reported.",
        "",
        "Coordinate normalization",
        "------------------------",
        "PD_RECORDED_FACE_TRUE_400 is used only to infer each subject's recorded squareSidePx.",
        "All recorded PD coordinates and distances are rescaled to the shared 0-10 space before aggregation, plotting, or statistics.",
        "True geometry for all PD plots and learned D references comes from FACE_TRUE_RAW.",
        f"Included subject pool follows completed-all-task participants: {list(completed_all_task_subject_ids())}.",
        "",
        "Square-side inference",
        "---------------------",
        *scale_df.to_string(index=False, float_format=lambda value: f'{value:.4f}').splitlines(),
        "",
        "D-error subject summary",
        "-----------------------",
        *d_error_outputs["subject_summary"].to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        "D-error planned contrasts",
        "-------------------------",
        *d_error_outputs["planned_contrasts"].to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        "Varignon matched-trial counts",
        "-----------------------------",
        *(
            match_df.groupby(["raw_village_pair", "pair_condition", "estimate_type"])
            .size()
            .rename("n_trials")
            .reset_index()
            .to_string(index=False)
            .splitlines()
            if not match_df.empty
            else ["No matched Varignon trials found."]
        ),
        "",
        "Varignon subject centers",
        "------------------------",
        *(
            subject_centers.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines()
            if not subject_centers.empty
            else ["No subject-level Varignon centers found."]
        ),
        "",
        "Varignon axis-wise paired tests",
        "-------------------------------",
        *(
            axis_tests.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines()
            if not axis_tests.empty
            else ["No paired tests available."]
        ),
        "",
        "Varignon center-distance summary",
        "--------------------------------",
        *(
            center_distance_summary.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines()
            if not center_distance_summary.empty
            else ["No center-distance summary available."]
        ),
        "",
        "Near-condition Varignon test",
        "----------------------------",
        "Question: do the two Varignon midpoint estimates differ in the recoded near condition?",
        *(
            near_sign_flip.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines()
            if not near_sign_flip.empty
            else ["No near-condition sign-flip result available."]
        ),
        "",
        "Near-condition supporting axis tests",
        "------------------------------------",
        *(
            near_axis_tests.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines()
            if not near_axis_tests.empty
            else ["No near-condition axis test available."]
        ),
    ]
    (OUTPUT_DIR / "stats_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    reset_proc_output_dir(OUTPUT_DIR)
    configure_plot_style("paper")
    plt.rcParams["font.family"] = ["Arial Unicode MS", "DejaVu Sans", "Arial"]
    plt.rcParams["axes.unicode_minus"] = False

    raw_df = load_pd_trials()
    trial_df, scale_df = prepare_trials(raw_df)
    d_error_outputs = summarize_d_error(trial_df)
    match_df = build_varignon_matches(trial_df)
    subject_centers = aggregate_subject_centers(match_df)
    group_summary = summarize_group_centers(subject_centers)
    axis_tests, center_distance_summary = paired_axis_tests(subject_centers)
    near_sign_flip, near_axis_tests = near_varignon_tests(subject_centers)

    save_tables(
        scale_df=scale_df,
        trial_df=trial_df,
        d_error_outputs=d_error_outputs,
        match_df=match_df,
        subject_centers=subject_centers,
        group_summary=group_summary,
        axis_tests=axis_tests,
        center_distance_summary=center_distance_summary,
        near_sign_flip=near_sign_flip,
        near_axis_tests=near_axis_tests,
    )
    for labels in ["zh", "en"]:
        save_condition_figure(d_error_outputs["subject_condition"], labels)
    save_subject_condition_figures(trial_df, d_error_outputs["subject_condition"])
    if not match_df.empty and not subject_centers.empty:
        save_varignon_figures(match_df, subject_centers)
    write_report(
        scale_df=scale_df,
        d_error_outputs=d_error_outputs,
        match_df=match_df,
        subject_centers=subject_centers,
        axis_tests=axis_tests,
        center_distance_summary=center_distance_summary,
        near_sign_flip=near_sign_flip,
        near_axis_tests=near_axis_tests,
    )


if __name__ == "__main__":
    main()
