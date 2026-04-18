from __future__ import annotations

from pathlib import Path
import warnings

from analysis_common import (
    completed_all_task_subject_ids,
    DATA_DIR,
    RESULTS_DIR,
    FACE_PALETTE,
    FACE_TRUE_400,
    TASK_PALETTE,
    add_true_face_points,
    coerce_numeric,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    load_task_tables,
    paired_test_report,
    save_figure,
    setup_square_axis,
)
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from scipy import stats


DATA_PATH = DATA_DIR / "MRtask_data"
OUTPUT_DIR = RESULTS_DIR / "mrtask_reconstruction_analysis"
SUBJECT_DIR = OUTPUT_DIR / "per_subject"
GROUP_DIR = OUTPUT_DIR / "group"
FACE_ORDER = [1, 2, 3, 4, 5, 6]
RNG_SEED = 20260417
PERMUTATION_SAMPLES = 20000

LANG = {
    "zh": {
        "face_prefix": "面孔",
        "subject_actual_title": "MR任务：被试{sub_no}的实际重建矩形",
        "subject_projected_title": "MR任务：被试{sub_no}的方框投射结果",
        "group_rectangles_title": "MR任务：所有被试的实际重建矩形",
        "group_projection_title": "MR任务：所有被试的方框投射结果",
        "x_actual": "能力轴长度",
        "y_actual": "温暖轴长度",
        "x_square": "能力值",
        "y_square": "温暖值",
        "subject_label": "被试",
        "mean_rectangle": "均值矩形",
        "subject_rectangles": "个体矩形",
        "projected_mean": "均值 ± 标准误",
        "true_point": "真实点",
        "projected_point": "投射点",
        "n_subjects": "纳入被试",
        "schema": "数据格式",
        "range_note": "能力轴={ability:.1f}, 温暖轴={warmth:.1f}",
        "group_range_note": "能力轴均值={ability:.1f}±{ability_se:.1f}; 温暖轴均值={warmth:.1f}±{warmth_se:.1f}",
    },
    "en": {
        "face_prefix": "F",
        "subject_actual_title": "MR task: Subject {sub_no} actual reconstructed rectangle",
        "subject_projected_title": "MR task: Subject {sub_no} projected square reconstruction",
        "group_rectangles_title": "MR task: All subjects' reconstructed rectangles",
        "group_projection_title": "MR task: All subjects' projected square reconstructions",
        "x_actual": "Ability-axis length",
        "y_actual": "Warmth-axis length",
        "x_square": "Ability",
        "y_square": "Warmth",
        "subject_label": "Subject",
        "mean_rectangle": "Mean rectangle",
        "subject_rectangles": "Subject rectangles",
        "projected_mean": "Mean ± SE",
        "true_point": "True point",
        "projected_point": "Projected point",
        "n_subjects": "Included subjects",
        "schema": "Schema",
        "range_note": "Ability axis={ability:.1f}, Warmth axis={warmth:.1f}",
        "group_range_note": "Mean ability axis={ability:.1f}±{ability_se:.1f}; mean warmth axis={warmth:.1f}±{warmth_se:.1f}",
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
    df = filter_excluded_subjects(df)
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
        "df1": differences.shape[1],
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
        result = permutation_t2_test(differences, seed=RNG_SEED + int(face_frame["face"].iloc[0]), n_resamples=PERMUTATION_SAMPLES)
    result["n_subjects"] = int(differences.shape[0])
    result["shapiro_ability_p"] = shapiro_ability
    result["shapiro_warmth_p"] = shapiro_warmth
    return result


def prepare_analysis_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    subject_rows: list[dict[str, object]] = []
    point_rows: list[dict[str, object]] = []

    for row in raw.itertuples(index=False):
        legacy_schema = pd.notna(getattr(row, "Xrange", np.nan))
        ability_range = float(getattr(row, "Xrange")) if legacy_schema else float(getattr(row, "AbilityRange"))
        warmth_range = float(getattr(row, "Yrange")) if legacy_schema else float(getattr(row, "WarmthRange"))
        x_scale = ability_range
        y_scale = ability_range if legacy_schema else warmth_range
        schema = "legacy_xy" if legacy_schema else "warmth_ability"
        source = str(getattr(row, "source"))
        sub_no = int(getattr(row, "SubNo"))

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
            if legacy_schema:
                ability_pct = float(getattr(row, f"F{face}X"))
                warmth_pct = float(getattr(row, f"F{face}Y"))
            else:
                ability_pct = float(getattr(row, f"F{face}Ability"))
                warmth_pct = float(getattr(row, f"F{face}Warmth"))

            projected_ability = ability_pct * 4
            projected_warmth = warmth_pct * 4
            true_ability, true_warmth = FACE_TRUE_400[face]
            point_rows.append(
                {
                    "SubNo": sub_no,
                    "source": source,
                    "schema": schema,
                    "face": face,
                    "village": int(getattr(row, f"F{face}V")),
                    "ability_pct": ability_pct,
                    "warmth_pct": warmth_pct,
                    "actual_ability": ability_pct / 100 * x_scale,
                    "actual_warmth": warmth_pct / 100 * y_scale,
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


def draw_subject_actual_rectangle(
    subject_row: pd.Series,
    point_frame: pd.DataFrame,
    *,
    language: str,
) -> None:
    labels = LANG[language]
    ability_range = float(subject_row["ability_range"])
    warmth_range = float(subject_row["warmth_range"])
    max_x = max(ability_range, point_frame["actual_ability"].max()) * 1.08
    max_y = max(warmth_range, point_frame["actual_warmth"].max()) * 1.08

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
    ax.set_xlabel(labels["x_actual"])
    ax.set_ylabel(labels["y_actual"])
    ax.set_title(labels["subject_actual_title"].format(sub_no=int(subject_row["SubNo"])))
    ax.text(
        0.02,
        0.98,
        f"{labels['range_note'].format(ability=ability_range, warmth=warmth_range)}\n"
        f"{labels['schema']}: {subject_row['schema']}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, subject_output_dir(int(subject_row["SubNo"])), f"subject_actual_rectangle_{language}")


def draw_subject_projected_square(
    subject_row: pd.Series,
    point_frame: pd.DataFrame,
    *,
    language: str,
) -> None:
    labels = LANG[language]
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    setup_square_axis(ax, labels="zh" if language == "zh" else "en")
    add_true_face_points(ax, labels="zh" if language == "zh" else "en", size=58, marker="X", zorder=4)

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
            s=70,
            color=FACE_PALETTE[point.face],
            edgecolor="#1F2933",
            linewidth=0.8,
            zorder=3,
        )
        ax.text(
            point.projected_ability + 6,
            point.projected_warmth - 10,
            f"{labels['face_prefix']}{point.face}",
            fontsize=8,
            color="#1F2933",
            zorder=5,
        )

    ax.set_title(labels["subject_projected_title"].format(sub_no=int(subject_row["SubNo"])))
    ax.text(
        0.02,
        0.98,
        f"{labels['range_note'].format(ability=float(subject_row['ability_range']), warmth=float(subject_row['warmth_range']))}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, subject_output_dir(int(subject_row["SubNo"])), f"subject_projected_square_{language}")


def draw_group_rectangles(subject_summary: pd.DataFrame, *, language: str) -> None:
    labels = LANG[language]
    mean_ability = float(subject_summary["ability_range"].mean())
    mean_warmth = float(subject_summary["warmth_range"].mean())
    se_ability = float(subject_summary["ability_range"].std(ddof=1) / np.sqrt(len(subject_summary)))
    se_warmth = float(subject_summary["warmth_range"].std(ddof=1) / np.sqrt(len(subject_summary)))
    max_x = subject_summary["ability_range"].max() * 1.08
    max_y = subject_summary["warmth_range"].max() * 1.08

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
                alpha=0.18,
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
    ax.set_xlim(0, max_x)
    ax.set_ylim(0, max_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(labels["x_actual"])
    ax.set_ylabel(labels["y_actual"])
    ax.set_title(labels["group_rectangles_title"])
    ax.text(
        0.02,
        0.98,
        f"{labels['n_subjects']}: {len(subject_summary)}\n"
        f"{labels['group_range_note'].format(ability=mean_ability, ability_se=se_ability, warmth=mean_warmth, warmth_se=se_warmth)}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )
    save_figure(fig, GROUP_DIR, f"group_rectangles_{language}")


def draw_group_projection(point_summary: pd.DataFrame, face_summary: pd.DataFrame, *, language: str) -> None:
    labels = LANG[language]
    fig, ax = plt.subplots(figsize=(7.0, 6.4))
    setup_square_axis(ax, labels="zh" if language == "zh" else "en")
    add_true_face_points(ax, labels="zh" if language == "zh" else "en", size=62, marker="X", zorder=5)

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
            face_row["mean_projected_ability"] + 7,
            face_row["mean_projected_warmth"] - 10,
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
    save_figure(fig, GROUP_DIR, f"group_projected_square_{language}")


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
    summary["true_ability"] = summary["face"].map(lambda face: FACE_TRUE_400[int(face)][0])
    summary["true_warmth"] = summary["face"].map(lambda face: FACE_TRUE_400[int(face)][1])
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
        rows.append(
            {
                "face": int(face),
                **result,
            }
        )
    return pd.DataFrame(rows)


def write_report(
    subject_summary: pd.DataFrame,
    rectangle_test: dict[str, float | str | int],
    rectangle_summary: pd.DataFrame,
    face_summary: pd.DataFrame,
    face_tests: pd.DataFrame,
) -> None:
    legacy_n = int((subject_summary["schema"] == "legacy_xy").sum())
    modern_n = int((subject_summary["schema"] == "warmth_ability").sum())
    lines = [
        "MR task reconstruction analysis",
        "===============================",
        "",
        "Sample",
        "------",
        f"Included subjects: {len(subject_summary)}",
        f"Legacy X/Y schema subjects: {legacy_n}",
        f"Warmth/Ability schema subjects: {modern_n}",
        "",
        "Data handling",
        "-------------",
        "Raw files were loaded from data/MRtask_data with .mat preferred over .xlsx/.csv for duplicate stems.",
        "Base exclusions followed scripts/analysis_common.py filters: 1, 15, and 17.",
        f"Included subject pool follows completed-all-task participants: {list(completed_all_task_subject_ids())}.",
        "Legacy files used Xrange/Yrange plus F*X/F*Y fields. Based on the original task code, both F*X and F*Y were stored as percentages of Xrange.",
        "Warmth/Ability files used axis-specific percentages and axis lengths.",
        "Projected square coordinates were computed by multiplying stored percentages by 4 to map 0-100 values into the 400x400 square.",
        "",
        "Statistical methods",
        "-------------------",
        "Rectangle width-vs-height used a paired t-test when Shapiro-Wilk on within-subject differences was >= 0.05, otherwise a Wilcoxon signed-rank test.",
        "Per-face projected-vs-true tests used one-sample Hotelling T-squared when both coordinate differences passed Shapiro-Wilk; otherwise a sign-flip permutation test on the Hotelling statistic (20,000 resamples).",
        "",
        "Rectangle summary",
        "-----------------",
        *rectangle_summary.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        "Rectangle width-vs-height test",
        "------------------------------",
        *pd.DataFrame([rectangle_test]).to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        "Face projection summary",
        "-----------------------",
        *face_summary.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
        "",
        "Face projection tests",
        "---------------------",
        *face_tests.to_string(index=False, float_format=lambda value: f"{value:.4f}").splitlines(),
    ]
    (OUTPUT_DIR / "mrtask_reconstruction_report.txt").write_text("\n".join(lines), encoding="utf-8")


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
    point_summary.to_csv(OUTPUT_DIR / "subject_projected_points.csv", index=False)
    rectangle_summary.to_csv(OUTPUT_DIR / "group_rectangle_summary.csv", index=False)
    face_summary.to_csv(OUTPUT_DIR / "group_projected_face_summary.csv", index=False)
    pd.DataFrame([rectangle_test]).to_csv(OUTPUT_DIR / "rectangle_width_height_test.csv", index=False)
    face_tests.to_csv(OUTPUT_DIR / "face_projection_tests.csv", index=False)


def generate_subject_figures(subject_summary: pd.DataFrame, point_summary: pd.DataFrame) -> None:
    for subject_row in subject_summary.itertuples(index=False):
        point_frame = point_summary[point_summary["SubNo"] == subject_row.SubNo].copy()
        subject_series = pd.Series(subject_row._asdict())
        for language in ["zh", "en"]:
            draw_subject_actual_rectangle(subject_series, point_frame, language=language)
            draw_subject_projected_square(subject_series, point_frame, language=language)


def generate_group_figures(subject_summary: pd.DataFrame, point_summary: pd.DataFrame, face_summary: pd.DataFrame) -> None:
    for language in ["zh", "en"]:
        draw_group_rectangles(subject_summary, language=language)
        draw_group_projection(point_summary, face_summary, language=language)


def main() -> None:
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
    write_report(subject_summary, rectangle_test, rectangle_summary, face_summary, face_tests)


if __name__ == "__main__":
    main()
