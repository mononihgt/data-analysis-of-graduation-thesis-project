from __future__ import annotations

import os
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "results" / "proc5_cttask_position_analysis"
OUTPUT_CACHE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "proc5_cttask_position_analysis_cache"
os.environ["MPLCONFIGDIR"] = str(OUTPUT_CACHE_DIR / "matplotlib")
os.environ["XDG_CACHE_HOME"] = str(OUTPUT_CACHE_DIR)

from analysis_common import (
    DATA_DIR,
    FACE_PALETTE,
    FACE_TRUE_RAW,
    TRUE_SPACE_MAX,
    add_true_face_points_0_to_10,
    coerce_numeric,
    completed_all_task_subject_ids,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    infer_square_side_from_face_truth,
    load_task_tables,
    pixels_to_true_space,
    save_figure,
    setup_true_space_axis,
)
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D


TASK_DATA_DIR = DATA_DIR / "CTtask_data"
TABLE_DIR = OUTPUT_DIR / "tables"
SUBJECT_FIG_DIR = OUTPUT_DIR / "subjects"
GROUP_FIG_DIR = OUTPUT_DIR / "group"
REPORT_DIR = OUTPUT_DIR / "reports"
RNG_SEED = 20260418
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
        "axis_x": "Ability",
        "axis_y": "Warmth",
        "subject_title": "CT task position reconstruction — Subject {subno:02d}",
        "subject_subtitle": "Canonical truth (6 points) and 24 restored responses in shared 0–10 space",
        "group_title": "CT task position reconstruction — Subject face means",
        "group_subtitle": "Each dot is the 4-trial mean for one subject and one face (n={n_subjects})",
        "legend_true": "True position",
        "legend_trial": "Trial response",
        "legend_subject_mean": "Subject face mean",
        "legend_face": "Face color",
        "report_title": "CT task position analysis (proc5)",
        "report_section_data": "Data and preprocessing",
        "report_section_desc": "Descriptive summary by face",
        "report_section_stats": "Face-wise inferential tests",
        "report_section_outputs": "Generated outputs",
        "primary_label": "Primary test",
        "perm_label": "Permutation alternative",
        "param_label": "Parametric reference",
        "significant_none": "No face remains significant after FDR-BH correction on the primary test.",
        "significant_some": "Faces significant after FDR-BH correction on the primary test",
    },
    "zh": {
        "axis_x": "能力值",
        "axis_y": "温暖值",
        "subject_title": "CT任务位置复原——被试{subno:02d}",
        "subject_subtitle": "共享 0–10 空间中的真实六点与 24 个复原点",
        "group_title": "CT任务位置复原——被试均值",
        "group_subtitle": "每个点表示 1 名被试对该面孔 4 次复原的均值（n={n_subjects}）",
        "legend_true": "真实位置",
        "legend_trial": "单次复原",
        "legend_subject_mean": "被试面孔均值",
        "legend_face": "面孔颜色",
        "report_title": "CT任务位置分析（proc5）",
        "report_section_data": "数据与预处理",
        "report_section_desc": "按面孔的描述统计",
        "report_section_stats": "按面孔的推断统计",
        "report_section_outputs": "生成结果",
        "primary_label": "主检验",
        "perm_label": "置换替代",
        "param_label": "参数参考",
        "significant_none": "按主检验做 FDR-BH 校正后，没有面孔仍显著。",
        "significant_some": "按主检验做 FDR-BH 校正后仍显著的面孔",
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
            {"face": face, "true_ability": ability, "true_warmth": warmth}
            for face, (ability, warmth) in FACE_TRUE_RAW.items()
        ]
    ).sort_values("face")


def load_ct_data() -> pd.DataFrame:
    data = load_task_tables(TASK_DATA_DIR, "CTtask-")
    data = coerce_numeric(data, NUMERIC_COLUMNS)
    data = data.dropna(
        subset=["SubNo", "face", "true_leftBar", "true_rightBar", "leftBarLength", "rightBarLength"]
    ).copy()
    data["SubNo"] = data["SubNo"].astype(int)
    data["face"] = data["face"].astype(int)
    data = filter_excluded_subjects(data)
    data = filter_completed_subjects(data)
    data = data.sort_values(["SubNo", "source", "face"]).reset_index(drop=True)
    return data


def estimate_square_side_ls(face_truth: pd.DataFrame) -> float:
    observed = np.concatenate(
        [
            face_truth["true_leftBar"].to_numpy(float),
            face_truth["true_rightBar"].to_numpy(float),
        ]
    )
    canonical = np.concatenate(
        [
            face_truth["true_ability"].to_numpy(float) / TRUE_SPACE_MAX,
            face_truth["true_warmth"].to_numpy(float) / TRUE_SPACE_MAX,
        ]
    )
    return float(np.dot(observed, canonical) / np.dot(canonical, canonical))


def build_session_coordinate_map(data: pd.DataFrame) -> pd.DataFrame:
    truth = face_truth_frame()
    rows: list[dict[str, float | int | str]] = []

    for (subno, source), session_data in data.groupby(["SubNo", "source"], sort=True):
        face_truth = (
            session_data.groupby("face", as_index=False)[["true_leftBar", "true_rightBar"]]
            .first()
            .merge(truth, on="face", how="left")
            .sort_values("face")
        )

        if face_truth["face"].nunique() != len(FACE_TRUE_RAW):
            raise ValueError(f"Subject {subno} / session {source} does not contain all six faces.")

        best_side, fit_rmse_px, fit_max_abs_error_px = infer_square_side_from_face_truth(face_truth)
        ls_square_side_px = estimate_square_side_ls(face_truth)

        rows.append(
            {
                "SubNo": int(subno),
                "source": source,
                "session_square_side_px": int(best_side),
                "session_square_side_px_ls": ls_square_side_px,
                "fit_rmse_px": float(fit_rmse_px),
                "fit_max_abs_error_px": float(fit_max_abs_error_px),
                "n_faces": int(face_truth["face"].nunique()),
                "n_trials": int(len(session_data)),
            }
        )

    return pd.DataFrame(rows).sort_values(["SubNo", "source"]).reset_index(drop=True)


def standardize_positions(data: pd.DataFrame, session_map: pd.DataFrame) -> pd.DataFrame:
    truth = face_truth_frame()
    standardized = data.merge(session_map, on=["SubNo", "source"], how="left").merge(truth, on="face", how="left")

    standardized["ability_0_10"] = pixels_to_true_space(
        standardized["leftBarLength"],
        standardized["session_square_side_px"],
    )
    standardized["warmth_0_10"] = pixels_to_true_space(
        standardized["rightBarLength"],
        standardized["session_square_side_px"],
    )
    standardized["recorded_true_ability_0_10"] = pixels_to_true_space(
        standardized["true_leftBar"],
        standardized["session_square_side_px"],
    )
    standardized["recorded_true_warmth_0_10"] = pixels_to_true_space(
        standardized["true_rightBar"],
        standardized["session_square_side_px"],
    )
    standardized["ability_bias"] = standardized["ability_0_10"] - standardized["true_ability"]
    standardized["warmth_bias"] = standardized["warmth_0_10"] - standardized["true_warmth"]
    standardized["euclidean_bias"] = np.hypot(standardized["ability_bias"], standardized["warmth_bias"])
    standardized["true_mapping_ability_error"] = standardized["recorded_true_ability_0_10"] - standardized["true_ability"]
    standardized["true_mapping_warmth_error"] = standardized["recorded_true_warmth_0_10"] - standardized["true_warmth"]
    return standardized


def build_subject_face_means(standardized: pd.DataFrame) -> pd.DataFrame:
    truth = face_truth_frame()
    subject_means = (
        standardized.groupby(["SubNo", "face"], as_index=False)
        .agg(
            n_trials=("face", "size"),
            n_sessions=("source", "nunique"),
            ability_0_10=("ability_0_10", "mean"),
            warmth_0_10=("warmth_0_10", "mean"),
            mean_euclidean_bias=("euclidean_bias", "mean"),
            sd_euclidean_bias=("euclidean_bias", "std"),
            mean_rt=("rt", "mean"),
            accuracy=("acc", "mean"),
        )
        .merge(truth, on="face", how="left")
        .sort_values(["SubNo", "face"])
        .reset_index(drop=True)
    )
    subject_means["ability_bias"] = subject_means["ability_0_10"] - subject_means["true_ability"]
    subject_means["warmth_bias"] = subject_means["warmth_0_10"] - subject_means["true_warmth"]
    subject_means["euclidean_bias_from_mean"] = np.hypot(
        subject_means["ability_bias"],
        subject_means["warmth_bias"],
    )
    return subject_means


def build_face_group_summary(subject_means: pd.DataFrame) -> pd.DataFrame:
    summary = (
        subject_means.groupby("face", as_index=False)
        .agg(
            n_subjects=("SubNo", "nunique"),
            mean_ability_0_10=("ability_0_10", "mean"),
            sd_ability_0_10=("ability_0_10", "std"),
            mean_warmth_0_10=("warmth_0_10", "mean"),
            sd_warmth_0_10=("warmth_0_10", "std"),
            mean_ability_bias=("ability_bias", "mean"),
            sd_ability_bias=("ability_bias", "std"),
            mean_warmth_bias=("warmth_bias", "mean"),
            sd_warmth_bias=("warmth_bias", "std"),
            mean_euclidean_bias=("euclidean_bias_from_mean", "mean"),
            sd_euclidean_bias=("euclidean_bias_from_mean", "std"),
            mean_trial_bias=("mean_euclidean_bias", "mean"),
            sd_trial_bias=("mean_euclidean_bias", "std"),
        )
        .merge(face_truth_frame(), on="face", how="left")
        .sort_values("face")
        .reset_index(drop=True)
    )
    for column in [
        "ability_0_10",
        "warmth_0_10",
        "ability_bias",
        "warmth_bias",
        "euclidean_bias",
        "trial_bias",
    ]:
        summary[f"se_{column}"] = summary[f"sd_{column}"] / np.sqrt(summary["n_subjects"])
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
    covariance = np.cov(differences, rowvar=False, ddof=1)
    inverse_covariance = np.linalg.pinv(covariance)
    observed = hotelling_t2_one_sample(differences)["hotelling_t2"]

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
    rows: list[dict[str, float | int | str | bool]] = []

    for face, face_data in subject_means.groupby("face"):
        ordered = face_data.sort_values("SubNo")
        differences = ordered[["ability_bias", "warmth_bias"]].to_numpy(float)
        shapiro_ability_p = safe_shapiro(ordered["ability_bias"])
        shapiro_warmth_p = safe_shapiro(ordered["warmth_bias"])
        can_use_hotelling = (
            len(ordered) > 2
            and np.isfinite(shapiro_ability_p)
            and np.isfinite(shapiro_warmth_p)
            and shapiro_ability_p >= 0.05
            and shapiro_warmth_p >= 0.05
        )

        hotelling_result = hotelling_t2_one_sample(differences)
        permutation_result = sign_flip_hotelling_test(differences, seed=RNG_SEED + int(face))
        primary_method = "one-sample Hotelling T²" if can_use_hotelling else "sign-flip permutation on Hotelling-like T²"
        primary_statistic_label = "F" if can_use_hotelling else "T²"
        primary_statistic_value = (
            hotelling_result["f_statistic"] if can_use_hotelling else permutation_result["hotelling_t2"]
        )
        primary_p_value = hotelling_result["p_value"] if can_use_hotelling else permutation_result["p_value"]

        rows.append(
            {
                "face": int(face),
                "n_subjects": int(len(ordered)),
                "mean_ability_0_10": float(ordered["ability_0_10"].mean()),
                "mean_warmth_0_10": float(ordered["warmth_0_10"].mean()),
                "true_ability": float(ordered["true_ability"].iloc[0]),
                "true_warmth": float(ordered["true_warmth"].iloc[0]),
                "mean_ability_bias": float(ordered["ability_bias"].mean()),
                "mean_warmth_bias": float(ordered["warmth_bias"].mean()),
                "mean_euclidean_bias": float(ordered["euclidean_bias_from_mean"].mean()),
                "shapiro_ability_p": shapiro_ability_p,
                "shapiro_warmth_p": shapiro_warmth_p,
                "hotelling_t2": float(hotelling_result["hotelling_t2"]),
                "hotelling_f": float(hotelling_result["f_statistic"]),
                "hotelling_p_value": float(hotelling_result["p_value"]),
                "permutation_t2": float(permutation_result["hotelling_t2"]),
                "permutation_p_value": float(permutation_result["p_value"]),
                "permutation_n": int(permutation_result["n_permutations"]),
                "primary_method": primary_method,
                "primary_statistic_label": primary_statistic_label,
                "primary_statistic_value": float(primary_statistic_value),
                "primary_p_value": float(primary_p_value),
                "used_hotelling_as_primary": bool(can_use_hotelling),
            }
        )

    tests = pd.DataFrame(rows).sort_values("face").reset_index(drop=True)
    reject, p_fdr, _, _ = multipletests(tests["primary_p_value"], method="fdr_bh")
    tests["primary_p_value_fdr_bh"] = p_fdr
    tests["reject_fdr_bh_0_05"] = reject
    return tests


def legend_handles(language: str, *, include_subject_mean: bool) -> list[Line2D]:
    labels = TEXT[language]
    handles = [
        Line2D(
            [0],
            [0],
            marker="X",
            linestyle="None",
            markerfacecolor="#1F2933",
            markeredgecolor="#1F2933",
            markersize=8,
            label=labels["legend_true"],
        )
    ]
    if include_subject_mean:
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="None",
                markerfacecolor="#9CA3AF",
                markeredgecolor="#2F3437",
                markersize=7,
                alpha=0.7,
                label=labels["legend_subject_mean"],
            )
        )
    else:
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="None",
                markerfacecolor="#9CA3AF",
                markeredgecolor="#2F3437",
                markersize=7,
                alpha=0.7,
                label=labels["legend_trial"],
            )
        )
    return handles


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
        for face in sorted(FACE_TRUE_RAW)
    ]
    handles[0].set_label(f"{labels['legend_face']}: {handles[0].get_label()}")
    return handles


def save_subject_figure(subject_trials: pd.DataFrame, *, subno: int, language: str) -> None:
    labels = TEXT[language]
    fig, ax = plt.subplots(figsize=(7.4, 7.1))
    add_true_face_points_0_to_10(ax, labels=language, size=90, marker="X", zorder=5)

    for face, face_trials in subject_trials.groupby("face"):
        color = FACE_PALETTE[int(face)]
        ax.scatter(
            face_trials["ability_0_10"],
            face_trials["warmth_0_10"],
            s=46,
            alpha=0.64,
            color=color,
            edgecolor="#2F3437",
            linewidth=0.35,
            zorder=3,
        )

    setup_true_space_axis(ax, labels=language)
    ax.set_xticks(np.arange(0, 10.1, 2))
    ax.set_yticks(np.arange(0, 10.1, 2))
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
    first_legend = ax.legend(handles=legend_handles(language, include_subject_mean=False), loc="upper left", fontsize=8)
    ax.add_artist(first_legend)
    ax.legend(handles=face_color_handles(language), loc="lower right", fontsize=8, ncol=2)
    save_figure(fig, SUBJECT_FIG_DIR, f"sub-{subno:02d}_cttask_positions_0_to_10_{language}")


def save_group_figure(subject_means: pd.DataFrame, *, language: str) -> None:
    labels = TEXT[language]
    fig, ax = plt.subplots(figsize=(7.6, 7.2))
    add_true_face_points_0_to_10(ax, labels=language, size=90, marker="X", zorder=5)

    for face, face_means in subject_means.groupby("face"):
        color = FACE_PALETTE[int(face)]
        ax.scatter(
            face_means["ability_0_10"],
            face_means["warmth_0_10"],
            s=42,
            alpha=0.42,
            color=color,
            edgecolor="none",
            zorder=3,
        )

    setup_true_space_axis(ax, labels=language)
    ax.set_xticks(np.arange(0, 10.1, 2))
    ax.set_yticks(np.arange(0, 10.1, 2))
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
    first_legend = ax.legend(handles=legend_handles(language, include_subject_mean=True), loc="upper left", fontsize=8)
    ax.add_artist(first_legend)
    ax.legend(handles=face_color_handles(language), loc="lower right", fontsize=8, ncol=2)
    save_figure(fig, GROUP_FIG_DIR, f"cttask_group_subject_means_0_to_10_{language}")


def save_tables(
    standardized: pd.DataFrame,
    session_map: pd.DataFrame,
    subject_means: pd.DataFrame,
    face_summary: pd.DataFrame,
    face_tests: pd.DataFrame,
) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    session_map.to_csv(TABLE_DIR / "session_coordinate_map.csv", index=False)
    standardized.to_csv(TABLE_DIR / "trial_positions_0_to_10.csv", index=False)
    subject_means.to_csv(TABLE_DIR / "subject_face_means.csv", index=False)
    face_summary.to_csv(TABLE_DIR / "face_group_summary.csv", index=False)
    face_tests.to_csv(TABLE_DIR / "face_position_tests.csv", index=False)


def build_report(
    *,
    language: str,
    standardized: pd.DataFrame,
    session_map: pd.DataFrame,
    face_summary: pd.DataFrame,
    face_tests: pd.DataFrame,
) -> str:
    labels = TEXT[language]
    is_zh = language == "zh"
    lines: list[str] = []
    lines.append(labels["report_title"])
    lines.append("=" * 64)
    lines.append("")
    lines.append(labels["report_section_data"])
    lines.append(
        f"- {'输入目录' if is_zh else 'Input directory'}: {TASK_DATA_DIR}"
    )
    lines.append(
        f"- {'纳入被试' if is_zh else 'Included subjects'}: {standardized['SubNo'].nunique()} "
        f"({', '.join(map(str, sorted(standardized['SubNo'].unique())))})"
    )
    lines.append(f"- {'纳入试次总数' if is_zh else 'Total included trials'}: {len(standardized)}")
    lines.append(
        f"- {'基础排除' if is_zh else 'Base exclusions'}: 1, 15, 17"
    )
    lines.append(
        f"- {'完成全部任务的被试' if is_zh else 'Completed-all-task subjects'}: "
        f"{list(completed_all_task_subject_ids())}"
    )
    lines.append(
        (
            "- 每个被试 / session 都用原始文件里的 `true_leftBar` 与 `true_rightBar`，"
            "结合 canonical `FACE_TRUE_RAW` 反推 `squareSidePx`，再把 `leftBarLength` / `rightBarLength`"
            " 统一换算到共享 0–10 空间。"
        )
        if is_zh
        else (
            "- For each subject/session, raw `true_leftBar` and `true_rightBar` were matched to canonical "
            "`FACE_TRUE_RAW` to infer `squareSidePx`, then `leftBarLength` and `rightBarLength` were rescaled "
            "into the shared 0–10 space."
        )
    )
    lines.append(
        (
            f"- 推断得到的 `squareSidePx` 分布: {session_map['session_square_side_px'].value_counts().sort_index().to_dict()}"
        )
        if is_zh
        else f"- Inferred `squareSidePx` distribution: {session_map['session_square_side_px'].value_counts().sort_index().to_dict()}"
    )
    lines.append(
        (
            f"- session 映射 RMSE 中位数: {session_map['fit_rmse_px'].median():.3f}px；"
            f"最大绝对误差中位数: {session_map['fit_max_abs_error_px'].median():.3f}px。"
        )
        if is_zh
        else (
            f"- Median session mapping RMSE: {session_map['fit_rmse_px'].median():.3f}px; "
            f"median max-absolute error: {session_map['fit_max_abs_error_px'].median():.3f}px."
        )
    )
    lines.append("")
    lines.append(labels["report_section_desc"])

    for row in face_summary.itertuples(index=False):
        if is_zh:
            lines.append(
                f"- 面孔{row.face}: 均值=({row.mean_ability_0_10:.3f}, {row.mean_warmth_0_10:.3f})，"
                f"真值=({row.true_ability:.3f}, {row.true_warmth:.3f})，"
                f"偏差=({row.mean_ability_bias:.3f}, {row.mean_warmth_bias:.3f})，"
                f"被试均值欧氏偏差={row.mean_euclidean_bias:.3f}，"
                f"单次试次平均欧氏偏差={row.mean_trial_bias:.3f}。"
            )
        else:
            lines.append(
                f"- Face {row.face}: mean=({row.mean_ability_0_10:.3f}, {row.mean_warmth_0_10:.3f}), "
                f"truth=({row.true_ability:.3f}, {row.true_warmth:.3f}), "
                f"bias=({row.mean_ability_bias:.3f}, {row.mean_warmth_bias:.3f}), "
                f"subject-mean Euclidean bias={row.mean_euclidean_bias:.3f}, "
                f"mean trial Euclidean bias={row.mean_trial_bias:.3f}."
            )

    lines.append("")
    lines.append(labels["report_section_stats"])
    lines.append(
        (
            "- 主检验规则：若能力与温暖两个维度的被试均值偏差都通过 Shapiro 正态性检验（p ≥ 0.05），"
            "则报告单样本 Hotelling T²；否则报告 sign-flip permutation 的 Hotelling-like T²。"
        )
        if is_zh
        else (
            "- Primary-test rule: report one-sample Hotelling T² when both coordinate-wise subject-mean bias "
            "distributions pass Shapiro p ≥ 0.05; otherwise report a sign-flip permutation test on a Hotelling-like T² statistic."
        )
    )
    lines.append(
        (
            "- 同时保留参数参考与稳健置换替代，便于核对结论是否稳健。"
        )
        if is_zh
        else "- Both the parametric reference and the robust permutation alternative are retained for comparison."
    )

    for row in face_tests.itertuples(index=False):
        if is_zh:
            lines.append(
                f"- 面孔{row.face}: {labels['primary_label']}={row.primary_method}, "
                f"{row.primary_statistic_label}={row.primary_statistic_value:.4f}, "
                f"p={row.primary_p_value:.4g}, FDR-BH p={row.primary_p_value_fdr_bh:.4g}; "
                f"{labels['param_label']} Hotelling T²={row.hotelling_t2:.4f}, F={row.hotelling_f:.4f}, p={row.hotelling_p_value:.4g}; "
                f"{labels['perm_label']} T²={row.permutation_t2:.4f}, p={row.permutation_p_value:.4g}, "
                f"n={row.permutation_n}; Shapiro p=({row.shapiro_ability_p:.4g}, {row.shapiro_warmth_p:.4g})."
            )
        else:
            lines.append(
                f"- Face {row.face}: {labels['primary_label']}={row.primary_method}, "
                f"{row.primary_statistic_label}={row.primary_statistic_value:.4f}, "
                f"p={row.primary_p_value:.4g}, FDR-BH p={row.primary_p_value_fdr_bh:.4g}; "
                f"{labels['param_label']} Hotelling T²={row.hotelling_t2:.4f}, F={row.hotelling_f:.4f}, p={row.hotelling_p_value:.4g}; "
                f"{labels['perm_label']} T²={row.permutation_t2:.4f}, p={row.permutation_p_value:.4g}, "
                f"n={row.permutation_n}; Shapiro p=({row.shapiro_ability_p:.4g}, {row.shapiro_warmth_p:.4g})."
            )

    significant_faces = face_tests.loc[face_tests["reject_fdr_bh_0_05"], "face"].tolist()
    lines.append("")
    if significant_faces:
        face_list = ", ".join(map(str, significant_faces))
        lines.append(f"{labels['significant_some']}: {face_list}.")
    else:
        lines.append(labels["significant_none"])

    lines.append("")
    lines.append(labels["report_section_outputs"])
    lines.append(f"- {'被试图' if is_zh else 'Subject figures'}: {SUBJECT_FIG_DIR}")
    lines.append(f"- {'群体图' if is_zh else 'Group figures'}: {GROUP_FIG_DIR}")
    lines.append(f"- CSV {'表格' if is_zh else 'tables'}: {TABLE_DIR}")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    configure_plot_style(context="paper")
    configure_fonts()

    raw_data = load_ct_data()
    session_map = build_session_coordinate_map(raw_data)
    standardized = standardize_positions(raw_data, session_map)
    subject_means = build_subject_face_means(standardized)
    face_summary = build_face_group_summary(subject_means)
    face_tests = run_face_position_tests(subject_means)

    for subno, subject_trials in standardized.groupby("SubNo"):
        subject_trial_slice = subject_trials.sort_values(["face", "source"]).copy()
        for language in ("en", "zh"):
            save_subject_figure(subject_trial_slice, subno=int(subno), language=language)

    for language in ("en", "zh"):
        save_group_figure(subject_means, language=language)

    save_tables(standardized, session_map, subject_means, face_summary, face_tests)
    for language in ("en", "zh"):
        report_path = REPORT_DIR / f"cttask_position_stats_report_{language}.txt"
        report_path.write_text(
            build_report(
                language=language,
                standardized=standardized,
                session_map=session_map,
                face_summary=face_summary,
                face_tests=face_tests,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
