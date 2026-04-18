from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from analysis_common import (
    TASK_PALETTE,
    coerce_numeric,
    completed_all_task_subject_ids,
    configure_plot_style,
    filter_completed_subjects,
    infer_date_from_path,
    infer_subno_from_path,
    read_table_file,
    reset_proc_output_dir,
    save_figure,
)


DATA_DIR = ROOT / "data" / "SPtask1_data"
OUTPUT_DIR = ROOT / "results" / "proc2_sptask_rt_analysis"
FIGURE_DIR = OUTPUT_DIR / "figures"
SUFFIX_PRIORITY = {".csv": 0, ".xlsx": 1, ".mat": 2}
NUMERIC_COLUMNS = [
    "SubNo",
    "Age",
    "block",
    "village",
    "face1",
    "face2",
    "false_time",
    "rt",
    "mean_false",
    "mean_rt",
]
TRIAL_EXPORT_COLUMNS = [
    "SubNo",
    "subject_label",
    "trial_index",
    "rt",
    "block",
    "village",
    "face1",
    "face2",
    "false_time",
    "mean_false",
    "mean_rt",
    "session_date",
    "source_file",
]


@dataclass
class OneSampleTestResult:
    metric: str
    n_subjects: int
    method: str
    shapiro_p: float
    mean: float
    median: float
    statistic: float
    p_value: float


def configure_bilingual_fonts() -> None:
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "Hiragino Sans GB",
        "Arial Unicode MS",
        "Songti SC",
        "Heiti TC",
        "LXGW WenKai GB",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def build_file_catalog(data_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(data_dir.iterdir()):
        if not path.is_file() or path.suffix not in SUFFIX_PRIORITY:
            continue

        df = read_table_file(path)
        sub_no = infer_subno_from_path(path)
        if sub_no is None and "SubNo" in df.columns:
            sub_values = pd.to_numeric(df["SubNo"], errors="coerce").dropna().unique()
            if len(sub_values) == 1:
                sub_no = int(sub_values[0])

        session_date = infer_date_from_path(path)
        rows.append(
            {
                "path": path,
                "source_file": path.name,
                "subno": sub_no,
                "session_date": session_date,
                "suffix": path.suffix,
                "suffix_priority": SUFFIX_PRIORITY[path.suffix],
                "n_rows": len(df),
                "has_date": bool(session_date),
            }
        )

    catalog = pd.DataFrame(rows)
    if catalog.empty:
        raise FileNotFoundError(f"No SPtask1 data files found in {data_dir}")

    catalog = filter_completed_subjects(catalog, "subno")
    catalog = catalog.dropna(subset=["subno"]).copy()
    catalog["subno"] = catalog["subno"].astype(int)
    catalog["session_date"] = pd.to_datetime(catalog["session_date"], errors="coerce")
    return catalog


def select_subject_files(catalog: pd.DataFrame) -> pd.DataFrame:
    selected = (
        catalog.sort_values(
            ["subno", "has_date", "session_date", "n_rows", "suffix_priority"],
            ascending=[True, False, False, False, True],
        )
        .drop_duplicates(subset=["subno"], keep="first")
        .sort_values("subno")
        .reset_index(drop=True)
    )
    return selected


def load_selected_sessions(selected_files: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for row in selected_files.itertuples(index=False):
        df = read_table_file(row.path).copy()
        df["source_file"] = row.source_file
        df["session_date"] = row.session_date.strftime("%Y-%m-%d") if pd.notna(row.session_date) else ""
        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)
    raw = filter_completed_subjects(raw, "SubNo")
    raw = coerce_numeric(raw, NUMERIC_COLUMNS)
    raw = raw.dropna(subset=["SubNo", "rt"]).copy()
    raw["SubNo"] = raw["SubNo"].astype(int)
    raw["trial_index"] = raw.groupby("SubNo").cumcount() + 1
    raw["subject_label"] = raw["SubNo"].map(lambda value: f"S{value:02d}")
    return raw


def summarize_subjects(trial_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        trial_df.groupby(["SubNo", "subject_label", "source_file", "session_date"], as_index=False)["rt"]
        .agg(
            n_trials="size",
            mean_rt="mean",
            median_rt="median",
            sd_rt="std",
            min_rt="min",
            max_rt="max",
        )
        .sort_values("SubNo")
    )
    return summary


def summarize_trial_positions(trial_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        trial_df.groupby("trial_index", as_index=False)["rt"]
        .agg(n_subjects="size", mean_rt="mean", sd_rt="std", median_rt="median", min_rt="min", max_rt="max")
        .sort_values("trial_index")
    )
    summary["se_rt"] = summary["sd_rt"] / np.sqrt(summary["n_subjects"])
    return summary


def summarize_subject_trends(trial_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for sub_no, sub_df in trial_df.groupby("SubNo", sort=True):
        x_values = sub_df["trial_index"].to_numpy(dtype=float)
        y_values = sub_df["rt"].to_numpy(dtype=float)

        if len(sub_df) < 2:
            slope = np.nan
            intercept = np.nan
            r_value = np.nan
            p_value = np.nan
            stderr = np.nan
            spearman_rho = np.nan
            spearman_p = np.nan
        else:
            slope, intercept, r_value, p_value, stderr = stats.linregress(x_values, y_values)
            spearman_rho, spearman_p = stats.spearmanr(x_values, y_values)

        rows.append(
            {
                "SubNo": int(sub_no),
                "subject_label": sub_df["subject_label"].iloc[0],
                "n_trials": int(len(sub_df)),
                "slope_rt_per_trial": float(slope),
                "intercept_rt": float(intercept),
                "pearson_r": float(r_value),
                "linreg_p_value": float(p_value),
                "linreg_stderr": float(stderr),
                "spearman_rho": float(spearman_rho),
                "spearman_p_value": float(spearman_p),
            }
        )
    return pd.DataFrame(rows).sort_values("SubNo").reset_index(drop=True)


def run_one_sample_zero_test(values: pd.Series, metric: str) -> OneSampleTestResult:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        raise ValueError(f"No values available for {metric}")

    shapiro_p = float(stats.shapiro(clean).pvalue) if len(clean) >= 3 else np.nan
    if len(clean) >= 3 and shapiro_p >= 0.05:
        test = stats.ttest_1samp(clean, popmean=0.0)
        method = "one-sample t-test"
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    else:
        centered = clean - 0.0
        if np.allclose(centered.to_numpy(), 0.0):
            method = "Wilcoxon signed-rank test"
            statistic = 0.0
            p_value = 1.0
        else:
            test = stats.wilcoxon(centered, zero_method="wilcox", alternative="two-sided")
            method = "Wilcoxon signed-rank test"
            statistic = float(test.statistic)
            p_value = float(test.pvalue)

    return OneSampleTestResult(
        metric=metric,
        n_subjects=int(len(clean)),
        method=method,
        shapiro_p=shapiro_p,
        mean=float(clean.mean()),
        median=float(clean.median()),
        statistic=statistic,
        p_value=p_value,
    )


def save_csv_outputs(
    selected_files: pd.DataFrame,
    trial_df: pd.DataFrame,
    subject_summary: pd.DataFrame,
    trial_summary: pd.DataFrame,
    trend_summary: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected_export = selected_files.copy()
    selected_export["session_date"] = selected_export["session_date"].dt.strftime("%Y-%m-%d")
    selected_export[["subno", "session_date", "source_file", "suffix", "n_rows"]].rename(
        columns={"subno": "SubNo", "n_rows": "n_trials"}
    ).to_csv(OUTPUT_DIR / "selected_sessions.csv", index=False)

    available_trial_columns = [column for column in TRIAL_EXPORT_COLUMNS if column in trial_df.columns]
    trial_df[available_trial_columns].to_csv(OUTPUT_DIR / "trial_level_rt.csv", index=False)
    subject_summary.to_csv(OUTPUT_DIR / "subject_rt_summary.csv", index=False)
    trial_summary.to_csv(OUTPUT_DIR / "trial_position_summary.csv", index=False)
    trend_summary.to_csv(OUTPUT_DIR / "subject_trend_summary.csv", index=False)


def label_text(labels: str) -> dict[str, str]:
    if labels == "zh":
        return {
            "trial": "试次编号",
            "rt": "反应时（秒）",
            "subject_title": "Proc2 / SP任务被试{subject}反应时轨迹",
            "subject_subtitle": "数据文件：{source}；日期：{date}；试次数：{n_trials}",
            "group_title": "Proc2 / SP任务所有被试反应时轨迹",
            "group_subtitle": "浅灰线为单名被试；蓝线为跨被试均值，阴影为 ±1 SEM。",
            "mean_rt": "跨被试均值",
        }
    return {
        "trial": "Trial index",
        "rt": "Reaction time (s)",
        "subject_title": "Proc2 / SP task RT trajectory for {subject}",
        "subject_subtitle": "Source: {source}; date: {date}; trials: {n_trials}",
        "group_title": "Proc2 / SP task RT trajectories across subjects",
        "group_subtitle": "Light gray lines show subjects; the blue line shows the across-subject mean with ±1 SEM.",
        "mean_rt": "Across-subject mean",
    }


def add_block_guides(ax: plt.Axes, sub_df: pd.DataFrame) -> None:
    if "block" not in sub_df.columns or sub_df["block"].isna().all():
        return
    block_change_positions = sub_df.loc[sub_df["block"].ne(sub_df["block"].shift()), "trial_index"].tolist()[1:]
    for position in block_change_positions:
        ax.axvline(position - 0.5, color="#D1D5DB", linestyle="--", linewidth=0.9, zorder=0)


def plot_subject_rt(sub_df: pd.DataFrame, labels: str) -> None:
    text = label_text(labels)
    subject_label = sub_df["subject_label"].iloc[0]
    source_file = sub_df["source_file"].iloc[0]
    session_date = sub_df["session_date"].iloc[0] or "NA"
    n_trials = len(sub_df)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(
        sub_df["trial_index"],
        sub_df["rt"],
        color=TASK_PALETTE["blue"],
        linewidth=1.8,
        marker="o",
        markersize=4.0,
        markerfacecolor="white",
        markeredgewidth=0.9,
        markeredgecolor=TASK_PALETTE["blue"],
        zorder=3,
    )
    add_block_guides(ax, sub_df)
    ax.axhline(sub_df["rt"].mean(), color=TASK_PALETTE["orange"], linestyle="--", linewidth=1.1, alpha=0.86, zorder=1)
    ax.set_xlabel(text["trial"])
    ax.set_ylabel(text["rt"])
    ax.set_title(text["subject_title"].format(subject=subject_label), pad=14, fontsize=15)
    ax.text(
        0.5,
        1.01,
        text["subject_subtitle"].format(source=source_file, date=session_date, n_trials=n_trials),
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8.5,
        color="#4B5563",
    )
    ax.set_xlim(1, max(int(sub_df["trial_index"].max()), 1))
    ax.grid(axis="x", visible=False)
    sns_despine(ax)
    save_figure(fig, OUTPUT_DIR, f"figures/{subject_label.lower()}_rt_{labels}")


def plot_group_rt(trial_df: pd.DataFrame, trial_summary: pd.DataFrame, labels: str) -> None:
    text = label_text(labels)
    fig, ax = plt.subplots(figsize=(9.2, 5.4))

    for _, sub_df in trial_df.groupby("SubNo", sort=True):
        ax.plot(
            sub_df["trial_index"],
            sub_df["rt"],
            color="#9CA3AF",
            linewidth=0.8,
            alpha=0.24,
            zorder=1,
        )

    summary = trial_summary.sort_values("trial_index").copy()
    x_values = summary["trial_index"].to_numpy(dtype=float)
    mean_values = summary["mean_rt"].to_numpy(dtype=float)
    se_values = summary["se_rt"].fillna(0).to_numpy(dtype=float)
    ax.fill_between(
        x_values,
        mean_values - se_values,
        mean_values + se_values,
        color=TASK_PALETTE["blue"],
        alpha=0.18,
        linewidth=0,
        zorder=2,
    )
    ax.plot(
        x_values,
        mean_values,
        color=TASK_PALETTE["blue"],
        linewidth=2.4,
        marker="o",
        markersize=3.8,
        markerfacecolor="white",
        markeredgecolor=TASK_PALETTE["blue"],
        markeredgewidth=0.9,
        label=text["mean_rt"],
        zorder=4,
    )

    ax.set_xlabel(text["trial"])
    ax.set_ylabel(text["rt"])
    ax.set_title(text["group_title"], pad=14, fontsize=18)
    ax.text(0.5, 1.002, text["group_subtitle"], transform=ax.transAxes, ha="center", va="bottom", fontsize=8.5, color="#4B5563")
    ax.set_xlim(1, max(int(trial_df["trial_index"].max()), 1))
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    sns_despine(ax)
    save_figure(fig, OUTPUT_DIR, f"figures/all_subjects_rt_{labels}")


def sns_despine(ax: plt.Axes) -> None:
    import seaborn as sns

    sns.despine(ax=ax)


def write_report(
    selected_files: pd.DataFrame,
    trial_df: pd.DataFrame,
    subject_summary: pd.DataFrame,
    trial_summary: pd.DataFrame,
    trend_summary: pd.DataFrame,
    slope_test: OneSampleTestResult,
) -> None:
    negative_slopes = int((trend_summary["slope_rt_per_trial"] < 0).sum())
    significant_negative = int(
        ((trend_summary["slope_rt_per_trial"] < 0) & (trend_summary["linreg_p_value"] < 0.05)).sum()
    )
    rt_values = trial_df["rt"]

    interpretation_line = (
        "- Subject-level RT slopes were approximately normal, so the report used a two-sided one-sample t-test against zero."
        if slope_test.method == "one-sample t-test"
        else "- Subject-level RT slopes were non-normal, so the report used a two-sided Wilcoxon signed-rank test against zero."
    )

    lines = [
        "Proc2 / SP task RT analysis / Proc2 / SP任务反应时分析",
        "====================================================",
        "",
        "Data selection / 数据选择",
        "------------------------",
        "- Proc mapping: proc2 = village classification / SP task.",
        "- SP RT analysis does not use coordinate scaling.",
        "- Participant inclusion used the shared `filter_completed_subjects()` completed-subject filter.",
        f"- Completed-all-task subject pool from `completed_all_task_subject_ids()`: {list(completed_all_task_subject_ids())}.",
        "- Kept one session per subject after deduplicating parallel exports (.csv/.xlsx/.mat).",
        "- When the same session had multiple exports, the script kept the most complete file and then preferred csv > xlsx > mat.",
        "- When a subject had multiple dated sessions, the most recent dated session was kept.",
        "",
        "Sample overview / 样本概览",
        "--------------------------",
        f"- Included subjects: {subject_summary['SubNo'].nunique()}",
        f"- Total analyzed trials: {len(trial_df)}",
        f"- Selected source files: {len(selected_files)}",
        f"- Trial-count range per subject: {int(subject_summary['n_trials'].min())} to {int(subject_summary['n_trials'].max())}",
        f"- Overall RT mean ± SD: {rt_values.mean():.3f} ± {rt_values.std(ddof=1):.3f} s",
        f"- Overall RT median [min, max]: {rt_values.median():.3f} [{rt_values.min():.3f}, {rt_values.max():.3f}] s",
        f"- Mean RT at trial 1: {trial_summary.loc[trial_summary['trial_index'] == 1, 'mean_rt'].iloc[0]:.3f} s",
        f"- Mean RT at the last available trial ({int(trial_summary['trial_index'].max())}): {trial_summary.iloc[-1]['mean_rt']:.3f} s",
        "",
        "Trend summary / 趋势概览",
        "------------------------",
        "- Each subject was summarized by a simple linear slope from rt ~ trial_index.",
        f"- Subjects with negative slopes: {negative_slopes}/{len(trend_summary)}",
        f"- Subjects with individually significant negative slopes (p < 0.05): {significant_negative}/{len(trend_summary)}",
        f"- Mean slope: {trend_summary['slope_rt_per_trial'].mean():.3f} s/trial",
        f"- Median slope: {trend_summary['slope_rt_per_trial'].median():.3f} s/trial",
        "",
        "Inferential test / 推断检验",
        "--------------------------",
        f"- Metric tested: {slope_test.metric}",
        f"- Shapiro-Wilk p-value: {slope_test.shapiro_p:.4f}",
        f"- Method: {slope_test.method}",
        f"- n = {slope_test.n_subjects}, statistic = {slope_test.statistic:.4f}, p = {slope_test.p_value:.6f}",
        f"- Mean tested value = {slope_test.mean:.3f}, median tested value = {slope_test.median:.3f}",
        "",
        "Interpretation / 解释",
        "---------------------",
        interpretation_line,
        "- The negative median slope indicates that RT generally decreased over trials, consistent with practice-related speeding in this task.",
        "- Later trial positions contain fewer subjects because session lengths vary, so late-trial group summaries should be read with that changing denominator in mind.",
        "",
        "Outputs / 输出文件",
        "------------------",
        f"- Selected-session table: {OUTPUT_DIR / 'selected_sessions.csv'}",
        f"- Trial-level RT table: {OUTPUT_DIR / 'trial_level_rt.csv'}",
        f"- Subject summary table: {OUTPUT_DIR / 'subject_rt_summary.csv'}",
        f"- Trial-position summary table: {OUTPUT_DIR / 'trial_position_summary.csv'}",
        f"- Subject trend table: {OUTPUT_DIR / 'subject_trend_summary.csv'}",
        f"- Figures directory: {FIGURE_DIR}",
    ]

    (OUTPUT_DIR / "rt_analysis_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    reset_proc_output_dir(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    configure_plot_style("talk")
    configure_bilingual_fonts()

    file_catalog = build_file_catalog(DATA_DIR)
    selected_files = select_subject_files(file_catalog)
    trial_df = load_selected_sessions(selected_files)
    subject_summary = summarize_subjects(trial_df)
    trial_summary = summarize_trial_positions(trial_df)
    trend_summary = summarize_subject_trends(trial_df)
    slope_test = run_one_sample_zero_test(trend_summary["slope_rt_per_trial"], "subject slope of rt ~ trial_index")

    save_csv_outputs(selected_files, trial_df, subject_summary, trial_summary, trend_summary)
    for labels in ("zh", "en"):
        for _, sub_df in trial_df.groupby("SubNo", sort=True):
            plot_subject_rt(sub_df, labels)
        plot_group_rt(trial_df, trial_summary, labels)
    write_report(selected_files, trial_df, subject_summary, trial_summary, trend_summary, slope_test)


if __name__ == "__main__":
    main()
