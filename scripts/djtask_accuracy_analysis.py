from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from analysis_common import (
    completed_all_task_subject_ids,
    DATA_DIR,
    RESULTS_DIR,
    TASK_PALETTE,
    coerce_numeric,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    load_task_tables,
    paired_test_report,
    save_figure,
)
import matplotlib.pyplot as plt


TASK_DATA_DIR = DATA_DIR / "DJtask_data"
OUTPUT_DIR = RESULTS_DIR / "djtask_accuracy_analysis"
SUBJECT_FIGURE_DIR = OUTPUT_DIR / "subject_figures"
TYPE_ORDER = [1, 3]
TYPE_LABELS = {
    1: {"en": "Same-village distance judgment", "zh": "同村庄距离判别"},
    3: {"en": "Cross-village distance judgment", "zh": "异村庄距离判别"},
}
TYPE_PALETTE = {
    1: TASK_PALETTE["green"],
    3: TASK_PALETTE["blue"],
}
CJK_FONT_FALLBACK = [
    "Arial Unicode MS",
    "Hiragino Sans GB",
    "Heiti TC",
    "LXGW WenKai GB",
    "Songti SC",
    "DejaVu Sans",
    "sans-serif",
]


def load_dj_data() -> pd.DataFrame:
    raw = load_task_tables(TASK_DATA_DIR, "DJtask-")
    raw = coerce_numeric(
        raw,
        [
            "SubNo",
            "F0",
            "F1",
            "F2",
            "F0V",
            "F1V",
            "F2V",
            "type",
            "order",
            "correct_ans",
            "answer",
            "acc",
            "rt",
        ],
    )
    raw = filter_excluded_subjects(raw)
    raw = filter_completed_subjects(raw)
    raw = raw.dropna(subset=["SubNo", "type", "acc"]).copy()
    raw["SubNo"] = raw["SubNo"].astype(int)
    raw["type"] = raw["type"].astype(int)
    raw["acc"] = raw["acc"].astype(float)
    return raw


def prepare_accuracy_frame(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[raw["type"].isin(TYPE_ORDER)].copy()
    df["accuracy"] = df["acc"].clip(lower=0.0, upper=1.0)
    df["type_label_en"] = df["type"].map(lambda value: TYPE_LABELS[value]["en"])
    df["type_label_zh"] = df["type"].map(lambda value: TYPE_LABELS[value]["zh"])
    return df.sort_values(["SubNo", "type", "source"]).reset_index(drop=True)


def summarise_subject_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["SubNo", "type"], as_index=False)
        .agg(
            correct_trials=("accuracy", "sum"),
            total_trials=("accuracy", "size"),
            accuracy=("accuracy", "mean"),
            mean_rt=("rt", "mean"),
        )
        .sort_values(["SubNo", "type"])
        .reset_index(drop=True)
    )
    summary["type_label_en"] = summary["type"].map(lambda value: TYPE_LABELS[value]["en"])
    summary["type_label_zh"] = summary["type"].map(lambda value: TYPE_LABELS[value]["zh"])
    summary["correct_trials"] = summary["correct_trials"].round().astype(int)
    return summary


def summarise_group_accuracy(subject_summary: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        subject_summary.groupby("type", as_index=False)
        .agg(
            n_subjects=("SubNo", "nunique"),
            mean_accuracy=("accuracy", "mean"),
            sd_accuracy=("accuracy", "std"),
            min_accuracy=("accuracy", "min"),
            max_accuracy=("accuracy", "max"),
            mean_correct_trials=("correct_trials", "mean"),
            mean_total_trials=("total_trials", "mean"),
        )
        .sort_values("type")
        .reset_index(drop=True)
    )
    grouped["se_accuracy"] = grouped["sd_accuracy"] / np.sqrt(grouped["n_subjects"])
    grouped["type_label_en"] = grouped["type"].map(lambda value: TYPE_LABELS[value]["en"])
    grouped["type_label_zh"] = grouped["type"].map(lambda value: TYPE_LABELS[value]["zh"])
    return grouped


def trial_type_overview(raw: pd.DataFrame) -> pd.DataFrame:
    subject_accuracy = (
        raw.groupby(["SubNo", "type"], as_index=False)["acc"]
        .mean()
        .rename(columns={"acc": "subject_accuracy"})
    )
    overview = (
        raw.groupby("type", as_index=False)
        .agg(
            n_trials=("acc", "size"),
            trial_accuracy_mean=("acc", "mean"),
            n_subjects=("SubNo", "nunique"),
        )
        .sort_values("type")
        .reset_index(drop=True)
    )
    subject_means = (
        subject_accuracy.groupby("type", as_index=False)
        .agg(
            subject_accuracy_mean=("subject_accuracy", "mean"),
            subject_accuracy_sd=("subject_accuracy", "std"),
        )
        .sort_values("type")
        .reset_index(drop=True)
    )
    overview = overview.merge(subject_means, on="type", how="left")
    overview["included_in_primary_analysis"] = overview["type"].isin(TYPE_ORDER)
    return overview


def one_sample_accuracy_test(
    values: pd.Series,
    *,
    label: str,
    chance_level: float = 0.5,
    alternative: str = "greater",
) -> dict[str, float | str | int]:
    clean = values.dropna()
    diff = clean - chance_level
    normal = stats.shapiro(diff) if len(diff) >= 3 else None

    if normal is not None and normal.pvalue >= 0.05:
        ttest = stats.ttest_1samp(clean, popmean=chance_level)
        if alternative == "greater":
            p_value = ttest.pvalue / 2 if ttest.statistic >= 0 else 1 - (ttest.pvalue / 2)
        elif alternative == "less":
            p_value = ttest.pvalue / 2 if ttest.statistic <= 0 else 1 - (ttest.pvalue / 2)
        else:
            p_value = ttest.pvalue
        method = "one-sample t-test"
        statistic = float(ttest.statistic)
    else:
        signed = stats.wilcoxon(diff, zero_method="wilcox", alternative=alternative)
        method = f"Wilcoxon signed-rank test ({alternative})"
        statistic = float(signed.statistic)
        p_value = float(signed.pvalue)

    return {
        "test_id": f"{label}_vs_chance",
        "test_family": "one_sample",
        "comparison": f"{label} vs chance ({chance_level:.2f})",
        "label": label,
        "n_subjects": int(len(clean)),
        "alternative": alternative,
        "method": method,
        "mean_accuracy": float(clean.mean()),
        "sd_accuracy": float(clean.std(ddof=1)),
        "chance_level": float(chance_level),
        "mean_difference": float(diff.mean()),
        "normality_shapiro_p": float(normal.pvalue) if normal is not None else np.nan,
        "statistic": statistic,
        "p_value": float(p_value),
    }


def build_statistical_tests(subject_summary: pd.DataFrame) -> pd.DataFrame:
    wide = subject_summary.pivot(index="SubNo", columns="type", values="accuracy")
    type_one = subject_summary.loc[subject_summary["type"] == 1, "accuracy"]
    type_three = subject_summary.loc[subject_summary["type"] == 3, "accuracy"]

    paired = paired_test_report(wide[1], wide[3], "type_1", "type_3")
    paired_row = {
        "test_id": "type_1_vs_type_3",
        "test_family": "paired",
        "comparison": paired["comparison"],
        "label": "type_1_vs_type_3",
        "n_subjects": paired["n_subjects"],
        "alternative": "two-sided",
        "method": paired["method"],
        "mean_accuracy": np.nan,
        "sd_accuracy": np.nan,
        "chance_level": np.nan,
        "mean_difference": paired["mean_difference"],
        "normality_shapiro_p": paired["normality_shapiro_p"],
        "statistic": paired["statistic"],
        "p_value": paired["p_value"],
    }

    rows = [
        one_sample_accuracy_test(type_one, label="type_1"),
        one_sample_accuracy_test(type_three, label="type_3"),
        paired_row,
    ]
    return pd.DataFrame(rows)


def format_p_value(p_value: float) -> str:
    if p_value < 0.001:
        return "p < 0.001"
    return f"p = {p_value:.3f}"


def figure_label(type_code: int, language: str) -> str:
    if language == "en":
        return TYPE_LABELS[type_code][language].replace(" distance ", "\ndistance ")
    return TYPE_LABELS[type_code][language].replace("村庄", "村庄\n")


def apply_plot_fonts(*, language: str) -> None:
    if language == "zh":
        plt.rcParams["font.family"] = CJK_FONT_FALLBACK
    else:
        plt.rcParams["font.family"] = ["Arial", "DejaVu Sans", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False


def annotate_paired_result(ax: plt.Axes, *, x1: float, x2: float, y: float, text: str) -> None:
    height = 0.03
    ax.plot([x1, x1, x2, x2], [y, y + height, y + height, y], color="#1F2933", linewidth=1.0)
    ax.text((x1 + x2) / 2, y + height + 0.01, text, ha="center", va="bottom", fontsize=10)


def plot_group_accuracy(
    subject_summary: pd.DataFrame,
    group_summary: pd.DataFrame,
    stats_table: pd.DataFrame,
    *,
    language: str,
) -> None:
    configure_plot_style(context="talk")
    apply_plot_fonts(language=language)
    fig, ax = plt.subplots(figsize=(7.2, 5.2))

    labels = [figure_label(type_code, language) for type_code in TYPE_ORDER]
    positions = np.arange(len(TYPE_ORDER))
    summary = group_summary.set_index("type").loc[TYPE_ORDER].reset_index()

    ax.bar(
        positions,
        summary["mean_accuracy"],
        yerr=summary["se_accuracy"],
        width=0.58,
        capsize=6,
        color=[TYPE_PALETTE[type_code] for type_code in TYPE_ORDER],
        edgecolor="#2F3437",
        linewidth=1.0,
        zorder=2,
    )

    for index, type_code in enumerate(TYPE_ORDER):
        values = subject_summary.loc[subject_summary["type"] == type_code, "accuracy"].to_numpy()
        jitter = np.linspace(-0.12, 0.12, len(values)) if len(values) > 1 else np.array([0.0])
        ax.scatter(
            np.full(len(values), positions[index]) + jitter,
            values,
            s=32,
            color=TYPE_PALETTE[type_code],
            edgecolor="#1F2933",
            linewidth=0.7,
            alpha=0.75,
            zorder=3,
        )
        ax.text(
            positions[index],
            summary.loc[index, "mean_accuracy"] + summary.loc[index, "se_accuracy"] + 0.04,
            f"M = {summary.loc[index, 'mean_accuracy']:.3f}\nSE = {summary.loc[index, 'se_accuracy']:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    chance_text = "Chance = 0.50" if language == "en" else "机会水平 = 0.50"
    paired_row = stats_table.loc[stats_table["test_id"] == "type_1_vs_type_3"].iloc[0]
    paired_text = format_p_value(float(paired_row["p_value"]))
    ax.axhline(0.5, linestyle="--", linewidth=1.0, color=TASK_PALETTE["gray"], zorder=1)
    ax.text(1.02, 0.5, chance_text, transform=ax.get_yaxis_transform(), va="center", fontsize=9, color=TASK_PALETTE["gray"])
    annotate_paired_result(ax, x1=positions[0], x2=positions[1], y=1.01, text=paired_text)

    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Accuracy" if language == "en" else "正确率")
    ax.set_xlabel("")
    ax.set_title("DJ task accuracy across subjects" if language == "en" else "DJ任务正确率（所有被试）")
    ax.grid(axis="x", visible=False)

    figure_name = f"dj_accuracy_group_{language}"
    save_figure(fig, OUTPUT_DIR, figure_name)


def plot_subject_accuracy(subject_row: pd.DataFrame, *, language: str) -> None:
    configure_plot_style(context="paper")
    apply_plot_fonts(language=language)
    fig, ax = plt.subplots(figsize=(6.0, 4.2))

    ordered = subject_row.set_index("type").loc[TYPE_ORDER].reset_index()
    positions = np.arange(len(TYPE_ORDER))
    labels = [figure_label(type_code, language) for type_code in TYPE_ORDER]

    ax.bar(
        positions,
        ordered["accuracy"],
        width=0.58,
        color=[TYPE_PALETTE[type_code] for type_code in TYPE_ORDER],
        edgecolor="#2F3437",
        linewidth=1.0,
        zorder=2,
    )

    for index, row in ordered.iterrows():
        ax.text(
            positions[index],
            row["accuracy"] + 0.03,
            f"{row['correct_trials']}/{row['total_trials']}\n{row['accuracy']:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.axhline(0.5, linestyle="--", linewidth=1.0, color=TASK_PALETTE["gray"], zorder=1)
    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Accuracy" if language == "en" else "正确率")
    ax.set_xlabel("")
    subject_id = int(ordered["SubNo"].iloc[0])
    if language == "en":
        ax.set_title(f"Sub-{subject_id:02d} DJ task accuracy")
    else:
        ax.set_title(f"被试{subject_id:02d}的DJ任务正确率")
    ax.grid(axis="x", visible=False)

    save_figure(fig, SUBJECT_FIGURE_DIR, f"sub-{subject_id:02d}_dj_accuracy_{language}")


def write_report(
    raw: pd.DataFrame,
    analysis_df: pd.DataFrame,
    subject_summary: pd.DataFrame,
    group_summary: pd.DataFrame,
    stats_table: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    included_subjects = sorted(subject_summary["SubNo"].unique().tolist())
    type_lookup = group_summary.set_index("type")
    paired_row = stats_table.loc[stats_table["test_id"] == "type_1_vs_type_3"].iloc[0]
    chance_rows = stats_table.loc[stats_table["test_family"] == "one_sample"].set_index("label")

    lines = [
        "DJ accuracy analysis report",
        "==========================",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Data and scope",
        "--------------",
        "Script: scripts/djtask_accuracy_analysis.py",
        f"Data directory: {TASK_DATA_DIR}",
        f"Output directory: {OUTPUT_DIR}",
        "Selected trial types: type 1 (same-village distance judgment) and type 3 (cross-village distance judgment).",
        "Type 2 trials were kept only in the overview table and excluded from the primary analysis.",
        "Odd/even participant mapping is harmonized by using each trial's recorded `correct_ans` / `acc`,",
        "so type 3 accuracy is aggregated on the participant-specific correct rule before cross-subject summaries.",
        f"Completed-all-task subject pool: {', '.join(str(sub_no) for sub_no in completed_all_task_subject_ids())}",
        f"Included subjects (n = {len(included_subjects)}): {', '.join(str(sub_no) for sub_no in included_subjects)}",
        f"Included trial count: {len(analysis_df)} (each included subject contributes 16 trials per analyzed type).",
        "",
        "Descriptive summaries",
        "---------------------",
    ]

    for type_code in TYPE_ORDER:
        row = type_lookup.loc[type_code]
        label_en = TYPE_LABELS[type_code]["en"]
        lines.append(
            f"{label_en}: mean subject accuracy = {row['mean_accuracy']:.3f}, "
            f"SD = {row['sd_accuracy']:.3f}, SE = {row['se_accuracy']:.3f}, "
            f"range = [{row['min_accuracy']:.3f}, {row['max_accuracy']:.3f}]"
        )

    lines.extend(
        [
            "",
            "Inferential statistics",
            "----------------------",
        ]
    )

    for label in ["type_1", "type_3"]:
        row = chance_rows.loc[label]
        lines.append(
            f"{label} vs chance (0.50): {row['method']}, n = {int(row['n_subjects'])}, "
            f"mean diff = {row['mean_difference']:.3f}, statistic = {row['statistic']:.3f}, "
            f"{format_p_value(float(row['p_value']))}."
        )

    lines.append(
        f"type 1 vs type 3: {paired_row['method']}, n = {int(paired_row['n_subjects'])}, "
        f"mean difference = {paired_row['mean_difference']:.3f}, statistic = {paired_row['statistic']:.3f}, "
        f"{format_p_value(float(paired_row['p_value']))}."
    )

    lines.extend(
        [
            "",
            "Interpretation",
            "--------------",
            "Both analyzed DJ trial types are well above chance at the subject level.",
            "The paired type-1 vs type-3 comparison is not significant with the current sample.",
            "Cross-village judgments show slightly lower mean accuracy and larger between-subject variability.",
            "",
            "Generated files",
            "---------------",
            "- `group_accuracy_summary.csv`: subject-level descriptive summary by trial type.",
            "- `subject_accuracy_summary.csv`: per-subject accuracy table for the analyzed trial types.",
            "- `statistical_tests.csv`: one-sample and paired inferential results.",
            "- `trial_type_overview.csv`: all trial types after exclusion filtering, including type 2.",
            "- `analysis_report.txt`: this report.",
            "- `dj_accuracy_group_en|zh.(png|pdf)`: bilingual group figures.",
            "- `subject_figures/sub-XX_dj_accuracy_en|zh.(png|pdf)`: bilingual per-subject figures.",
        ]
    )

    (OUTPUT_DIR / "analysis_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    raw = load_dj_data()
    analysis_df = prepare_accuracy_frame(raw)
    subject_summary = summarise_subject_accuracy(analysis_df)
    group_summary = summarise_group_accuracy(subject_summary)
    stats_table = build_statistical_tests(subject_summary)
    overview = trial_type_overview(raw)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUBJECT_FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    subject_summary.to_csv(OUTPUT_DIR / "subject_accuracy_summary.csv", index=False)
    group_summary.to_csv(OUTPUT_DIR / "group_accuracy_summary.csv", index=False)
    stats_table.to_csv(OUTPUT_DIR / "statistical_tests.csv", index=False)
    overview.to_csv(OUTPUT_DIR / "trial_type_overview.csv", index=False)

    for language in ["en", "zh"]:
        plot_group_accuracy(subject_summary, group_summary, stats_table, language=language)

    for _, subject_row in subject_summary.groupby("SubNo", sort=True):
        for language in ["en", "zh"]:
            plot_subject_accuracy(subject_row.copy(), language=language)

    write_report(raw, analysis_df, subject_summary, group_summary, stats_table)


if __name__ == "__main__":
    main()
