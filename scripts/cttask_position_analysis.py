from __future__ import annotations

import os
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "results" / "cttask_position_analysis"
OUTPUT_CACHE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "cttask_position_analysis_cache"
os.environ["MPLCONFIGDIR"] = str(OUTPUT_CACHE_DIR / "matplotlib")
os.environ["XDG_CACHE_HOME"] = str(OUTPUT_CACHE_DIR)

from analysis_common import (
    completed_all_task_subject_ids,
    DATA_DIR,
    FACE_PALETTE,
    FACE_TRUE_400,
    add_true_face_points,
    coerce_numeric,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    load_task_tables,
    save_figure,
    setup_square_axis,
)
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D


TASK_DATA_DIR = DATA_DIR / "CTtask_data"
TABLE_DIR = OUTPUT_DIR / "tables"
SUBJECT_FIG_DIR = OUTPUT_DIR / "subjects"
GROUP_FIG_DIR = OUTPUT_DIR / "group"
REPORT_PATH = OUTPUT_DIR / "cttask_position_report.txt"
RNG_SEED = 20260417
N_PERMUTATIONS = 20000
NUMERIC_COLUMNS = [
    "SubNo",
    "Age",
    "face",
    "true_leftBar",
    "true_rightBar",
    "leftBarLength",
    "rightBarLength",
    "error",
    "acc",
    "rt",
]

TEXT = {
    "en": {
        "subject_title": "CT task position reconstruction — Subject {subno:02d}",
        "subject_subtitle": "24 trial responses in harmonized 400×400 coordinates",
        "group_title": "CT task position reconstruction — Subject means",
        "group_subtitle": "Each dot shows the 4-trial mean for one subject (n={n_subjects})",
        "legend_true": "True position",
        "legend_trial": "Trial response",
        "legend_subject_mean": "Subject mean",
        "legend_group_mean": "Group mean",
        "legend_face": "Face color",
    },
    "zh": {
        "subject_title": "CT任务位置复原——被试{subno:02d}",
        "subject_subtitle": "24次作答已统一映射到 400×400 坐标空间",
        "group_title": "CT任务位置复原——被试均值",
        "group_subtitle": "每个点表示1名被试对该面孔4次复原的平均值（n={n_subjects}）",
        "legend_true": "真实位置",
        "legend_trial": "单次复原",
        "legend_subject_mean": "被试均值",
        "legend_group_mean": "组均值",
        "legend_face": "面孔颜色",
    },
}


def configure_fonts() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    zh_candidates = [
        "Noto Sans CJK SC",
        "PingFang SC",
        "Hiragino Sans GB",
        "Microsoft YaHei",
        "SimHei",
        "Heiti SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    zh_font = next((font for font in zh_candidates if font in available), "DejaVu Sans")
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [zh_font, "Arial", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def face_truth_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "face": face,
                "true_ability": coords[0],
                "true_warmth": coords[1],
            }
            for face, coords in FACE_TRUE_400.items()
        ]
    ).sort_values("face")


def load_ct_data() -> pd.DataFrame:
    data = load_task_tables(TASK_DATA_DIR, "CTtask-")
    data = coerce_numeric(data, NUMERIC_COLUMNS)
    data = data.dropna(subset=["SubNo", "face", "leftBarLength", "rightBarLength"]).copy()
    data["SubNo"] = data["SubNo"].astype(int)
    data["face"] = data["face"].astype(int)
    data = filter_excluded_subjects(data)
    data = filter_completed_subjects(data)
    data = data.sort_values(["SubNo", "face", "source"]).reset_index(drop=True)
    return data


def fit_axis_transform(raw_values: np.ndarray, target_values: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(raw_values, target_values, 1)
    predicted = slope * raw_values + intercept
    rmse = float(np.sqrt(np.mean((predicted - target_values) ** 2)))
    return float(slope), float(intercept), rmse


def build_subject_coordinate_map(data: pd.DataFrame) -> pd.DataFrame:
    truth = face_truth_frame()
    rows: list[dict[str, float | int]] = []

    for subno, subject_data in data.groupby("SubNo"):
        raw_truth = (
            subject_data.groupby("face", as_index=False)[["true_leftBar", "true_rightBar"]]
            .first()
            .merge(truth, on="face", how="left")
            .sort_values("face")
        )

        if raw_truth["face"].nunique() != len(FACE_TRUE_400):
            raise ValueError(f"Subject {subno} does not contain all six faces.")

        slope_x, intercept_x, rmse_x = fit_axis_transform(
            raw_truth["true_leftBar"].to_numpy(float),
            raw_truth["true_ability"].to_numpy(float),
        )
        slope_y, intercept_y, rmse_y = fit_axis_transform(
            raw_truth["true_rightBar"].to_numpy(float),
            raw_truth["true_warmth"].to_numpy(float),
        )

        rows.append(
            {
                "SubNo": int(subno),
                "ability_slope": slope_x,
                "ability_intercept": intercept_x,
                "ability_rmse_px": rmse_x,
                "warmth_slope": slope_y,
                "warmth_intercept": intercept_y,
                "warmth_rmse_px": rmse_y,
            }
        )

    return pd.DataFrame(rows).sort_values("SubNo").reset_index(drop=True)


def harmonize_positions(data: pd.DataFrame, coordinate_map: pd.DataFrame) -> pd.DataFrame:
    truth = face_truth_frame()
    harmonized = data.merge(coordinate_map, on="SubNo", how="left").merge(truth, on="face", how="left")
    harmonized["ability"] = harmonized["leftBarLength"] * harmonized["ability_slope"] + harmonized["ability_intercept"]
    harmonized["warmth"] = harmonized["rightBarLength"] * harmonized["warmth_slope"] + harmonized["warmth_intercept"]
    harmonized["raw_true_ability"] = harmonized["true_leftBar"]
    harmonized["raw_true_warmth"] = harmonized["true_rightBar"]
    harmonized["mapped_true_ability"] = (
        harmonized["raw_true_ability"] * harmonized["ability_slope"] + harmonized["ability_intercept"]
    )
    harmonized["mapped_true_warmth"] = (
        harmonized["raw_true_warmth"] * harmonized["warmth_slope"] + harmonized["warmth_intercept"]
    )
    harmonized["ability_error"] = harmonized["ability"] - harmonized["true_ability"]
    harmonized["warmth_error"] = harmonized["warmth"] - harmonized["true_warmth"]
    harmonized["euclidean_error"] = np.hypot(harmonized["ability_error"], harmonized["warmth_error"])
    return harmonized


def build_subject_face_means(harmonized: pd.DataFrame) -> pd.DataFrame:
    subject_means = (
        harmonized.groupby(["SubNo", "face"], as_index=False)
        .agg(
            n_trials=("face", "size"),
            ability=("ability", "mean"),
            warmth=("warmth", "mean"),
            mean_euclidean_error=("euclidean_error", "mean"),
            sd_euclidean_error=("euclidean_error", "std"),
            mean_rt=("rt", "mean"),
            accuracy=("acc", "mean"),
        )
        .sort_values(["SubNo", "face"])
        .reset_index(drop=True)
    )
    truth = face_truth_frame()
    subject_means = subject_means.merge(truth, on="face", how="left")
    subject_means["ability_bias"] = subject_means["ability"] - subject_means["true_ability"]
    subject_means["warmth_bias"] = subject_means["warmth"] - subject_means["true_warmth"]
    subject_means["euclidean_bias"] = np.hypot(subject_means["ability_bias"], subject_means["warmth_bias"])
    return subject_means


def build_face_group_summary(subject_means: pd.DataFrame) -> pd.DataFrame:
    summary = (
        subject_means.groupby("face", as_index=False)
        .agg(
            n_subjects=("SubNo", "nunique"),
            mean_ability=("ability", "mean"),
            sd_ability=("ability", "std"),
            mean_warmth=("warmth", "mean"),
            sd_warmth=("warmth", "std"),
            mean_ability_bias=("ability_bias", "mean"),
            sd_ability_bias=("ability_bias", "std"),
            mean_warmth_bias=("warmth_bias", "mean"),
            sd_warmth_bias=("warmth_bias", "std"),
            mean_euclidean_bias=("euclidean_bias", "mean"),
            sd_euclidean_bias=("euclidean_bias", "std"),
            mean_trial_error=("mean_euclidean_error", "mean"),
            sd_trial_error=("mean_euclidean_error", "std"),
        )
        .sort_values("face")
        .reset_index(drop=True)
    )
    summary["se_ability"] = summary["sd_ability"] / np.sqrt(summary["n_subjects"])
    summary["se_warmth"] = summary["sd_warmth"] / np.sqrt(summary["n_subjects"])
    summary["se_ability_bias"] = summary["sd_ability_bias"] / np.sqrt(summary["n_subjects"])
    summary["se_warmth_bias"] = summary["sd_warmth_bias"] / np.sqrt(summary["n_subjects"])
    summary["se_euclidean_bias"] = summary["sd_euclidean_bias"] / np.sqrt(summary["n_subjects"])
    summary["se_trial_error"] = summary["sd_trial_error"] / np.sqrt(summary["n_subjects"])
    truth = face_truth_frame()
    summary = summary.merge(truth, on="face", how="left")
    return summary


def hotelling_t2_one_sample(differences: np.ndarray) -> dict[str, float]:
    sample_size, n_dims = differences.shape
    mean_vector = differences.mean(axis=0)
    covariance = np.cov(differences, rowvar=False, ddof=1)
    inverse_covariance = np.linalg.pinv(covariance)
    t2_statistic = float(sample_size * mean_vector @ inverse_covariance @ mean_vector)
    f_statistic = float((sample_size - n_dims) * t2_statistic / (n_dims * (sample_size - 1)))
    p_value = float(1 - stats.f.cdf(f_statistic, n_dims, sample_size - n_dims))
    return {
        "hotelling_t2": t2_statistic,
        "f_statistic": f_statistic,
        "p_value": p_value,
    }


def sign_flip_hotelling_test(
    differences: np.ndarray,
    *,
    n_permutations: int = N_PERMUTATIONS,
    seed: int = RNG_SEED,
) -> dict[str, float | int]:
    sample_size = differences.shape[0]
    observed = hotelling_t2_one_sample(differences)["hotelling_t2"]
    covariance = np.cov(differences, rowvar=False, ddof=1)
    inverse_covariance = np.linalg.pinv(covariance)

    if sample_size <= 14:
        sign_matrix = np.array(list(product([-1.0, 1.0], repeat=sample_size)), dtype=float)
    else:
        rng = np.random.default_rng(seed)
        sign_matrix = rng.choice([-1.0, 1.0], size=(n_permutations, sample_size)).astype(float)

    permuted_means = (sign_matrix @ differences) / sample_size
    permuted_stats = sample_size * np.einsum(
        "ij,jk,ik->i",
        permuted_means,
        inverse_covariance,
        permuted_means,
    )
    p_value = float((np.count_nonzero(permuted_stats >= observed) + 1) / (len(permuted_stats) + 1))
    return {
        "hotelling_t2": float(observed),
        "p_value": p_value,
        "n_permutations": int(len(permuted_stats)),
    }


def safe_shapiro(series: pd.Series) -> float:
    values = series.dropna().to_numpy(float)
    if len(values) < 3 or np.allclose(values, values[0]):
        return np.nan
    return float(stats.shapiro(values).pvalue)


def run_face_position_tests(subject_means: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []

    for face, face_data in subject_means.groupby("face"):
        ordered = face_data.sort_values("SubNo")
        differences = ordered[["ability_bias", "warmth_bias"]].to_numpy(float)
        shapiro_ability_p = safe_shapiro(ordered["ability_bias"])
        shapiro_warmth_p = safe_shapiro(ordered["warmth_bias"])
        use_hotelling = (
            len(ordered) > 2
            and np.isfinite(shapiro_ability_p)
            and np.isfinite(shapiro_warmth_p)
            and shapiro_ability_p >= 0.05
            and shapiro_warmth_p >= 0.05
        )

        if use_hotelling:
            result = hotelling_t2_one_sample(differences)
            method = "one-sample Hotelling T²"
            statistic_label = "F"
            statistic_value = result["f_statistic"]
            n_permutations = 0
        else:
            result = sign_flip_hotelling_test(differences, seed=RNG_SEED + int(face))
            method = "sign-flip permutation on Hotelling-like T²"
            statistic_label = "T²"
            statistic_value = result["hotelling_t2"]
            n_permutations = int(result["n_permutations"])

        rows.append(
            {
                "face": int(face),
                "n_subjects": int(len(ordered)),
                "mean_ability": float(ordered["ability"].mean()),
                "mean_warmth": float(ordered["warmth"].mean()),
                "true_ability": float(ordered["true_ability"].iloc[0]),
                "true_warmth": float(ordered["true_warmth"].iloc[0]),
                "mean_ability_bias": float(ordered["ability_bias"].mean()),
                "mean_warmth_bias": float(ordered["warmth_bias"].mean()),
                "mean_euclidean_bias": float(ordered["euclidean_bias"].mean()),
                "shapiro_ability_p": shapiro_ability_p,
                "shapiro_warmth_p": shapiro_warmth_p,
                "method": method,
                "statistic_label": statistic_label,
                "statistic_value": float(statistic_value),
                "hotelling_t2": float(result["hotelling_t2"]),
                "p_value": float(result["p_value"]),
                "n_permutations": n_permutations,
            }
        )

    tests = pd.DataFrame(rows).sort_values("face").reset_index(drop=True)
    reject, p_fdr, _, _ = multipletests(tests["p_value"], method="fdr_bh")
    tests["p_value_fdr_bh"] = p_fdr
    tests["reject_fdr_bh_0_05"] = reject
    return tests


def marker_legend_handles(language: str) -> list[Line2D]:
    labels = TEXT[language]
    return [
        Line2D(
            [0],
            [0],
            marker="X",
            linestyle="None",
            markerfacecolor="#1F2933",
            markeredgecolor="#1F2933",
            markersize=8,
            label=labels["legend_true"],
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor="#9CA3AF",
            markeredgecolor="#2F3437",
            markersize=7,
            alpha=0.75,
            label=labels["legend_trial"],
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            linestyle="None",
            markerfacecolor="#F3F4F6",
            markeredgecolor="#111827",
            markersize=7,
            label=labels["legend_subject_mean"],
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            linestyle="None",
            markerfacecolor="#F3F4F6",
            markeredgecolor="#111827",
            markersize=7,
            label=labels["legend_group_mean"],
        ),
    ]


def face_color_handles(language: str) -> list[Line2D]:
    labels = TEXT[language]
    prefix = "面孔" if language == "zh" else "F"
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markerfacecolor=FACE_PALETTE[face],
            markeredgecolor=FACE_PALETTE[face],
            markersize=6,
            label=f"{prefix}{face}",
        )
        for face in sorted(FACE_TRUE_400)
    ]
    handles[0].set_label(f"{labels['legend_face']}: {handles[0].get_label()}")
    return handles


def save_subject_figure(
    subject_trials: pd.DataFrame,
    subject_means: pd.DataFrame,
    *,
    subno: int,
    language: str,
) -> None:
    labels = TEXT[language]
    fig, ax = plt.subplots(figsize=(7.5, 7.2))
    add_true_face_points(ax, labels=language, size=90, marker="X", zorder=5)

    for face, face_trials in subject_trials.groupby("face"):
        color = FACE_PALETTE[int(face)]
        ax.scatter(
            face_trials["ability"],
            face_trials["warmth"],
            s=42,
            alpha=0.60,
            color=color,
            edgecolor="#2F3437",
            linewidth=0.35,
            zorder=3,
        )
        face_mean = subject_means.loc[subject_means["face"] == face].iloc[0]
        ax.plot(
            [face_mean["true_ability"], face_mean["ability"]],
            [face_mean["true_warmth"], face_mean["warmth"]],
            linestyle="--",
            linewidth=0.9,
            color=color,
            alpha=0.85,
            zorder=2,
        )
        ax.scatter(
            face_mean["ability"],
            face_mean["warmth"],
            s=84,
            marker="D",
            color=color,
            edgecolor="#111827",
            linewidth=0.9,
            zorder=4,
        )

    setup_square_axis(ax, labels=language)
    ax.set_xticks(np.arange(0, 401, 100))
    ax.set_yticks(np.arange(0, 401, 100))
    ax.set_title(labels["subject_title"].format(subno=subno), pad=16)
    ax.text(
        0.5,
        1.01,
        labels["subject_subtitle"],
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#4B5563",
    )
    first_legend = ax.legend(handles=marker_legend_handles(language)[:3], loc="upper left", fontsize=8)
    ax.add_artist(first_legend)
    ax.legend(handles=face_color_handles(language), loc="lower right", fontsize=8, ncol=2)
    save_figure(fig, SUBJECT_FIG_DIR, f"sub-{subno:02d}_positions_{language}")


def save_group_figure(subject_means: pd.DataFrame, *, language: str) -> None:
    labels = TEXT[language]
    group_means = (
        subject_means.groupby("face", as_index=False)[["ability", "warmth", "true_ability", "true_warmth"]]
        .mean()
        .sort_values("face")
    )

    fig, ax = plt.subplots(figsize=(7.8, 7.4))
    add_true_face_points(ax, labels=language, size=90, marker="X", zorder=6)

    for face, face_means in subject_means.groupby("face"):
        color = FACE_PALETTE[int(face)]
        ax.scatter(
            face_means["ability"],
            face_means["warmth"],
            s=38,
            alpha=0.32,
            color=color,
            edgecolor="none",
            zorder=3,
        )
        face_group_mean = group_means.loc[group_means["face"] == face].iloc[0]
        ax.plot(
            [face_group_mean["true_ability"], face_group_mean["ability"]],
            [face_group_mean["true_warmth"], face_group_mean["warmth"]],
            linestyle="--",
            linewidth=1.0,
            color=color,
            alpha=0.9,
            zorder=4,
        )
        ax.scatter(
            face_group_mean["ability"],
            face_group_mean["warmth"],
            s=92,
            marker="s",
            facecolor="#F9FAFB",
            edgecolor=color,
            linewidth=1.5,
            zorder=5,
        )

    setup_square_axis(ax, labels=language)
    ax.set_xticks(np.arange(0, 401, 100))
    ax.set_yticks(np.arange(0, 401, 100))
    ax.set_title(labels["group_title"], pad=16)
    ax.text(
        0.5,
        1.01,
        labels["group_subtitle"].format(n_subjects=subject_means["SubNo"].nunique()),
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
        color="#4B5563",
    )
    first_legend = ax.legend(
        handles=[marker_legend_handles(language)[0], marker_legend_handles(language)[1], marker_legend_handles(language)[3]],
        loc="upper left",
        fontsize=8,
    )
    ax.add_artist(first_legend)
    ax.legend(handles=face_color_handles(language), loc="lower right", fontsize=8, ncol=2)
    save_figure(fig, GROUP_FIG_DIR, f"cttask_group_subject_means_{language}")


def save_tables(
    harmonized: pd.DataFrame,
    coordinate_map: pd.DataFrame,
    subject_means: pd.DataFrame,
    face_summary: pd.DataFrame,
    face_tests: pd.DataFrame,
) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    coordinate_map.to_csv(TABLE_DIR / "subject_coordinate_map.csv", index=False)
    harmonized.to_csv(TABLE_DIR / "trial_positions_standardized.csv", index=False)
    subject_means.to_csv(TABLE_DIR / "subject_face_means.csv", index=False)
    face_summary.to_csv(TABLE_DIR / "face_group_summary.csv", index=False)
    face_tests.to_csv(TABLE_DIR / "face_position_tests.csv", index=False)


def build_report(
    harmonized: pd.DataFrame,
    coordinate_map: pd.DataFrame,
    face_summary: pd.DataFrame,
    face_tests: pd.DataFrame,
) -> str:
    lines: list[str] = []
    lines.append("CT task position analysis / CT任务位置分析")
    lines.append("=" * 56)
    lines.append("")
    lines.append("Data and preprocessing")
    lines.append(f"- Input directory: {TASK_DATA_DIR}")
    lines.append(f"- Included subjects: {harmonized['SubNo'].nunique()} ({', '.join(map(str, sorted(harmonized['SubNo'].unique())))})")
    lines.append(f"- Total included trials: {len(harmonized)}")
    lines.append("- Base exclusions: 1, 15, 17")
    lines.append(f"- Completed-all-task subjects: {list(completed_all_task_subject_ids())}")
    lines.append(
        "- Raw `true_leftBar`/`true_rightBar` coordinates vary across cohorts, so each subject was linearly mapped"
        " into the shared 400×400 face-coordinate system from `scripts/analysis_common.py`."
    )
    lines.append(
        f"- Coordinate-map RMSE: ability median {coordinate_map['ability_rmse_px'].median():.2f}px, "
        f"warmth median {coordinate_map['warmth_rmse_px'].median():.2f}px."
    )
    lines.append("")
    lines.append("Descriptive summary by face")

    for row in face_summary.itertuples(index=False):
        lines.append(
            f"- Face {row.face}: mean=({row.mean_ability:.2f}, {row.mean_warmth:.2f}), "
            f"true=({row.true_ability:.2f}, {row.true_warmth:.2f}), "
            f"bias=({row.mean_ability_bias:.2f}, {row.mean_warmth_bias:.2f}), "
            f"mean Euclidean bias={row.mean_euclidean_bias:.2f}px, "
            f"mean trial error={row.mean_trial_error:.2f}px."
        )

    lines.append("")
    lines.append("Face-wise inferential tests")
    lines.append(
        "- Decision rule: use one-sample Hotelling T² when both coordinate-wise Shapiro tests on subject-level"
        " mean bias pass p ≥ 0.05; otherwise use a sign-flip permutation test on a Hotelling-like T² statistic."
    )

    for row in face_tests.itertuples(index=False):
        permutation_note = ""
        if row.n_permutations:
            permutation_note = f", permutations={row.n_permutations}"
        lines.append(
            f"- Face {row.face}: method={row.method}, {row.statistic_label}={row.statistic_value:.4f}, "
            f"p={row.p_value:.4g}, FDR-BH p={row.p_value_fdr_bh:.4g}, "
            f"mean bias=({row.mean_ability_bias:.2f}, {row.mean_warmth_bias:.2f}), "
            f"Shapiro p=({row.shapiro_ability_p:.4g}, {row.shapiro_warmth_p:.4g}){permutation_note}."
        )

    significant_faces = face_tests.loc[face_tests["reject_fdr_bh_0_05"], "face"].tolist()
    lines.append("")
    if significant_faces:
        lines.append(f"Faces significant after FDR-BH correction: {', '.join(map(str, significant_faces))}.")
    else:
        lines.append("No face remains significant after FDR-BH correction.")
    lines.append("")
    lines.append("Generated outputs")
    lines.append(f"- Subject figures: {SUBJECT_FIG_DIR}")
    lines.append(f"- Group figures: {GROUP_FIG_DIR}")
    lines.append(f"- CSV tables: {TABLE_DIR}")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    configure_plot_style(context="paper")
    configure_fonts()

    raw_data = load_ct_data()
    coordinate_map = build_subject_coordinate_map(raw_data)
    harmonized = harmonize_positions(raw_data, coordinate_map)
    subject_means = build_subject_face_means(harmonized)
    face_summary = build_face_group_summary(subject_means)
    face_tests = run_face_position_tests(subject_means)

    for subno, subject_trials in harmonized.groupby("SubNo"):
        subject_trial_slice = subject_trials.sort_values(["face", "source"]).copy()
        subject_mean_slice = subject_means.loc[subject_means["SubNo"] == subno].copy()
        for language in ("en", "zh"):
            save_subject_figure(subject_trial_slice, subject_mean_slice, subno=int(subno), language=language)

    for language in ("en", "zh"):
        save_group_figure(subject_means, language=language)

    save_tables(harmonized, coordinate_map, subject_means, face_summary, face_tests)
    REPORT_PATH.write_text(build_report(harmonized, coordinate_map, face_summary, face_tests), encoding="utf-8")


if __name__ == "__main__":
    main()
