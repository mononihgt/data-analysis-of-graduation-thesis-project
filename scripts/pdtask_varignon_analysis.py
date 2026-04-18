from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from analysis_common import (
    completed_all_task_subject_ids,
    DATA_DIR,
    FACE_TRUE_400,
    PD_RECORDED_FACE_TRUE_400,
    TASK_PALETTE,
    coerce_numeric,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    load_task_tables,
    paired_test_report,
    raw_pair_condition,
    recode_distance_condition,
    save_figure,
    setup_square_axis,
)
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "results" / "pdtask_varignon_analysis"
SUBJECT_FIG_DIR = OUTPUT_DIR / "figures_subject"
GROUP_FIG_DIR = OUTPUT_DIR / "figures_group"
DATA_PATH = DATA_DIR / "PDtask_data"

RAW_QUADRILATERALS = {
    "AB": (1, 2, 3, 4),
    "AC": (1, 2, 5, 6),
    "BC": (3, 4, 5, 6),
}
KEY_PAIR_MAP = {
    frozenset({(1, 2), (3, 4)}): ("AB", "same_edges"),
    frozenset({(1, 4), (2, 3)}): ("AB", "cross_edges"),
    frozenset({(1, 2), (5, 6)}): ("AC", "same_edges"),
    frozenset({(1, 5), (2, 6)}): ("AC", "cross_edges"),
    frozenset({(3, 4), (5, 6)}): ("BC", "same_edges"),
    frozenset({(3, 5), (4, 6)}): ("BC", "cross_edges"),
}
CONSTRUCTION_COLORS = {
    "same_edges": TASK_PALETTE["green"],
    "cross_edges": TASK_PALETTE["blue"],
}
CONSTRUCTION_MARKERS = {
    "same_edges": "o",
    "cross_edges": "s",
}
LANG = {
    "en": {
        "subject_prefix": "Subject",
        "group_title": "All subjects",
        "title_suffix": "Varignon midpoint analysis",
        "same_edges": "Same-village edges",
        "cross_edges": "Cross-village edges",
        "trial_points": "Matched trials",
        "subject_median": "Subject median",
        "group_median": "Group median",
        "true_center": "True Varignon center",
        "pair_note": {
            "AB": "AB quadrilateral",
            "AC": "AC quadrilateral",
            "BC": "BC quadrilateral",
        },
    },
    "zh": {
        "subject_prefix": "被试",
        "group_title": "所有被试",
        "title_suffix": "Varignon 中点分析",
        "same_edges": "同村庄对边",
        "cross_edges": "跨村庄对边",
        "trial_points": "匹配试次",
        "subject_median": "被试中位数",
        "group_median": "总体中位数",
        "true_center": "真实 Varignon 中心",
        "pair_note": {
            "AB": "AB 四边形",
            "AC": "AC 四边形",
            "BC": "BC 四边形",
        },
    },
}


def recorded_face_vector() -> np.ndarray:
    return np.array([coord for face in range(1, 7) for coord in PD_RECORDED_FACE_TRUE_400[face]], dtype=float)


def order_polygon(points: np.ndarray) -> np.ndarray:
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    return points[np.argsort(angles)]


def add_learned_true_face_points(ax: plt.Axes, *, labels: str = "en") -> None:
    for face, (x_coord, y_coord) in FACE_TRUE_400.items():
        ax.scatter(
            x_coord,
            y_coord,
            s=56,
            marker="X",
            color=TASK_PALETTE["gray"],
            edgecolor="#1F2933",
            linewidth=0.8,
            zorder=5,
        )
        prefix = "面孔" if labels == "zh" else "F"
        ax.text(x_coord + 5, y_coord + 5, f"{prefix}{face}", fontsize=8, zorder=6)


def true_center_for_pair(raw_village_pair: str) -> tuple[float, float]:
    points = np.array([FACE_TRUE_400[face] for face in RAW_QUADRILATERALS[raw_village_pair]], dtype=float)
    center = points.mean(axis=0)
    return float(center[0]), float(center[1])


def face_coordinate_template(subject_df: pd.DataFrame) -> dict[int, tuple[float, float]]:
    coords: dict[int, tuple[float, float]] = {}
    for face in range(1, 7):
        face_coords: list[tuple[float, float]] = []
        if {"F1", "F1X", "F1Y"}.issubset(subject_df.columns):
            face_coords.extend(
                map(tuple, subject_df.loc[subject_df["F1"] == face, ["F1X", "F1Y"]].dropna().to_numpy())
            )
        if {"F2", "F2X", "F2Y"}.issubset(subject_df.columns):
            face_coords.extend(
                map(tuple, subject_df.loc[subject_df["F2"] == face, ["F2X", "F2Y"]].dropna().to_numpy())
            )
        if not face_coords:
            raise ValueError(f"Missing face coordinates for subject {int(subject_df['SubNo'].iloc[0])}, face {face}")
        coords[face] = tuple(np.median(np.array(face_coords, dtype=float), axis=0))
    return coords


def subject_scale_factor(subject_df: pd.DataFrame) -> float:
    template = face_coordinate_template(subject_df)
    raw_vector = np.array([coord for face in range(1, 7) for coord in template[face]], dtype=float)
    target_vector = recorded_face_vector()
    return float(np.dot(raw_vector, target_vector) / np.dot(raw_vector, raw_vector))


def load_varignon_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_task_tables(DATA_PATH, "PDtask-")
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
        "Mtask",
        "MX",
        "MY",
        "MMX",
        "MMY",
        "DX",
        "DY",
        "ans_D",
    ]
    df = coerce_numeric(df, numeric_columns)
    df = filter_excluded_subjects(df)
    df = filter_completed_subjects(df)
    df = df.dropna(subset=["SubNo", "F1", "F2", "F1V", "F2V", "Mtask"]).copy()
    df["SubNo"] = df["SubNo"].astype(int)
    df["F1"] = df["F1"].astype(int)
    df["F2"] = df["F2"].astype(int)
    df["F1V"] = df["F1V"].astype(int)
    df["F2V"] = df["F2V"].astype(int)
    df["Mtask"] = df["Mtask"].astype(int)
    df["trial_index"] = df.groupby("SubNo").cumcount() + 1
    df["raw_condition"] = [raw_pair_condition(a, b) for a, b in zip(df["F1V"], df["F2V"])]
    df["condition"] = [recode_distance_condition(sub_no, cond) for sub_no, cond in zip(df["SubNo"], df["raw_condition"])]

    scale_rows = []
    for sub_no, subject_df in df.groupby("SubNo", sort=True):
        scale = subject_scale_factor(subject_df)
        scale_rows.append({"SubNo": int(sub_no), "scale_to_canonical": scale})
        mask = df["SubNo"] == sub_no
        for column in ["F1X", "F1Y", "F2X", "F2Y", "MX", "MY", "MMX", "MMY", "DX", "DY"]:
            df.loc[mask, f"{column}_norm"] = df.loc[mask, column] * scale
    return df, pd.DataFrame(scale_rows)


def build_varignon_matches(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sub_no, subject_df in df.groupby("SubNo", sort=True):
        subject_df = subject_df.sort_values("trial_index").reset_index(drop=True)
        for row_index in range(1, len(subject_df)):
            current = subject_df.iloc[row_index]
            previous = subject_df.iloc[row_index - 1]
            if previous["Mtask"] != 1 or current["Mtask"] != 2:
                continue
            pair_set = frozenset(
                {
                    tuple(sorted((int(previous["F1"]), int(previous["F2"])))),
                    tuple(sorted((int(current["F1"]), int(current["F2"])))),
                }
            )
            mapped = KEY_PAIR_MAP.get(pair_set)
            if mapped is None or pd.isna(current["MMX_norm"]) or pd.isna(current["MMY_norm"]):
                continue

            raw_village_pair, construction = mapped
            pair_condition = recode_distance_condition(int(sub_no), raw_village_pair)
            true_x, true_y = true_center_for_pair(raw_village_pair)
            derived_center_x = float(np.nanmean([previous["MX_norm"], current["MX_norm"]]))
            derived_center_y = float(np.nanmean([previous["MY_norm"], current["MY_norm"]]))
            rows.append(
                {
                    "SubNo": int(sub_no),
                    "prev_trial_index": int(previous["trial_index"]),
                    "trial_index": int(current["trial_index"]),
                    "raw_village_pair": raw_village_pair,
                    "pair_condition": pair_condition,
                    "construction": construction,
                    "construction_condition": "same" if construction == "same_edges" else pair_condition,
                    "prev_pair": f"{min(previous['F1'], previous['F2'])}-{max(previous['F1'], previous['F2'])}",
                    "current_pair": f"{min(current['F1'], current['F2'])}-{max(current['F1'], current['F2'])}",
                    "center_x": float(current["MMX_norm"]),
                    "center_y": float(current["MMY_norm"]),
                    "prev_mid_x": float(previous["MX_norm"]),
                    "prev_mid_y": float(previous["MY_norm"]),
                    "current_mid_x": float(current["MX_norm"]),
                    "current_mid_y": float(current["MY_norm"]),
                    "derived_center_x": derived_center_x,
                    "derived_center_y": derived_center_y,
                    "center_minus_derived_x": float(current["MMX_norm"] - derived_center_x),
                    "center_minus_derived_y": float(current["MMY_norm"] - derived_center_y),
                    "true_center_x": true_x,
                    "true_center_y": true_y,
                    "distance_to_true": float(np.hypot(current["MMX_norm"] - true_x, current["MMY_norm"] - true_y)),
                    "distance_to_derived": float(
                        np.hypot(current["MMX_norm"] - derived_center_x, current["MMY_norm"] - derived_center_y)
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["SubNo", "raw_village_pair", "construction", "trial_index"]).reset_index(
        drop=True
    )


def aggregate_subject_centers(match_df: pd.DataFrame) -> pd.DataFrame:
    centers = (
        match_df.groupby(["SubNo", "raw_village_pair", "pair_condition", "construction"], as_index=False)
        .agg(
            n_matches=("trial_index", "size"),
            center_x=("center_x", "median"),
            center_y=("center_y", "median"),
            trial_distance_to_true=("distance_to_true", "median"),
            trial_distance_to_derived=("distance_to_derived", "median"),
        )
        .sort_values(["SubNo", "raw_village_pair", "construction"])
    )
    true_centers = centers["raw_village_pair"].map(lambda pair: true_center_for_pair(pair))
    centers["true_center_x"] = [coord[0] for coord in true_centers]
    centers["true_center_y"] = [coord[1] for coord in true_centers]
    centers["distance_to_true"] = np.hypot(
        centers["center_x"] - centers["true_center_x"],
        centers["center_y"] - centers["true_center_y"],
    )
    return centers


def summarize_group_centers(match_df: pd.DataFrame, subject_centers: pd.DataFrame) -> pd.DataFrame:
    trial_summary = (
        match_df.groupby(["raw_village_pair", "pair_condition", "construction"], as_index=False)
        .agg(
            n_trials=("trial_index", "size"),
            mean_center_x=("center_x", "mean"),
            mean_center_y=("center_y", "mean"),
            median_center_x=("center_x", "median"),
            median_center_y=("center_y", "median"),
            mean_distance_to_true=("distance_to_true", "mean"),
            median_distance_to_true=("distance_to_true", "median"),
        )
        .sort_values(["raw_village_pair", "construction"])
    )
    subject_summary = (
        subject_centers.groupby(["raw_village_pair", "pair_condition", "construction"], as_index=False)
        .agg(
            n_subjects=("SubNo", "size"),
            subject_mean_center_x=("center_x", "mean"),
            subject_mean_center_y=("center_y", "mean"),
            subject_median_center_x=("center_x", "median"),
            subject_median_center_y=("center_y", "median"),
            subject_mean_distance_to_true=("distance_to_true", "mean"),
            subject_median_distance_to_true=("distance_to_true", "median"),
        )
        .sort_values(["raw_village_pair", "construction"])
    )
    return trial_summary.merge(
        subject_summary,
        on=["raw_village_pair", "pair_condition", "construction"],
        how="left",
    )


def safe_paired_test(values_a: pd.Series, values_b: pd.Series, label_a: str, label_b: str) -> dict[str, float | str | int]:
    paired = pd.concat([values_a.rename(label_a), values_b.rename(label_b)], axis=1).dropna()
    diff = paired[label_a] - paired[label_b]
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


def paired_stats(subject_centers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = (
        subject_centers.pivot_table(
            index=["SubNo", "raw_village_pair", "pair_condition"],
            columns="construction",
            values=["center_x", "center_y", "distance_to_true"],
        )
        .sort_index()
        .reset_index()
    )
    wide.columns = ["_".join(col).strip("_") for col in wide.columns.to_flat_index()]
    wide["center_distance"] = np.hypot(
        wide["center_x_cross_edges"] - wide["center_x_same_edges"],
        wide["center_y_cross_edges"] - wide["center_y_same_edges"],
    )

    test_rows = []
    distance_rows = []
    for scope, group_column in [("raw_village_pair", "raw_village_pair"), ("pair_condition", "pair_condition")]:
        for group_value, frame in wide.groupby(group_column, sort=False):
            if group_value not in {"AB", "AC", "BC", "near", "far", "unknown"}:
                continue
            for metric in ["center_x", "center_y", "distance_to_true"]:
                result = safe_paired_test(
                    frame[f"{metric}_cross_edges"],
                    frame[f"{metric}_same_edges"],
                    "cross_edges",
                    "same_edges",
                )
                result.update({"scope": scope, "group": group_value, "metric": metric})
                test_rows.append(result)
            distance_rows.append(
                {
                    "scope": scope,
                    "group": group_value,
                    "n_subjects": int(frame.shape[0]),
                    "mean_center_distance": float(frame["center_distance"].mean()),
                    "median_center_distance": float(frame["center_distance"].median()),
                    "sd_center_distance": float(frame["center_distance"].std(ddof=1)),
                }
            )

    return pd.DataFrame(test_rows), pd.DataFrame(distance_rows)


def subject_title(sub_no: int | None, raw_village_pair: str, labels: str) -> str:
    labels_map = LANG[labels]
    pair_note = labels_map["pair_note"][raw_village_pair]
    if sub_no is None:
        return f"{labels_map['group_title']} · {pair_note} · {labels_map['title_suffix']}"
    return f"{labels_map['subject_prefix']} {sub_no:02d} · {pair_note} · {labels_map['title_suffix']}"


def draw_background(ax: plt.Axes, raw_village_pair: str, labels: str) -> None:
    quad_points = np.array([FACE_TRUE_400[face] for face in RAW_QUADRILATERALS[raw_village_pair]], dtype=float)
    polygon = Polygon(
        order_polygon(quad_points),
        closed=True,
        facecolor="#D1D5DB",
        edgecolor="#4B5563",
        linewidth=1.2,
        alpha=0.22,
        zorder=1,
    )
    ax.add_patch(polygon)
    add_learned_true_face_points(ax, labels=labels)
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
        true_x + 6,
        true_y - 10,
        LANG[labels]["true_center"],
        fontsize=8,
        color="#111827",
        zorder=8,
    )
    setup_square_axis(ax, labels=labels)


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
    for construction in ["same_edges", "cross_edges"]:
        handles.append(
            Line2D(
                [0],
                [0],
                marker=CONSTRUCTION_MARKERS[construction],
                color="none",
                markerfacecolor=CONSTRUCTION_COLORS[construction],
                markeredgecolor="#1F2933",
                markersize=8,
                alpha=0.8,
                label=f"{LANG[labels][construction]} · {LANG[labels]['trial_points']}",
            )
        )
        handles.append(
            Line2D(
                [0],
                [0],
                marker=CONSTRUCTION_MARKERS[construction],
                color="none",
                markerfacecolor=CONSTRUCTION_COLORS[construction],
                markeredgecolor="#111827",
                markersize=10,
                label=f"{LANG[labels][construction]} · {LANG[labels]['subject_median']}",
            )
        )
        if include_group:
            handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="D",
                    color="none",
                    markerfacecolor=CONSTRUCTION_COLORS[construction],
                    markeredgecolor="#111827",
                    markersize=10,
                    label=f"{LANG[labels][construction]} · {LANG[labels]['group_median']}",
                )
            )
    return handles


def plot_subject_figure(
    raw_village_pair: str,
    trial_points: pd.DataFrame,
    subject_points: pd.DataFrame,
    sub_no: int,
    labels: str,
) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 6.1))
    draw_background(ax, raw_village_pair, labels)

    for construction in ["same_edges", "cross_edges"]:
        trial_subset = trial_points.loc[trial_points["construction"] == construction]
        subject_subset = subject_points.loc[subject_points["construction"] == construction]
        ax.scatter(
            trial_subset["center_x"],
            trial_subset["center_y"],
            s=44,
            marker=CONSTRUCTION_MARKERS[construction],
            color=CONSTRUCTION_COLORS[construction],
            edgecolor="#1F2933",
            linewidth=0.5,
            alpha=0.42,
            zorder=3,
        )
        ax.scatter(
            subject_subset["center_x"],
            subject_subset["center_y"],
            s=96,
            marker=CONSTRUCTION_MARKERS[construction],
            color=CONSTRUCTION_COLORS[construction],
            edgecolor="#111827",
            linewidth=1.0,
            alpha=0.95,
            zorder=6,
        )

    ax.set_title(subject_title(sub_no, raw_village_pair, labels))
    ax.legend(handles=legend_handles(labels, include_group=False), loc="upper left", fontsize=8)
    stem = f"sub-{sub_no:02d}_{raw_village_pair.lower()}_varignon_{labels}"
    save_figure(fig, SUBJECT_FIG_DIR, stem)


def plot_group_figure(
    raw_village_pair: str,
    trial_points: pd.DataFrame,
    subject_points: pd.DataFrame,
    labels: str,
) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 6.2))
    draw_background(ax, raw_village_pair, labels)

    for construction in ["same_edges", "cross_edges"]:
        trial_subset = trial_points.loc[trial_points["construction"] == construction]
        subject_subset = subject_points.loc[subject_points["construction"] == construction]
        ax.scatter(
            trial_subset["center_x"],
            trial_subset["center_y"],
            s=28,
            marker=CONSTRUCTION_MARKERS[construction],
            color=CONSTRUCTION_COLORS[construction],
            edgecolor="none",
            alpha=0.16,
            zorder=2,
        )
        ax.scatter(
            subject_subset["center_x"],
            subject_subset["center_y"],
            s=60,
            marker=CONSTRUCTION_MARKERS[construction],
            color=CONSTRUCTION_COLORS[construction],
            edgecolor="#1F2933",
            linewidth=0.6,
            alpha=0.6,
            zorder=4,
        )
        ax.scatter(
            subject_subset["center_x"].median(),
            subject_subset["center_y"].median(),
            s=110,
            marker="D",
            color=CONSTRUCTION_COLORS[construction],
            edgecolor="#111827",
            linewidth=1.0,
            zorder=6,
        )

    ax.set_title(subject_title(None, raw_village_pair, labels))
    ax.legend(handles=legend_handles(labels, include_group=True), loc="upper left", fontsize=8)
    stem = f"group_{raw_village_pair.lower()}_varignon_{labels}"
    save_figure(fig, GROUP_FIG_DIR, stem)


def save_all_figures(match_df: pd.DataFrame, subject_centers: pd.DataFrame) -> None:
    SUBJECT_FIG_DIR.mkdir(parents=True, exist_ok=True)
    GROUP_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for (sub_no, raw_village_pair), subject_trials in match_df.groupby(["SubNo", "raw_village_pair"], sort=True):
        subject_points = subject_centers.loc[
            (subject_centers["SubNo"] == sub_no) & (subject_centers["raw_village_pair"] == raw_village_pair)
        ]
        for labels in ["zh", "en"]:
            plot_subject_figure(raw_village_pair, subject_trials, subject_points, int(sub_no), labels)

    for raw_village_pair, pair_trials in match_df.groupby("raw_village_pair", sort=True):
        pair_subjects = subject_centers.loc[subject_centers["raw_village_pair"] == raw_village_pair]
        for labels in ["zh", "en"]:
            plot_group_figure(raw_village_pair, pair_trials, pair_subjects, labels)


def report_lines(
    scale_df: pd.DataFrame,
    match_df: pd.DataFrame,
    subject_centers: pd.DataFrame,
    stats_df: pd.DataFrame,
    distance_df: pd.DataFrame,
) -> list[str]:
    lines = [
        "PD task Varignon analysis",
        "=========================",
        "",
        "Design note",
        "-----------",
        "Distance and village relationship are partially confounded due to design constraints.",
        "AB and AC raw quadrilaterals swap near/far meaning across odd and even participants.",
        "Figures therefore keep raw quadrilateral geometry (AB/AC/BC) and label the second construction generically as cross-village edges.",
        "",
        "Coordinate normalization",
        "------------------------",
        "Raw PD task files use multiple square-size templates.",
        "The PD source-code face coordinates are used only to infer each subject's square-size scale.",
        "True centers are computed from the learned EP/MR face coordinates, then all responses are plotted in canonical 400x400 units.",
        f"Included subject pool follows completed-all-task participants: {list(completed_all_task_subject_ids())}.",
        "",
        "Sample summary",
        "--------------",
        f"Included subjects: {scale_df['SubNo'].nunique()}",
        f"Matched Varignon midpoint-of-midpoint trials: {len(match_df)}",
        "",
        "Subject scale factors",
        "---------------------",
        *scale_df.to_string(index=False, float_format=lambda value: f'{value:.4f}').splitlines(),
        "",
        "Matched trial counts",
        "--------------------",
        *(
            match_df.groupby(["raw_village_pair", "construction"])
            .size()
            .rename("n_trials")
            .reset_index()
            .to_string(index=False)
            .splitlines()
        ),
        "",
        "Subject-level center summaries",
        "------------------------------",
        *subject_centers.to_string(index=False, float_format=lambda value: f"{value:.3f}").splitlines(),
        "",
        "Paired tests: cross-village edges vs same-village edges",
        "-------------------------------------------------------",
        *stats_df.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        "Center-distance descriptives",
        "----------------------------",
        *distance_df.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
    ]
    return lines


def save_outputs(
    scale_df: pd.DataFrame,
    match_df: pd.DataFrame,
    subject_centers: pd.DataFrame,
    group_summary: pd.DataFrame,
    stats_df: pd.DataFrame,
    distance_df: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scale_df.to_csv(OUTPUT_DIR / "subject_coordinate_scales.csv", index=False)
    match_df.to_csv(OUTPUT_DIR / "varignon_trial_matches.csv", index=False)
    subject_centers.to_csv(OUTPUT_DIR / "subject_varignon_centers.csv", index=False)
    group_summary.to_csv(OUTPUT_DIR / "group_varignon_summary.csv", index=False)
    stats_df.to_csv(OUTPUT_DIR / "paired_stats_summary.csv", index=False)
    distance_df.to_csv(OUTPUT_DIR / "center_distance_summary.csv", index=False)
    (OUTPUT_DIR / "stats_report.txt").write_text(
        "\n".join(report_lines(scale_df, match_df, subject_centers, stats_df, distance_df)),
        encoding="utf-8",
    )


def main() -> None:
    configure_plot_style("paper")
    plt.rcParams["font.family"] = "Arial Unicode MS"
    plt.rcParams["axes.unicode_minus"] = False
    raw_df, scale_df = load_varignon_data()
    match_df = build_varignon_matches(raw_df)
    subject_centers = aggregate_subject_centers(match_df)
    group_summary = summarize_group_centers(match_df, subject_centers)
    stats_df, distance_df = paired_stats(subject_centers)
    save_outputs(scale_df, match_df, subject_centers, group_summary, stats_df, distance_df)
    save_all_figures(match_df, subject_centers)


if __name__ == "__main__":
    main()
