from __future__ import annotations

from pathlib import Path
import warnings

from analysis_common import (
    DATA_DIR,
    RESULTS_DIR,
    FACE_PALETTE,
    FACE_TRUE_RAW,
    TASK_PALETTE,
    TRUE_SPACE_MAX,
    add_true_face_points_0_to_10,
    coerce_numeric,
    completed_all_task_subject_ids,
    configure_plot_style,
    filter_completed_subjects,
    load_task_tables,
    paired_test_report,
    reset_proc_output_dir,
    save_figure,
    setup_true_space_axis,
)
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from scipy import stats


DATA_PATH = DATA_DIR / "MRtask_data"
OUTPUT_DIR = RESULTS_DIR / "proc6_mrtask_reconstruction_analysis"
SUBJECT_DIR = OUTPUT_DIR / "per_subject"
GROUP_DIR = OUTPUT_DIR / "group"
FACE_ORDER = [1, 2, 3, 4, 5, 6]
RNG_SEED = 20260418
PERMUTATION_SAMPLES = 20000

LANG = {
    "zh": {
        "report_title": "proc6 / MR task 重建分析",
        "face_prefix": "面孔",
        "subject_actual_title": "MR任务：被试{sub_no}的实际重建矩形",
        "subject_projected_title": "MR任务：被试{sub_no}的 0–10 投射结果",
        "group_rectangles_title": "MR任务：群体实际重建矩形叠加",
        "group_projection_title": "MR任务：群体 0–10 投射点",
        "actual_x": "能力轴长度",
        "actual_y": "温暖轴长度",
        "true_x": "能力值",
        "true_y": "温暖值",
        "subject_label": "被试",
        "mean_rectangle": "平均矩形",
        "subject_rectangles": "个体矩形",
        "projected_mean": "均值 ± 标准误",
        "true_point": "真实点",
        "projected_point": "投射点",
        "n_subjects": "纳入被试",
        "schema": "数据格式",
        "source": "来源文件",
        "range_note": "能力轴={ability:.1f}；温暖轴={warmth:.1f}",
        "group_range_note": "能力轴均值={ability:.1f}±{ability_se:.1f}；温暖轴均值={warmth:.1f}±{warmth_se:.1f}",
        "projection_note": "点位按各自矩形比例线性投射回 0–10 空间",
        "report_sample": "样本",
        "report_methods": "方法",
        "report_rectangle_summary": "矩形汇总",
        "report_rectangle_test": "矩形长宽比较",
        "report_face_summary": "面孔投射汇总",
        "report_face_tests": "面孔投射与真实点比较",
        "schema_legacy": "legacy Xrange/Yrange + F*X/F*Y",
        "schema_modern": "WarmthRange/AbilityRange + F*Warmth/F*Ability",
    },
    "en": {
        "report_title": "proc6 / MR task reconstruction analysis",
        "face_prefix": "F",
        "subject_actual_title": "MR task: Subject {sub_no} actual reconstructed rectangle",
        "subject_projected_title": "MR task: Subject {sub_no} projected points in 0–10 space",
        "group_rectangles_title": "MR task: Group overlay of actual reconstructed rectangles",
        "group_projection_title": "MR task: Group projected points in 0–10 space",
        "actual_x": "Ability-axis length",
        "actual_y": "Warmth-axis length",
        "true_x": "Ability",
        "true_y": "Warmth",
        "subject_label": "Subject",
        "mean_rectangle": "Mean rectangle",
        "subject_rectangles": "Subject rectangles",
        "projected_mean": "Mean ± SE",
        "true_point": "True point",
        "projected_point": "Projected point",
        "n_subjects": "Included subjects",
        "schema": "Schema",
        "source": "Source file",
        "range_note": "Ability axis={ability:.1f}; Warmth axis={warmth:.1f}",
        "group_range_note": "Mean ability axis={ability:.1f}±{ability_se:.1f}; mean warmth axis={warmth:.1f}±{warmth_se:.1f}",
        "projection_note": "Points are linearly projected back to the shared 0–10 space",
        "report_sample": "Sample",
        "report_methods": "Methods",
        "report_rectangle_summary": "Rectangle summary",
        "report_rectangle_test": "Rectangle width-height comparison",
        "report_face_summary": "Face projection summary",
        "report_face_tests": "Face projected-vs-true comparison",
        "schema_legacy": "legacy Xrange/Yrange + F*X/F*Y",
        "schema_modern": "WarmthRange/AbilityRange + F*Warmth/F*Ability",
    },
}


def configure_fonts() -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
        "Arial",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    warnings.filterwarnings("ignore", message=r"Glyph .* missing from font")


def load_raw_data() -> pd.DataFrame:
    df = load_task_tables(DATA_PATH, "MRtask")
    numeric_columns = [
        "SubNo",
        "Age",
        "Xrange",
        "Yrange",
        "WarmthRange",
        "AbilityRange",
        *[f"F{face}X" for face in FACE_ORDER],
        *[f"F{face}Y" for face in FACE_ORDER],
        *[f"F{face}Warmth" for face in FACE_ORDER],
        *[f"F{face}Ability" for face in FACE_ORDER],
        *[f"F{face}V" for face in FACE_ORDER],
    ]
    df = coerce_numeric(df, numeric_columns)
    df = filter_completed_subjects(df)
    df = df.dropna(subset=["SubNo"]).copy()
    df["SubNo"] = df["SubNo"].astype(int)
    return df.sort_values("SubNo").reset_index(drop=True)


def shapiro_p_safe(values: pd.Series | np.ndarray) -> float:
    array = pd.Series(values).dropna().to_numpy(dtype=float)
    if len(array) < 3:
        return np.nan
    return float(stats.shapiro(array).pvalue)


def hotelling_t2_test(differences: np.ndarray) -> dict[str, float | str | int]:
    n_obs, n_dim = differences.shape
    mean_vector = differences.mean(axis=0)
    covariance = np.cov(differences, rowvar=False, ddof=1)
    inv_covariance = np.linalg.pinv(np.atleast_2d(covariance))
    t2_statistic = float(n_obs * mean_vector @ inv_covariance @ mean_vector)
    f_statistic = float((n_obs - n_dim) * t2_statistic / (n_dim * (n_obs - 1)))
    p_value = float(1 - stats.f.cdf(f_statistic, n_dim, n_obs - n_dim))
    return {
        "method": "one-sample Hotelling T-squared",
        "statistic": t2_statistic,
        "f_statistic": f_statistic,
        "df1": int(n_dim),
        "df2": int(n_obs - n_dim),
        "p_value": p_value,
    }


def permutation_t2_test(differences: np.ndarray, *, seed: int, n_resamples: int) -> dict[str, float | str | int]:
    rng = np.random.default_rng(seed)
    observed = hotelling_t2_test(differences)["statistic"]
    exceedances = 0
    for _ in range(n_resamples):
        signs = rng.choice([-1.0, 1.0], size=(differences.shape[0], 1))
        permuted = differences * signs
        statistic = hotelling_t2_test(permuted)["statistic"]
        exceedances += statistic >= observed
    p_value = float((exceedances + 1) / (n_resamples + 1))
    return {
        "method": "sign-flip permutation test on Hotelling T-squared",
        "statistic": float(observed),
        "f_statistic": np.nan,
        "df1": int(differences.shape[1]),
        "df2": np.nan,
        "p_value": p_value,
        "n_resamples": int(n_resamples),
    }


def choose_face_test(face_frame: pd.DataFrame) -> dict[str, float | str | int]:
    differences = face_frame[["delta_ability", "delta_warmth"]].dropna().to_numpy(dtype=float)
    shapiro_ability = shapiro_p_safe(face_frame["delta_ability"])
    shapiro_warmth = shapiro_p_safe(face_frame["delta_warmth"])
    if (
        differences.shape[0] > differences.shape[1]
        and not np.isnan(shapiro_ability)
        and not np.isnan(shapiro_warmth)
        and shapiro_ability >= 0.05
        and shapiro_warmth >= 0.05
    ):
        result = hotelling_t2_test(differences)
    else:
        result = permutation_t2_test(
            differences,
            seed=RNG_SEED + int(face_frame["face"].iloc[0]),
            n_resamples=PERMUTATION_SAMPLES,
        )
    result["n_subjects"] = int(differences.shape[0])
    result["shapiro_ability_p"] = shapiro_ability
    result["shapiro_warmth_p"] = shapiro_warmth
    return result


def detect_schema(row: pd.Series) -> str:
    if pd.notna(row.get("AbilityRange")) and pd.notna(row.get("WarmthRange")):
        return "warmth_ability"
    if pd.notna(row.get("Xrange")) and pd.notna(row.get("Yrange")):
        return "legacy_xy"
    raise ValueError(f"Unable to infer MR schema for subject {row.get('SubNo')}")


def get_face_percentages(row: pd.Series, face: int, schema: str) -> tuple[float, float]:
    if schema == "legacy_xy":
        return float(row[f"F{face}X"]), float(row[f"F{face}Y"])
    return float(row[f"F{face}Ability"]), float(row[f"F{face}Warmth"])


def get_ranges(row: pd.Series, schema: str) -> tuple[float, float]:
    if schema == "legacy_xy":
        return float(row["Xrange"]), float(row["Yrange"])
    return float(row["AbilityRange"]), float(row["WarmthRange"])


def prepare_analysis_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    subject_rows: list[dict[str, object]] = []
    point_rows: list[dict[str, object]] = []

    for _, row in raw.iterrows():
        schema = detect_schema(row)
        ability_range, warmth_range = get_ranges(row, schema)
        sub_no = int(row["SubNo"])
        source = str(row["source"])

        subject_rows.append(
            {
                "SubNo": sub_no,
                "source": source,
                "schema": schema,
                "ability_range": ability_range,
                "warmth_range": warmth_range,
                "aspect_ratio": warmth_range / ability_range if ability_range else np.nan,
            }
        )

        for face in FACE_ORDER:
            ability_pct, warmth_pct = get_face_percentages(row, face, schema)
            projected_ability = ability_pct / 100.0 * TRUE_SPACE_MAX
            projected_warmth = warmth_pct / 100.0 * TRUE_SPACE_MAX
            true_ability, true_warmth = FACE_TRUE_RAW[face]

            point_rows.append(
                {
                    "SubNo": sub_no,
                    "source": source,
                    "schema": schema,
                    "face": face,
                    "village": int(row[f"F{face}V"]),
                    "ability_pct": ability_pct,
                    "warmth_pct": warmth_pct,
                    "actual_ability": ability_pct / 100.0 * ability_range,
                    "actual_warmth": warmth_pct / 100.0 * warmth_range,
                    "projected_ability": projected_ability,
                    "projected_warmth": projected_warmth,
                    "true_ability": true_ability,
                    "true_warmth": true_warmth,
                    "delta_ability": projected_ability - true_ability,
                    "delta_warmth": projected_warmth - true_warmth,
                    "euclidean_error": float(
                        np.hypot(projected_ability - true_ability, projected_warmth - true_warmth)
                    ),
                }
            )

    subject_summary = pd.DataFrame(subject_rows).sort_values("SubNo").reset_index(drop=True)
    point_summary = pd.DataFrame(point_rows).sort_values(["SubNo", "face"]).reset_index(drop=True)
    return subject_summary, point_summary


def subject_output_dir(sub_no: int) -> Path:
    return SUBJECT_DIR / f"sub-{sub_no:02d}"


def schema_label(schema: str, language: str) -> str:
    labels = LANG[language]
    if schema == "legacy_xy":
        return labels["schema_legacy"]
    return labels["schema_modern"]


def draw_subject_actual_rectangle(subject_row: pd.Series, point_frame: pd.DataFrame, *, language: str) -> None:
    labels = LANG[language]
    ability_range = float(subject_row["ability_range"])
    warmth_range = float(subject_row["warmth_range"])
    max_x = max(ability_range, float(point_frame["actual_ability"].max())) * 1.08
    max_y = max(warmth_range, float(point_frame["actual_warmth"].max())) * 1.08

    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    ax.add_patch(
        Rectangle(
            (0, 0),
            ability_range,
            warmth_range,
            fill=False,
            linewidth=1.8,
            edgecolor=TASK_PALETTE["gray"],
        )
    )

    for point in point_frame.itertuples(index=False):
        ax.scatter(
            point.actual_ability,
            point.actual_warmth,
            s=88,
            color=FACE_PALETTE[point.face],
            edgecolor="#1F2933",
            linewidth=0.8,
            zorder=3,
        )
        ax.text(
            point.actual_ability + max_x * 0.012,
            point.actual_warmth + max_y * 0.012,
            f"{labels['face_prefix']}{point.face}",
            fontsize=8,
            color="#1F2933",
            zorder=4,
        )

    ax.set_xlim(0, max_x)
    ax.set_ylim(0, max_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(labels["actual_x"])
    ax.set_ylabel(labels["actual_y"])
    ax.set_title(labels["subject_actual_title"].format(sub_no=int(subject_row["SubNo"])))
    ax.text(
        0.02,
        0.98,
        (
            f"{labels['range_note'].format(ability=ability_range, warmth=warmth_range)}\n"
            f"{labels['schema']}: {schema_label(str(subject_row['schema']), language)}\n"
            f"{labels['source']}: {subject_row['source']}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, subject_output_dir(int(subject_row["SubNo"])), f"subject_actual_rectangle_{language}")


def draw_subject_projected_space(subject_row: pd.Series, point_frame: pd.DataFrame, *, language: str) -> None:
    labels = LANG[language]
    axis_language = "zh" if language == "zh" else "en"
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    setup_true_space_axis(ax, labels=axis_language)
    add_true_face_points_0_to_10(ax, labels=axis_language, size=58, marker="X", zorder=4)

    for point in point_frame.itertuples(index=False):
        ax.plot(
            [point.true_ability, point.projected_ability],
            [point.true_warmth, point.projected_warmth],
            color=FACE_PALETTE[point.face],
            alpha=0.35,
            linewidth=1.0,
            zorder=2,
        )
        ax.scatter(
            point.projected_ability,
            point.projected_warmth,
            s=72,
            color=FACE_PALETTE[point.face],
            edgecolor="#1F2933",
            linewidth=0.8,
            zorder=3,
        )
        ax.text(
            point.projected_ability + 0.14,
            point.projected_warmth - 0.22,
            f"{labels['face_prefix']}{point.face}",
            fontsize=8,
            color="#1F2933",
            zorder=5,
        )

    ax.set_title(labels["subject_projected_title"].format(sub_no=int(subject_row["SubNo"])))
    ax.text(
        0.02,
        0.98,
        (
            f"{labels['range_note'].format(ability=float(subject_row['ability_range']), warmth=float(subject_row['warmth_range']))}\n"
            f"{labels['projection_note']}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, subject_output_dir(int(subject_row["SubNo"])), f"subject_projected_0to10_{language}")


def draw_group_rectangles(subject_summary: pd.DataFrame, *, language: str) -> None:
    labels = LANG[language]
    mean_ability = float(subject_summary["ability_range"].mean())
    mean_warmth = float(subject_summary["warmth_range"].mean())
    se_ability = float(subject_summary["ability_range"].std(ddof=1) / np.sqrt(len(subject_summary)))
    se_warmth = float(subject_summary["warmth_range"].std(ddof=1) / np.sqrt(len(subject_summary)))
    max_x = float(subject_summary["ability_range"].max()) * 1.08
    max_y = float(subject_summary["warmth_range"].max()) * 1.08

    fig, ax = plt.subplots(figsize=(7.0, 6.2))
    for subject in subject_summary.itertuples(index=False):
        ax.add_patch(
            Rectangle(
                (0, 0),
                subject.ability_range,
                subject.warmth_range,
                fill=False,
                linewidth=1.0,
                edgecolor=TASK_PALETTE["blue"],
                alpha=0.2,
            )
        )

    ax.add_patch(
        Rectangle(
            (0, 0),
            mean_ability,
            mean_warmth,
            fill=False,
            linewidth=2.2,
            edgecolor=TASK_PALETTE["red"],
        )
    )

    legend_handles = [
        Line2D([0], [0], color=TASK_PALETTE["blue"], lw=1.4, alpha=0.4, label=labels["subject_rectangles"]),
        Line2D([0], [0], color=TASK_PALETTE["red"], lw=2.2, label=labels["mean_rectangle"]),
    ]
    ax.legend(handles=legend_handles, loc="lower right")
    ax.set_xlim(0, max_x)
    ax.set_ylim(0, max_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(labels["actual_x"])
    ax.set_ylabel(labels["actual_y"])
    ax.set_title(labels["group_rectangles_title"])
    ax.text(
        0.02,
        0.98,
        (
            f"{labels['n_subjects']}: {len(subject_summary)}\n"
            f"{labels['group_range_note'].format(ability=mean_ability, ability_se=se_ability, warmth=mean_warmth, warmth_se=se_warmth)}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, GROUP_DIR, f"group_actual_rectangles_{language}")


def draw_group_projection(point_summary: pd.DataFrame, face_summary: pd.DataFrame, *, language: str) -> None:
    labels = LANG[language]
    axis_language = "zh" if language == "zh" else "en"
    fig, ax = plt.subplots(figsize=(7.0, 6.4))
    setup_true_space_axis(ax, labels=axis_language)
    add_true_face_points_0_to_10(ax, labels=axis_language, size=62, marker="X", zorder=5)

    for face in FACE_ORDER:
        face_points = point_summary[point_summary["face"] == face]
        ax.scatter(
            face_points["projected_ability"],
            face_points["projected_warmth"],
            s=28,
            color=FACE_PALETTE[face],
            alpha=0.24,
            edgecolor="none",
            zorder=2,
        )

        face_row = face_summary.loc[face_summary["face"] == face].iloc[0]
        ax.errorbar(
            face_row["mean_projected_ability"],
            face_row["mean_projected_warmth"],
            xerr=face_row["se_projected_ability"],
            yerr=face_row["se_projected_warmth"],
            fmt="o",
            markersize=7,
            color=FACE_PALETTE[face],
            ecolor=FACE_PALETTE[face],
            elinewidth=1.3,
            capsize=3,
            markeredgecolor="#1F2933",
            markeredgewidth=0.8,
            zorder=4,
        )
        ax.text(
            face_row["mean_projected_ability"] + 0.16,
            face_row["mean_projected_warmth"] - 0.24,
            f"{labels['face_prefix']}{face}",
            fontsize=8,
            color="#1F2933",
            zorder=6,
        )

    ax.set_title(labels["group_projection_title"])
    ax.text(
        0.02,
        0.98,
        f"{labels['n_subjects']}: {point_summary['SubNo'].nunique()}\n{labels['projected_mean']}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, GROUP_DIR, f"group_projected_0to10_{language}")


def build_face_summary(point_summary: pd.DataFrame) -> pd.DataFrame:
    summary = (
        point_summary.groupby("face", as_index=False)
        .agg(
            n_subjects=("SubNo", "nunique"),
            mean_projected_ability=("projected_ability", "mean"),
            sd_projected_ability=("projected_ability", "std"),
            mean_projected_warmth=("projected_warmth", "mean"),
            sd_projected_warmth=("projected_warmth", "std"),
            mean_delta_ability=("delta_ability", "mean"),
            sd_delta_ability=("delta_ability", "std"),
            mean_delta_warmth=("delta_warmth", "mean"),
            sd_delta_warmth=("delta_warmth", "std"),
            mean_euclidean_error=("euclidean_error", "mean"),
            sd_euclidean_error=("euclidean_error", "std"),
        )
        .sort_values("face")
    )
    summary["se_projected_ability"] = summary["sd_projected_ability"] / np.sqrt(summary["n_subjects"])
    summary["se_projected_warmth"] = summary["sd_projected_warmth"] / np.sqrt(summary["n_subjects"])
    summary["se_delta_ability"] = summary["sd_delta_ability"] / np.sqrt(summary["n_subjects"])
    summary["se_delta_warmth"] = summary["sd_delta_warmth"] / np.sqrt(summary["n_subjects"])
    summary["se_euclidean_error"] = summary["sd_euclidean_error"] / np.sqrt(summary["n_subjects"])
    summary["true_ability"] = summary["face"].map(lambda face: FACE_TRUE_RAW[int(face)][0])
    summary["true_warmth"] = summary["face"].map(lambda face: FACE_TRUE_RAW[int(face)][1])
    return summary


def build_rectangle_summary(subject_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in ["ability_range", "warmth_range", "aspect_ratio"]:
        series = subject_summary[metric].dropna()
        rows.append(
            {
                "metric": metric,
                "n_subjects": int(series.shape[0]),
                "mean": float(series.mean()),
                "sd": float(series.std(ddof=1)),
                "se": float(series.std(ddof=1) / np.sqrt(series.shape[0])),
                "median": float(series.median()),
                "min": float(series.min()),
                "max": float(series.max()),
            }
        )
    return pd.DataFrame(rows)


def build_face_tests(point_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for face, frame in point_summary.groupby("face", sort=True):
        result = choose_face_test(frame)
        rows.append({"face": int(face), **result})
    return pd.DataFrame(rows)


def write_report(
    *,
    language: str,
    subject_summary: pd.DataFrame,
    rectangle_test: dict[str, float | str | int],
    rectangle_summary: pd.DataFrame,
    face_summary: pd.DataFrame,
    face_tests: pd.DataFrame,
) -> None:
    labels = LANG[language]
    legacy_n = int((subject_summary["schema"] == "legacy_xy").sum())
    modern_n = int((subject_summary["schema"] == "warmth_ability").sum())
    included_subjects = ", ".join(str(sub_no) for sub_no in completed_all_task_subject_ids())
    lines = [
        labels["report_title"],
        "=" * len(labels["report_title"]),
        "",
        labels["report_sample"],
        "-" * len(labels["report_sample"]),
        f"{labels['n_subjects']}: {len(subject_summary)}",
        f"{labels['schema_legacy']}: {legacy_n}",
        f"{labels['schema_modern']}: {modern_n}",
        f"Completed-subject pool: [{included_subjects}]",
        "",
        labels["report_methods"],
        "-" * len(labels["report_methods"]),
        (
            "Actual rectangles use WarmthRange/AbilityRange or legacy Xrange/Yrange; "
            "recorded face percentages are projected back to the shared 0–10 space before group comparison."
            if language == "en"
            else "实际矩形使用 WarmthRange/AbilityRange 或 legacy Xrange/Yrange；记录到的面孔百分比先按比例投射回共享 0–10 空间，再进行群体比较。"
        ),
        (
            "Rectangle width-vs-height uses a paired t-test when Shapiro-Wilk on within-subject differences is >= 0.05; otherwise Wilcoxon signed-rank."
            if language == "en"
            else "矩形长宽比较：若被试内差值通过 Shapiro-Wilk 正态性检验，则用配对 t 检验；否则用 Wilcoxon 符号秩检验。"
        ),
        (
            "Per-face projected-vs-true tests use one-sample Hotelling T-squared when both coordinate differences pass Shapiro-Wilk; otherwise a sign-flip permutation test on the Hotelling statistic (20,000 resamples)."
            if language == "en"
            else "每张脸的投射点 vs 真实点比较：若两个坐标差值都通过 Shapiro-Wilk，则用单样本 Hotelling T²；否则用基于 Hotelling 统计量的 sign-flip permutation test（20,000 次重采样）。"
        ),
        "",
        labels["report_rectangle_summary"],
        "-" * len(labels["report_rectangle_summary"]),
        *rectangle_summary.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        labels["report_rectangle_test"],
        "-" * len(labels["report_rectangle_test"]),
        *pd.DataFrame([rectangle_test]).to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        labels["report_face_summary"],
        "-" * len(labels["report_face_summary"]),
        *face_summary.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        labels["report_face_tests"],
        "-" * len(labels["report_face_tests"]),
        *face_tests.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / f"proc6_mrtask_reconstruction_stats_report_{language}.txt").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def save_tables(
    subject_summary: pd.DataFrame,
    point_summary: pd.DataFrame,
    rectangle_summary: pd.DataFrame,
    face_summary: pd.DataFrame,
    rectangle_test: dict[str, float | str | int],
    face_tests: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    subject_summary.to_csv(OUTPUT_DIR / "subject_rectangle_summary.csv", index=False)
    point_summary.to_csv(OUTPUT_DIR / "subject_projected_points_0to10.csv", index=False)
    rectangle_summary.to_csv(OUTPUT_DIR / "group_rectangle_summary.csv", index=False)
    face_summary.to_csv(OUTPUT_DIR / "group_projected_face_summary_0to10.csv", index=False)
    pd.DataFrame([rectangle_test]).to_csv(OUTPUT_DIR / "rectangle_width_height_test.csv", index=False)
    face_tests.to_csv(OUTPUT_DIR / "face_projection_tests_0to10.csv", index=False)


def generate_subject_figures(subject_summary: pd.DataFrame, point_summary: pd.DataFrame) -> None:
    for subject_row in subject_summary.itertuples(index=False):
        point_frame = point_summary[point_summary["SubNo"] == subject_row.SubNo].copy()
        subject_series = pd.Series(subject_row._asdict())
        for language in ["zh", "en"]:
            draw_subject_actual_rectangle(subject_series, point_frame, language=language)
            draw_subject_projected_space(subject_series, point_frame, language=language)


def generate_group_figures(subject_summary: pd.DataFrame, point_summary: pd.DataFrame, face_summary: pd.DataFrame) -> None:
    for language in ["zh", "en"]:
        draw_group_rectangles(subject_summary, language=language)
        draw_group_projection(point_summary, face_summary, language=language)


def main() -> None:
    reset_proc_output_dir(OUTPUT_DIR)
    configure_plot_style("paper")
    configure_fonts()
    raw = load_raw_data()
    subject_summary, point_summary = prepare_analysis_data(raw)
    rectangle_summary = build_rectangle_summary(subject_summary)
    face_summary = build_face_summary(point_summary)
    rectangle_test = paired_test_report(
        subject_summary["ability_range"],
        subject_summary["warmth_range"],
        "ability_range",
        "warmth_range",
    )
    face_tests = build_face_tests(point_summary)
    save_tables(subject_summary, point_summary, rectangle_summary, face_summary, rectangle_test, face_tests)
    generate_subject_figures(subject_summary, point_summary)
    generate_group_figures(subject_summary, point_summary, face_summary)
    for language in ["zh", "en"]:
        write_report(
            language=language,
            subject_summary=subject_summary,
            rectangle_test=rectangle_test,
            rectangle_summary=rectangle_summary,
            face_summary=face_summary,
            face_tests=face_tests,
        )


if __name__ == "__main__":
    main()
