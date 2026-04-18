from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io as sio
import seaborn as sns
from matplotlib import font_manager
from scipy import stats
from scipy.ndimage import gaussian_filter
from statsmodels.stats.anova import AnovaRM

from analysis_common import (
    completed_all_task_subject_ids,
    DATA_DIR,
    TASK_PALETTE,
    add_true_face_points,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    infer_date_from_path,
    infer_subno_from_path,
    mat_ret_to_df,
    save_figure,
    setup_square_axis,
)


LOGGER = logging.getLogger(__name__)
EP_DATA_DIR = DATA_DIR / "EPtask_data"
OUTPUT_DIR = ROOT / "results" / "eptask_learning_analysis"
TABLES_DIR = OUTPUT_DIR / "tables"
FIGURES_DIR = OUTPUT_DIR / "figures"
SUBJECT_FIGURES_DIR = FIGURES_DIR / "subjects"
GROUP_FIGURES_DIR = FIGURES_DIR / "group"
LANGUAGES = ("zh", "en")
PREFERRED_SUFFIX = {".mat": 0, ".xlsx": 1, ".csv": 2}
DAY_ORDER = [1, 2, 3]
DAY_COLORS = {
    1: TASK_PALETTE["blue"],
    2: TASK_PALETTE["orange"],
    3: TASK_PALETTE["green"],
}
FONT_PATH_CANDIDATES = [
    Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
]
FALLBACK_FONT_FAMILIES = ["Arial", "DejaVu Sans"]
REGISTERED_FONT_FAMILIES: list[str] | None = None


@dataclass
class MeasureStats:
    measure: str
    complete_n: int
    omnibus_method: str
    omnibus_statistic: float
    omnibus_p_value: float
    pairwise: pd.DataFrame


TEXT = {
    "zh": {
        "trajectory_title": "EP任务学习轨迹",
        "heatmap_title": "EP任务学习热力图",
        "group_heatmap_title": "EP任务群体学习热力图",
        "learning_time_title": "EP任务学习时间",
        "trial_count_title": "EP任务测试试次数",
        "day": "第{day}天",
        "day_short": "第{day}天",
        "subject": "被试{sub_no}",
        "date": "日期：{date}",
        "sessions": "学习阶段次数：{count}",
        "test_sessions": "测试阶段次数：{count}",
        "learn_time": "学习时间（秒）",
        "trial_count": "测试试次数",
        "density": "轨迹密度",
        "group_n": "被试数",
        "points": "坐标点数：{count}",
        "complete_n": "完整三天样本 n = {count}",
        "mean_se": "柱形为均值 ± SEM，散点为被试",
        "start": "起点",
        "end": "终点",
        "day_axis": "天数",
        "session": "阶段 {idx}",
        "missing": "缺失",
        "omnibus": "总体检验",
    },
    "en": {
        "trajectory_title": "EP Task Learning Trajectory",
        "heatmap_title": "EP Task Learning Heatmap",
        "group_heatmap_title": "EP Task Group Heatmap",
        "learning_time_title": "EP Task Learning Time",
        "trial_count_title": "EP Task Test Trials",
        "day": "Day {day}",
        "day_short": "Day {day}",
        "subject": "S{sub_no}",
        "date": "Date: {date}",
        "sessions": "Learning sessions: {count}",
        "test_sessions": "Test sessions: {count}",
        "learn_time": "Learning time (s)",
        "trial_count": "Test trials",
        "density": "Trajectory density",
        "group_n": "Participants",
        "points": "Coordinate points: {count}",
        "complete_n": "Complete 3-day sample n = {count}",
        "mean_se": "Bars show mean ± SEM; dots show subjects",
        "start": "Start",
        "end": "End",
        "day_axis": "Day",
        "session": "Session {idx}",
        "missing": "Missing",
        "omnibus": "Omnibus",
    },
}


def configure_ep_style() -> None:
    global REGISTERED_FONT_FAMILIES
    configure_plot_style(context="paper")
    if REGISTERED_FONT_FAMILIES is None:
        registered_fonts = []
        for font_path in FONT_PATH_CANDIDATES:
            if not font_path.exists():
                continue
            font_manager.fontManager.addfont(str(font_path))
            registered_fonts.append(font_manager.FontProperties(fname=str(font_path)).get_name())
        REGISTERED_FONT_FAMILIES = list(dict.fromkeys(registered_fonts + FALLBACK_FONT_FAMILIES))
    plt.rcParams["font.family"] = REGISTERED_FONT_FAMILIES
    plt.rcParams["font.sans-serif"] = REGISTERED_FONT_FAMILIES
    plt.rcParams["axes.unicode_minus"] = False


def session_index_from_path(path: Path) -> int:
    match = re.search(r"\d{4}-\d{2}-\d{2}(?:-(\d+))?\.", path.name)
    if not match:
        return 0
    return int(match.group(1) or 0)


def read_ep_test_file(path: Path) -> pd.DataFrame:
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
        raise ValueError(f"Unsupported EP test file: {path}")
    df["source"] = path.name
    return df


def select_preferred_files(paths: list[Path]) -> list[Path]:
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        by_stem[path.stem].append(path)
    selected = [
        sorted(stem_paths, key=lambda path: PREFERRED_SUFFIX.get(path.suffix, 99))[0]
        for stem_paths in by_stem.values()
    ]
    return sorted(selected, key=lambda path: (infer_subno_from_path(path) or -1, infer_date_from_path(path) or "", session_index_from_path(path)))


def load_learning_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    session_rows: list[dict[str, object]] = []
    coordinate_rows: list[dict[str, object]] = []

    learning_files = sorted(EP_DATA_DIR.glob("EPtask_learning-*.mat"))
    for path in learning_files:
        mat = sio.loadmat(path, squeeze_me=True, struct_as_record=False)
        if "learnSummary" not in mat:
            raise KeyError(f"`learnSummary` missing in {path}")
        summary = mat["learnSummary"]
        sub_no = int(getattr(summary, "SubNo"))
        date = str(getattr(summary, "Date", infer_date_from_path(path) or ""))
        session_rows.append(
            {
                "SubNo": sub_no,
                "date": date,
                "source": path.name,
                "session_index": session_index_from_path(path),
                "total_learning_time_s": float(getattr(summary, "TotalLearnTime", np.nan)),
                "return_to_learn_count": int(getattr(summary, "ReturnToLearnCount", 0)),
                "total_points": int(getattr(summary, "TotalPoints", 0)),
            }
        )

        coordinate_data = np.atleast_1d(getattr(summary, "CoordinateData"))
        coord_rows = []
        for point in coordinate_data:
            coord_rows.append(
                {
                    "SubNo": sub_no,
                    "date": date,
                    "source": path.name,
                    "session_index": session_index_from_path(path),
                    "leftBar": float(getattr(point, "leftBar", np.nan)),
                    "rightBar": float(getattr(point, "rightBar", np.nan)),
                    "timestamp_s": float(getattr(point, "timestamp", np.nan)),
                }
            )
        coord_df = pd.DataFrame(coord_rows).sort_values("timestamp_s", kind="mergesort")
        coord_df["point_order"] = np.arange(1, len(coord_df) + 1)
        coordinate_rows.extend(coord_df.to_dict("records"))

    session_df = pd.DataFrame(session_rows)
    coord_df = pd.DataFrame(coordinate_rows)
    session_df = filter_excluded_subjects(session_df)
    coord_df = filter_excluded_subjects(coord_df)
    session_df = filter_completed_subjects(session_df)
    coord_df = filter_completed_subjects(coord_df)
    return session_df.sort_values(["SubNo", "date", "session_index"]), coord_df.sort_values(
        ["SubNo", "date", "session_index", "timestamp_s", "point_order"]
    )


def load_test_trials() -> pd.DataFrame:
    raw_paths = [
        path
        for path in EP_DATA_DIR.iterdir()
        if path.is_file() and path.name.startswith("EPtask-") and not path.name.startswith("EPtask_learning-")
    ]
    selected_paths = select_preferred_files(raw_paths)
    frames: list[pd.DataFrame] = []
    for path in selected_paths:
        df = read_ep_test_file(path)
        df["SubNo"] = pd.to_numeric(df.get("SubNo"), errors="coerce")
        df["test_time"] = pd.to_numeric(df.get("test_time"), errors="coerce")
        df["acc"] = pd.to_numeric(df.get("acc"), errors="coerce")
        df["rt"] = pd.to_numeric(df.get("rt"), errors="coerce")
        df["face"] = pd.to_numeric(df.get("face"), errors="coerce")
        df["session_index"] = session_index_from_path(path)
        df["date"] = infer_date_from_path(path)
        frames.append(df)

    trials = pd.concat(frames, ignore_index=True)
    trials = filter_excluded_subjects(trials)
    trials = filter_completed_subjects(trials)
    trials["SubNo"] = trials["SubNo"].astype(int)
    return trials.sort_values(["SubNo", "date", "session_index"])


def attach_day_index(session_df: pd.DataFrame, coord_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_days = pd.concat(
        [
            session_df[["SubNo", "date"]],
            test_df[["SubNo", "date"]],
        ],
        ignore_index=True,
    ).drop_duplicates()
    all_days = all_days.sort_values(["SubNo", "date"]).reset_index(drop=True)
    all_days["day_index"] = all_days.groupby("SubNo").cumcount() + 1

    session_df = session_df.merge(all_days, on=["SubNo", "date"], how="left").sort_values(["SubNo", "date", "session_index"])
    coord_df = coord_df.merge(all_days, on=["SubNo", "date"], how="left").sort_values(
        ["SubNo", "date", "session_index", "timestamp_s", "point_order"]
    )
    test_df = test_df.merge(all_days, on=["SubNo", "date"], how="left").sort_values(["SubNo", "date", "session_index"])

    session_df["session_order"] = session_df.groupby(["SubNo", "date"]).cumcount() + 1
    coord_order = (
        session_df[["SubNo", "date", "source", "session_order"]]
        .drop_duplicates()
        .rename(columns={"source": "source"})
    )
    coord_df = coord_df.merge(coord_order, on=["SubNo", "date", "source"], how="left")

    test_sessions = (
        test_df[["SubNo", "date", "source", "session_index"]]
        .drop_duplicates()
        .sort_values(["SubNo", "date", "session_index"])
    )
    test_sessions["test_session_order"] = test_sessions.groupby(["SubNo", "date"]).cumcount() + 1
    test_df = test_df.merge(test_sessions, on=["SubNo", "date", "source", "session_index"], how="left")
    return session_df, coord_df, test_df


def build_daily_summary(session_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    learning_session_summary = session_df.sort_values(["SubNo", "date", "session_order"]).copy()
    test_session_summary = (
        test_df.groupby(["SubNo", "date", "day_index", "source", "session_index", "test_session_order"], as_index=False)
        .agg(
            n_trials=("SubNo", "size"),
            mean_accuracy=("acc", "mean"),
            mean_rt=("rt", "mean"),
        )
        .sort_values(["SubNo", "date", "test_session_order"])
    )

    learning_day = (
        session_df.groupby(["SubNo", "date", "day_index"], as_index=False)
        .agg(
            n_learning_sessions=("source", "nunique"),
            learning_time_s=("total_learning_time_s", "sum"),
            return_to_learn_count=("return_to_learn_count", "sum"),
            n_coordinate_points=("total_points", "sum"),
        )
        .sort_values(["SubNo", "day_index"])
    )
    test_day = (
        test_df.groupby(["SubNo", "date", "day_index"], as_index=False)
        .agg(
            n_test_sessions=("source", "nunique"),
            trial_count=("SubNo", "size"),
            mean_accuracy=("acc", "mean"),
            mean_rt=("rt", "mean"),
        )
        .sort_values(["SubNo", "day_index"])
    )

    day_summary = pd.merge(learning_day, test_day, on=["SubNo", "date", "day_index"], how="outer").sort_values(["SubNo", "day_index"])
    fill_zero_cols = ["n_learning_sessions", "learning_time_s", "return_to_learn_count", "n_coordinate_points", "n_test_sessions", "trial_count"]
    for column in fill_zero_cols:
        day_summary[column] = day_summary[column].fillna(0)
    day_summary["mean_accuracy"] = day_summary["mean_accuracy"].astype(float)
    day_summary["mean_rt"] = day_summary["mean_rt"].astype(float)
    integer_cols = ["SubNo", "day_index", "n_learning_sessions", "return_to_learn_count", "n_coordinate_points", "n_test_sessions", "trial_count"]
    day_summary[integer_cols] = day_summary[integer_cols].astype(int)
    return learning_session_summary, test_session_summary, learning_day, day_summary


def build_group_day_summary(day_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for measure in ["learning_time_s", "trial_count"]:
        summary = (
            day_summary.groupby("day_index")[measure]
            .agg(n_subjects="count", mean="mean", median="median", sd="std")
            .reset_index()
        )
        summary["se"] = summary["sd"] / np.sqrt(summary["n_subjects"])
        summary["measure"] = measure
        rows.extend(summary.to_dict("records"))
    return pd.DataFrame(rows).sort_values(["measure", "day_index"])


def select_complete_subjects(day_summary: pd.DataFrame) -> list[int]:
    expected_days = set(DAY_ORDER)
    rows = []
    for sub_no, subject_days in day_summary.groupby("SubNo", sort=True):
        observed_days = set(pd.to_numeric(subject_days["day_index"], errors="coerce").dropna().astype(int).tolist())
        if observed_days == expected_days:
            rows.append(int(sub_no))
    return rows


def paired_test_report(values_a: pd.Series, values_b: pd.Series, label_a: str, label_b: str) -> dict[str, float | str | int]:
    paired = pd.concat([values_a.rename(label_a), values_b.rename(label_b)], axis=1).dropna()
    diff = paired[label_a] - paired[label_b]
    shapiro = stats.shapiro(diff) if len(diff) >= 3 else None
    if shapiro is not None and shapiro.pvalue >= 0.05:
        test = stats.ttest_rel(paired[label_a], paired[label_b])
        method = "paired t-test"
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    else:
        test = stats.wilcoxon(paired[label_a], paired[label_b], zero_method="wilcox", alternative="two-sided")
        method = "Wilcoxon signed-rank test"
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    return {
        "comparison": f"{label_a} vs {label_b}",
        "day_a": int(label_a.replace("day", "")),
        "day_b": int(label_b.replace("day", "")),
        "n_subjects": int(len(paired)),
        "method": method,
        "mean_difference": float(diff.mean()),
        "sd_difference": float(diff.std(ddof=1)),
        "normality_shapiro_p": float(shapiro.pvalue) if shapiro is not None else np.nan,
        "statistic": statistic,
        "p_value": p_value,
    }


def compute_measure_stats(day_summary: pd.DataFrame, measure: str) -> MeasureStats:
    complete_subjects = (
        day_summary.groupby("SubNo")["day_index"].max().loc[lambda values: values >= 3].index
    )
    wide = (
        day_summary.loc[day_summary["SubNo"].isin(complete_subjects), ["SubNo", "day_index", measure]]
        .pivot(index="SubNo", columns="day_index", values=measure)
        .reindex(columns=DAY_ORDER)
        .dropna()
    )
    pairwise_rows = []
    normality_p_values = []
    for day_a, day_b in combinations(DAY_ORDER, 2):
        normality_p_values.append(stats.shapiro(wide[day_a] - wide[day_b]).pvalue)
        pairwise_rows.append(paired_test_report(wide[day_a], wide[day_b], f"day{day_a}", f"day{day_b}"))
    pairwise_df = pd.DataFrame(pairwise_rows)

    if all(p_value >= 0.05 for p_value in normality_p_values):
        long_df = wide.reset_index().melt(id_vars="SubNo", var_name="day_index", value_name=measure)
        long_df["day_index"] = long_df["day_index"].astype(str)
        result = AnovaRM(data=long_df, depvar=measure, subject="SubNo", within=["day_index"]).fit()
        omnibus_method = "Repeated-measures ANOVA"
        omnibus_statistic = float(result.anova_table["F Value"].iloc[0])
        omnibus_p_value = float(result.anova_table["Pr > F"].iloc[0])
    else:
        friedman = stats.friedmanchisquare(wide[1], wide[2], wide[3])
        omnibus_method = "Friedman test"
        omnibus_statistic = float(friedman.statistic)
        omnibus_p_value = float(friedman.pvalue)

    return MeasureStats(
        measure=measure,
        complete_n=int(wide.shape[0]),
        omnibus_method=omnibus_method,
        omnibus_statistic=omnibus_statistic,
        omnibus_p_value=omnibus_p_value,
        pairwise=pairwise_df,
    )


def format_day_tick(day_index: int, date: str, language: str) -> str:
    if language == "zh":
        return f"第{day_index}天\n{date}"
    return f"Day {day_index}\n{date}"


def p_value_to_stars(p_value: float) -> str:
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "ns"


def add_significance_annotations(ax: plt.Axes, pairwise_df: pd.DataFrame, y_max: float) -> None:
    if pairwise_df.empty:
        return
    height = max(y_max * 0.06, 1.0)
    start = y_max * 1.04 if y_max > 0 else 1.0
    for offset, row in enumerate(pairwise_df.sort_values(["day_a", "day_b"]).itertuples(index=False), start=0):
        x1 = row.day_a - 1
        x2 = row.day_b - 1
        y = start + offset * height
        ax.plot([x1, x1, x2, x2], [y, y + height * 0.25, y + height * 0.25, y], color="#1F2933", linewidth=0.9)
        ax.text((x1 + x2) / 2, y + height * 0.28, p_value_to_stars(row.p_value), ha="center", va="bottom", fontsize=9)


def render_heatmap(points: pd.DataFrame, bins: int = 100, sigma: float = 1.6) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    x = points["leftBar"].to_numpy(dtype=float)
    y = points["rightBar"].to_numpy(dtype=float)
    heatmap, x_edges, y_edges = np.histogram2d(x, y, bins=bins, range=[[0, 400], [0, 400]])
    heatmap = gaussian_filter(heatmap.T, sigma=sigma)
    return heatmap, (x_edges[0], x_edges[-1], y_edges[0], y_edges[-1])


def plot_subject_trajectory(points: pd.DataFrame, meta: pd.Series, language: str, output_dir: Path) -> None:
    configure_ep_style()
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    setup_square_axis(ax, labels=language)
    add_true_face_points(ax, labels=language)

    n_sessions = int(meta["n_learning_sessions"])
    session_palette = sns.color_palette("blend:#4C78A8,#B279A2", n_colors=max(n_sessions, 2))
    for session_order, session_points in points.groupby("session_order", sort=True):
        color = session_palette[int(session_order) - 1]
        ax.plot(
            session_points["leftBar"],
            session_points["rightBar"],
            color=color,
            linewidth=1.0,
            alpha=0.72,
            label=TEXT[language]["session"].format(idx=int(session_order)),
            zorder=2,
        )
        first_point = session_points.iloc[0]
        last_point = session_points.iloc[-1]
        ax.scatter(first_point["leftBar"], first_point["rightBar"], s=18, color=color, marker="o", zorder=3)
        ax.scatter(last_point["leftBar"], last_point["rightBar"], s=22, color=color, marker="s", zorder=3)

    labels = TEXT[language]
    title = (
        f"{labels['trajectory_title']}\n"
        f"{labels['subject'].format(sub_no=int(meta['SubNo']))} · {labels['day'].format(day=int(meta['day_index']))} · {meta['date']}"
    )
    ax.set_title(title, fontsize=11)
    info = "\n".join(
        [
            labels["date"].format(date=meta["date"]),
            labels["sessions"].format(count=int(meta["n_learning_sessions"])),
            labels["points"].format(count=int(meta["n_coordinate_points"])),
            f"{labels['learn_time']}: {meta['learning_time_s']:.1f}",
        ]
    )
    ax.text(
        0.02,
        0.98,
        info,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#D1D5DB"},
    )
    ax.legend(loc="lower right", fontsize=7, ncol=1)
    stem = f"sub-{int(meta['SubNo']):02d}_day-{int(meta['day_index'])}_trajectory_{language}"
    save_figure(fig, output_dir, stem)


def plot_subject_heatmap(points: pd.DataFrame, meta: pd.Series, language: str, output_dir: Path) -> None:
    configure_ep_style()
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    setup_square_axis(ax, labels=language)
    heatmap, extent = render_heatmap(points, bins=96, sigma=1.8)
    masked = np.ma.masked_where(heatmap <= 0, heatmap)
    image = ax.imshow(masked, extent=extent, origin="lower", cmap="magma", alpha=0.88, aspect="equal")
    add_true_face_points(ax, labels=language)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(TEXT[language]["density"])

    labels = TEXT[language]
    title = (
        f"{labels['heatmap_title']}\n"
        f"{labels['subject'].format(sub_no=int(meta['SubNo']))} · {labels['day'].format(day=int(meta['day_index']))} · {meta['date']}"
    )
    ax.set_title(title, fontsize=11)
    info = "\n".join(
        [
            labels["sessions"].format(count=int(meta["n_learning_sessions"])),
            labels["points"].format(count=int(meta["n_coordinate_points"])),
            f"{labels['learn_time']}: {meta['learning_time_s']:.1f}",
        ]
    )
    ax.text(
        0.02,
        0.98,
        info,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#D1D5DB"},
    )
    stem = f"sub-{int(meta['SubNo']):02d}_day-{int(meta['day_index'])}_heatmap_{language}"
    save_figure(fig, output_dir, stem)


def plot_subject_measure(day_rows: pd.DataFrame, measure: str, language: str, output_dir: Path) -> None:
    configure_ep_style()
    fig, ax = plt.subplots(figsize=(5.6, 3.9))
    ax.grid(axis="y")

    labels = TEXT[language]
    value_label = labels["learn_time"] if measure == "learning_time_s" else labels["trial_count"]
    title_label = labels["learning_time_title"] if measure == "learning_time_s" else labels["trial_count_title"]

    ordered = (
        pd.DataFrame({"day_index": DAY_ORDER})
        .merge(day_rows.sort_values("day_index"), on="day_index", how="left")
        .assign(SubNo=lambda df: df["SubNo"].ffill().bfill())
    )
    x_positions = np.arange(len(ordered))
    missing_mask = ordered[measure].isna()
    colors = [DAY_COLORS[int(day_index)] if not is_missing else "#E5E7EB" for day_index, is_missing in zip(ordered["day_index"], missing_mask)]
    values = ordered[measure].fillna(0).to_numpy(dtype=float)
    bars = ax.bar(
        x_positions,
        values,
        color=colors,
        edgecolor="#2F3437",
        linewidth=0.9,
        width=0.65,
    )

    for bar, value, is_missing in zip(bars, values, missing_mask):
        if is_missing:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                0.6,
                TEXT[language]["missing"],
                ha="center",
                va="bottom",
                fontsize=8,
                color="#6B7280",
            )
            bar.set_hatch("//")
            continue
        label = f"{value:.1f}" if measure == "learning_time_s" else f"{int(value)}"
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), label, ha="center", va="bottom", fontsize=8)

    tick_labels = [
        format_day_tick(int(row.day_index), "" if pd.isna(row.date) else str(row.date), language)
        for row in ordered.itertuples(index=False)
    ]
    ax.set_xticks(x_positions, labels=tick_labels)
    ax.set_xlabel(labels["day_axis"])
    ax.set_ylabel(value_label)
    ax.set_title(f"{title_label}\n{labels['subject'].format(sub_no=int(ordered['SubNo'].iloc[0]))}", fontsize=11)
    sns.despine(ax=ax)

    stem = (
        f"sub-{int(ordered['SubNo'].iloc[0]):02d}_learning_time_{language}"
        if measure == "learning_time_s"
        else f"sub-{int(ordered['SubNo'].iloc[0]):02d}_test_trials_{language}"
    )
    save_figure(fig, output_dir, stem)


def plot_group_heatmap(points: pd.DataFrame, day_index: int, language: str, output_dir: Path) -> None:
    configure_ep_style()
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    setup_square_axis(ax, labels=language)
    heatmap, extent = render_heatmap(points, bins=110, sigma=2.1)
    masked = np.ma.masked_where(heatmap <= 0, heatmap)
    image = ax.imshow(masked, extent=extent, origin="lower", cmap="magma", alpha=0.9, aspect="equal")
    add_true_face_points(ax, labels=language)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(TEXT[language]["density"])

    labels = TEXT[language]
    title = f"{labels['group_heatmap_title']}\n{labels['day'].format(day=day_index)}"
    ax.set_title(title, fontsize=11)
    n_subjects = points["SubNo"].nunique()
    ax.text(
        0.02,
        0.98,
        f"{labels['group_n']}: {n_subjects}\n{labels['points'].format(count=len(points))}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#D1D5DB"},
    )
    stem = f"group_day-{day_index}_heatmap_{language}"
    save_figure(fig, output_dir, stem)


def plot_group_measure(day_summary: pd.DataFrame, stats_result: MeasureStats, measure: str, language: str, output_dir: Path) -> None:
    configure_ep_style()
    labels = TEXT[language]
    title_label = labels["learning_time_title"] if measure == "learning_time_s" else labels["trial_count_title"]
    value_label = labels["learn_time"] if measure == "learning_time_s" else labels["trial_count"]

    figure_data = day_summary.loc[day_summary["day_index"].isin(DAY_ORDER)].copy()
    summary = (
        figure_data.groupby("day_index")[measure]
        .agg(n_subjects="count", mean="mean", sd="std")
        .reindex(DAY_ORDER)
        .reset_index()
    )
    summary["se"] = summary["sd"] / np.sqrt(summary["n_subjects"])
    tick_labels = [
        f"{labels['day_short'].format(day=int(day_index))}\n(n={int(n_subjects)})"
        for day_index, n_subjects in zip(summary["day_index"], summary["n_subjects"])
    ]

    fig, ax = plt.subplots(figsize=(6.3, 4.5))
    sns.barplot(
        data=figure_data,
        x="day_index",
        y=measure,
        order=DAY_ORDER,
        estimator="mean",
        errorbar="se",
        palette=[DAY_COLORS[day_index] for day_index in DAY_ORDER],
        edgecolor="#2F3437",
        linewidth=0.9,
        capsize=0.15,
        ax=ax,
    )
    sns.stripplot(
        data=figure_data,
        x="day_index",
        y=measure,
        order=DAY_ORDER,
        color="#1F2933",
        alpha=0.55,
        size=4.4,
        jitter=0.18,
        ax=ax,
    )

    y_max = float(max(np.nanmax(summary["mean"] + summary["se"]), figure_data[measure].max()))
    add_significance_annotations(ax, stats_result.pairwise, y_max)
    ax.set_xlabel(labels["day_axis"])
    ax.set_ylabel(value_label)
    ax.set_xticks(range(len(DAY_ORDER)), labels=tick_labels)
    ax.set_title(title_label, fontsize=11)
    info = (
        f"{labels['complete_n'].format(count=stats_result.complete_n)}\n"
        f"{labels['omnibus']}: {stats_result.omnibus_method}, p = {stats_result.omnibus_p_value:.4g}\n"
        f"{labels['mean_se']}"
    )
    ax.text(
        0.02,
        0.98,
        info,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.3,
        bbox={"facecolor": "white", "alpha": 0.92, "edgecolor": "#D1D5DB"},
    )
    sns.despine(ax=ax)

    stem = "group_learning_time_" + language if measure == "learning_time_s" else "group_test_trials_" + language
    save_figure(fig, output_dir, stem)


def write_stats_report(day_summary: pd.DataFrame, stats_results: dict[str, MeasureStats], output_path: Path) -> None:
    included_subjects = sorted(day_summary["SubNo"].unique().tolist())
    mr_subjects = list(completed_all_task_subject_ids())
    excluded_after_mr = [sub_no for sub_no in mr_subjects if sub_no not in included_subjects]
    lines = [
        "EP task learning/test analysis",
        "================================",
        "",
        "Data integration rules",
        "- Learning files are combined within subject-date across all `EPtask_learning-*.mat` sessions.",
        "- Test files are deduplicated by stem, preferring `.mat` over `.xlsx` over `.csv`, then combined within subject-date.",
        "- Subject exclusions follow `analysis_common.EXCLUDED_SUBNOS`: 1, 15, 17.",
        f"- EP analyses are restricted to subjects with completed MR task data: {mr_subjects}.",
        f"- Group summaries and figures include only subjects with all three EP days present: {included_subjects}.",
        "",
        f"Participants included: {day_summary['SubNo'].nunique()}",
        f"Complete 3-day participants: {stats_results['learning_time_s'].complete_n}",
        f"MR-complete subjects excluded for incomplete EP days: {excluded_after_mr if excluded_after_mr else 'None'}",
        "",
    ]

    for measure in ["learning_time_s", "trial_count"]:
        title = "Learning time (s)" if measure == "learning_time_s" else "Test trials"
        lines.extend([title, "-" * len(title)])
        descriptive = (
            day_summary.groupby("day_index")[measure]
            .agg(n="count", mean="mean", median="median", sd="std")
            .reindex(DAY_ORDER)
        )
        descriptive["se"] = descriptive["sd"] / np.sqrt(descriptive["n"])
        lines.append(descriptive.round(4).to_string())
        lines.append("")

        result = stats_results[measure]
        lines.append(
            f"Omnibus: {result.omnibus_method}, statistic = {result.omnibus_statistic:.4f}, p = {result.omnibus_p_value:.6g}"
        )
        lines.append("Pairwise comparisons:")
        for row in result.pairwise.sort_values(["day_a", "day_b"]).itertuples(index=False):
            lines.append(
                "  "
                + f"Day {row.day_a} vs Day {row.day_b}: {row.method}, n = {row.n_subjects}, "
                + f"mean diff = {row.mean_difference:.4f}, statistic = {row.statistic:.4f}, p = {row.p_value:.6g}, "
                + f"Shapiro p = {row.normality_shapiro_p:.6g}"
            )
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_tables(
    learning_session_summary: pd.DataFrame,
    test_session_summary: pd.DataFrame,
    learning_day: pd.DataFrame,
    day_summary: pd.DataFrame,
    group_day_summary: pd.DataFrame,
    stats_results: dict[str, MeasureStats],
) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    learning_session_summary.to_csv(TABLES_DIR / "learning_session_summary.csv", index=False)
    test_session_summary.to_csv(TABLES_DIR / "test_session_summary.csv", index=False)
    learning_day.to_csv(TABLES_DIR / "learning_day_summary.csv", index=False)
    day_summary.to_csv(TABLES_DIR / "subject_day_summary.csv", index=False)
    group_day_summary.to_csv(TABLES_DIR / "group_day_summary.csv", index=False)

    pairwise_frames = []
    for measure, result in stats_results.items():
        pairwise = result.pairwise.copy()
        pairwise["measure"] = measure
        pairwise["omnibus_method"] = result.omnibus_method
        pairwise["omnibus_statistic"] = result.omnibus_statistic
        pairwise["omnibus_p_value"] = result.omnibus_p_value
        pairwise["complete_n"] = result.complete_n
        pairwise_frames.append(pairwise)
    pd.concat(pairwise_frames, ignore_index=True).to_csv(TABLES_DIR / "pairwise_stats.csv", index=False)


def generate_subject_figures(coord_df: pd.DataFrame, day_summary: pd.DataFrame) -> None:
    for sub_no, subject_days in day_summary.groupby("SubNo", sort=True):
        subject_days = subject_days.sort_values("day_index")
        subject_dir = SUBJECT_FIGURES_DIR / f"sub-{int(sub_no):02d}"
        subject_dir.mkdir(parents=True, exist_ok=True)
        for language in LANGUAGES:
            plot_subject_measure(subject_days, "learning_time_s", language, subject_dir)
            plot_subject_measure(subject_days, "trial_count", language, subject_dir)

        for meta in subject_days.itertuples(index=False):
            day_points = coord_df.loc[(coord_df["SubNo"] == meta.SubNo) & (coord_df["day_index"] == meta.day_index)].copy()
            for language in LANGUAGES:
                if not day_points.empty:
                    plot_subject_trajectory(day_points, pd.Series(meta._asdict()), language, subject_dir)
                    plot_subject_heatmap(day_points, pd.Series(meta._asdict()), language, subject_dir)


def generate_group_figures(coord_df: pd.DataFrame, day_summary: pd.DataFrame, stats_results: dict[str, MeasureStats]) -> None:
    GROUP_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for day_index in DAY_ORDER:
        day_points = coord_df.loc[coord_df["day_index"] == day_index]
        if day_points.empty:
            continue
        for language in LANGUAGES:
            plot_group_heatmap(day_points, day_index, language, GROUP_FIGURES_DIR)

    for measure in ["learning_time_s", "trial_count"]:
        for language in LANGUAGES:
            plot_group_measure(day_summary, stats_results[measure], measure, language, GROUP_FIGURES_DIR)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading EP learning data")
    learning_sessions, coordinates = load_learning_data()
    LOGGER.info("Loading EP test trials")
    test_trials = load_test_trials()
    learning_sessions, coordinates, test_trials = attach_day_index(learning_sessions, coordinates, test_trials)
    learning_session_summary, test_session_summary, learning_day, day_summary = build_daily_summary(learning_sessions, test_trials)
    included_subjects = select_complete_subjects(day_summary)
    learning_sessions = learning_sessions.loc[learning_sessions["SubNo"].isin(included_subjects)].copy()
    coordinates = coordinates.loc[coordinates["SubNo"].isin(included_subjects)].copy()
    test_trials = test_trials.loc[test_trials["SubNo"].isin(included_subjects)].copy()
    learning_session_summary = learning_session_summary.loc[learning_session_summary["SubNo"].isin(included_subjects)].copy()
    test_session_summary = test_session_summary.loc[test_session_summary["SubNo"].isin(included_subjects)].copy()
    learning_day = learning_day.loc[learning_day["SubNo"].isin(included_subjects)].copy()
    day_summary = day_summary.loc[day_summary["SubNo"].isin(included_subjects)].copy()
    group_day_summary = build_group_day_summary(day_summary)
    stats_results = {
        "learning_time_s": compute_measure_stats(day_summary, "learning_time_s"),
        "trial_count": compute_measure_stats(day_summary, "trial_count"),
    }

    LOGGER.info("Exporting tables")
    export_tables(
        learning_session_summary=learning_session_summary,
        test_session_summary=test_session_summary,
        learning_day=learning_day,
        day_summary=day_summary,
        group_day_summary=group_day_summary,
        stats_results=stats_results,
    )

    LOGGER.info("Rendering subject figures")
    generate_subject_figures(coordinates, day_summary)
    LOGGER.info("Rendering group figures")
    generate_group_figures(coordinates, day_summary, stats_results)
    LOGGER.info("Writing statistics report")
    write_stats_report(day_summary, stats_results, OUTPUT_DIR / "stats_report.txt")
    LOGGER.info("Done. Outputs written to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
