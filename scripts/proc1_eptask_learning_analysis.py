from __future__ import annotations

import logging
import os
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
from matplotlib import colors as mcolors
from scipy import stats
from scipy.ndimage import gaussian_filter
from statsmodels.stats.anova import AnovaRM

from analysis_common import (
    BAR_EDGE_COLOR,
    BAR_LINEWIDTH,
    BAR_WIDTH,
    DATA_DIR,
    FACE_TRUE_RAW,
    TASK_PALETTE,
    add_true_face_points_0_to_10,
    bar_error_kw,
    bar_scatter_kw,
    completed_all_task_subject_ids,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    infer_date_from_path,
    infer_square_side_from_face_truth,
    infer_subno_from_path,
    jittered_x,
    mat_ret_to_df,
    pixels_to_true_space,
    reset_proc_output_dir,
    save_figure,
    session_index_from_path,
    setup_true_space_axis,
)


LOGGER = logging.getLogger(__name__)
EP_DATA_DIR = DATA_DIR / "EPtask_data"
OUTPUT_DIR = ROOT / "results" / "proc1_eptask_learning_analysis"
TABLES_DIR = OUTPUT_DIR / "tables"
FIGURES_DIR = OUTPUT_DIR / "figures"
SUBJECT_FIGURES_DIR = FIGURES_DIR / "subjects"
GROUP_FIGURES_DIR = FIGURES_DIR / "group"
LANGUAGES = ("zh", "en")
DAY_ORDER = [1, 2, 3]
PREFERRED_SUFFIX = {".mat": 0, ".xlsx": 1, ".csv": 2}
NUMERIC_TEST_COLUMNS = [
    "SubNo",
    "test_time",
    "true_leftBar",
    "true_rightBar",
    "leftBarLength",
    "rightBarLength",
    "face",
    "acc",
    "rt",
]
DAY_COLORS = {
    1: TASK_PALETTE["blue"],
    2: TASK_PALETTE["orange"],
    3: TASK_PALETTE["green"],
}
HEATMAP_LOW_DENSITY_GAMMA = 0.55
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
        "trajectory_title": "EP任务探索轨迹",
        "heatmap_title": "EP任务探索热力图",
        "group_heatmap_title": "EP任务群体探索热力图",
        "learning_time_title": "EP任务探索时间",
        "trial_count_title": "EP任务测试试次数",
        "day": "第{day}天",
        "day_short": "第{day}天",
        "subject": "被试{sub_no}",
        "date": "日期：{date}",
        "sessions": "探索阶段次数：{count}",
        "test_sessions": "测试阶段次数：{count}",
        "learn_time": "探索停留时间（秒）",
        "trial_count": "测试试次数",
        "density": "轨迹密度",
        "group_n": "被试数",
        "points": "坐标点数：{count}",
        "complete_n": "完整三天样本 n = {count}",
        "mean_se": "柱形为均值 ± SEM，散点为被试",
        "day_axis": "天数",
        "session": "阶段 {idx}",
        "missing": "缺失",
        "omnibus": "总体检验",
        "square_side": "squareSidePx：{value}",
        "all_days": "全部天数",
    },
    "en": {
        "trajectory_title": "EP Task Explore Trajectory",
        "heatmap_title": "EP Task Explore Heatmap",
        "group_heatmap_title": "EP Task Group Explore Heatmap",
        "learning_time_title": "EP Task Explore Time",
        "trial_count_title": "EP Task Test Trials",
        "day": "Day {day}",
        "day_short": "Day {day}",
        "subject": "S{sub_no}",
        "date": "Date: {date}",
        "sessions": "Explore sessions: {count}",
        "test_sessions": "Test sessions: {count}",
        "learn_time": "Explore dwell time (s)",
        "trial_count": "Test trials",
        "density": "Trajectory density",
        "group_n": "Participants",
        "points": "Coordinate points: {count}",
        "complete_n": "Complete 3-day sample n = {count}",
        "mean_se": "Bars show mean ± SEM; dots show subjects",
        "day_axis": "Day",
        "session": "Session {idx}",
        "missing": "Missing",
        "omnibus": "Omnibus",
        "square_side": "squareSidePx: {value}",
        "all_days": "All days",
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
    df["source_stem"] = path.stem
    df["date"] = infer_date_from_path(path)
    df["session_index"] = session_index_from_path(path)
    if "SubNo" not in df.columns:
        df["SubNo"] = infer_subno_from_path(path)
    for column in NUMERIC_TEST_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


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


def load_test_trials() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_paths = [
        path
        for path in EP_DATA_DIR.iterdir()
        if path.is_file() and path.name.startswith("EPtask-") and not path.name.startswith("EPtask_learning-")
    ]
    selected_paths = select_preferred_files(raw_paths)
    selected_files = pd.DataFrame(
        [
            {
                "source": path.name,
                "source_stem": path.stem,
                "suffix": path.suffix,
                "SubNo_from_path": infer_subno_from_path(path),
                "date_from_path": infer_date_from_path(path),
                "session_index": session_index_from_path(path),
            }
            for path in selected_paths
        ]
    )
    frames = [read_ep_test_file(path) for path in selected_paths]
    if not frames:
        raise FileNotFoundError(f"No EP test files found in {EP_DATA_DIR}")

    trials = pd.concat(frames, ignore_index=True)
    trials = trials.dropna(subset=["SubNo", "date"]).copy()
    trials["SubNo"] = trials["SubNo"].astype(int)
    trials = filter_excluded_subjects(trials)
    trials = filter_completed_subjects(trials)
    trials = trials.sort_values(["SubNo", "date", "session_index", "source"]).reset_index(drop=True)
    return trials, selected_files


def load_learning_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    session_rows: list[dict[str, object]] = []
    coordinate_rows: list[dict[str, object]] = []

    for path in sorted(EP_DATA_DIR.glob("EPtask_learning-*.mat")):
        mat = sio.loadmat(path, squeeze_me=True, struct_as_record=False)
        if "learnSummary" not in mat:
            raise KeyError(f"`learnSummary` missing in {path}")
        summary = mat["learnSummary"]
        sub_no = int(getattr(summary, "SubNo"))
        date = str(getattr(summary, "Date", infer_date_from_path(path) or ""))
        session_index = session_index_from_path(path)
        session_rows.append(
            {
                "SubNo": sub_no,
                "date": date,
                "source": path.name,
                "session_index": session_index,
                "total_learning_time_s": float(getattr(summary, "TotalLearnTime", np.nan)),
                "return_to_learn_count": int(getattr(summary, "ReturnToLearnCount", 0)),
                "total_points": int(getattr(summary, "TotalPoints", 0)),
            }
        )

        coord_rows: list[dict[str, object]] = []
        for point in np.atleast_1d(getattr(summary, "CoordinateData")):
            coord_rows.append(
                {
                    "SubNo": sub_no,
                    "date": date,
                    "source": path.name,
                    "session_index": session_index,
                    "leftBar_px": float(getattr(point, "leftBar", np.nan)),
                    "rightBar_px": float(getattr(point, "rightBar", np.nan)),
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
    return (
        session_df.sort_values(["SubNo", "date", "session_index"]).reset_index(drop=True),
        coord_df.sort_values(["SubNo", "date", "session_index", "timestamp_s", "point_order"]).reset_index(drop=True),
    )


def estimate_trial_axes(test_trials: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    required = ["SubNo", "date", "source", "session_index", "face", "true_leftBar", "true_rightBar"]
    inference_data = test_trials.dropna(subset=required).copy()
    inference_data["face"] = inference_data["face"].astype(int)
    inference_data = inference_data[inference_data["face"].isin(FACE_TRUE_RAW)]

    for row in inference_data.itertuples(index=False):
        true_ability, true_warmth = FACE_TRUE_RAW[int(row.face)]
        rows.append(
            {
                "SubNo": int(row.SubNo),
                "date": row.date,
                "source": row.source,
                "session_index": int(row.session_index),
                "face": int(row.face),
                "axis": "left",
                "true_bar_px": float(row.true_leftBar),
                "face_value_0_to_10": true_ability,
                "face_value_ratio": true_ability / 10.0,
                "square_side_estimate": float(row.true_leftBar) / (true_ability / 10.0),
            }
        )
        rows.append(
            {
                "SubNo": int(row.SubNo),
                "date": row.date,
                "source": row.source,
                "session_index": int(row.session_index),
                "face": int(row.face),
                "axis": "right",
                "true_bar_px": float(row.true_rightBar),
                "face_value_0_to_10": true_warmth,
                "face_value_ratio": true_warmth / 10.0,
                "square_side_estimate": float(row.true_rightBar) / (true_warmth / 10.0),
            }
        )
    return pd.DataFrame(rows)


def summarize_square_side(
    test_trials: pd.DataFrame,
    estimates: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    inference_data = test_trials.dropna(subset=["SubNo", "date", "face", "true_leftBar", "true_rightBar"]).copy()
    inference_data["face"] = inference_data["face"].astype(int)
    inference_data = inference_data[inference_data["face"].isin(FACE_TRUE_RAW)]

    for keys, group in inference_data.groupby(group_columns, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_data = dict(zip(group_columns, keys))
        estimate_mask = np.ones(len(estimates), dtype=bool)
        for column, value in key_data.items():
            estimate_mask &= estimates[column].to_numpy() == value
        group_estimates = estimates.loc[estimate_mask, "square_side_estimate"].dropna()
        best_side, rmse_px, max_abs_error_px = infer_square_side_from_face_truth(
            group,
            face_col="face",
            x_col="true_leftBar",
            y_col="true_rightBar",
        )
        unique_faces = sorted(group["face"].dropna().astype(int).unique().tolist())
        rows.append(
            {
                **key_data,
                "n_files": int(group["source"].nunique()) if "source" in group.columns else np.nan,
                "n_trials": int(len(group)),
                "n_faces": int(len(unique_faces)),
                "faces_observed": " ".join(map(str, unique_faces)),
                "square_side_median": float(group_estimates.median()) if len(group_estimates) else np.nan,
                "square_side_mean": float(group_estimates.mean()) if len(group_estimates) else np.nan,
                "square_side_sd": float(group_estimates.std(ddof=1)) if len(group_estimates) > 1 else 0.0,
                "square_side_min": float(group_estimates.min()) if len(group_estimates) else np.nan,
                "square_side_max": float(group_estimates.max()) if len(group_estimates) else np.nan,
                "square_side_px": best_side,
                "square_side_rmse_px": rmse_px,
                "square_side_max_abs_error_px": max_abs_error_px,
            }
        )
    return pd.DataFrame(rows).sort_values(group_columns).reset_index(drop=True)


def attach_day_index(
    learning_sessions: pd.DataFrame,
    coordinates: pd.DataFrame,
    test_trials: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_days = pd.concat(
        [
            learning_sessions[["SubNo", "date"]],
            test_trials[["SubNo", "date"]],
        ],
        ignore_index=True,
    ).drop_duplicates()
    all_days = all_days.sort_values(["SubNo", "date"]).reset_index(drop=True)
    all_days["day_index"] = all_days.groupby("SubNo").cumcount() + 1

    learning_sessions = learning_sessions.merge(all_days, on=["SubNo", "date"], how="left")
    coordinates = coordinates.merge(all_days, on=["SubNo", "date"], how="left")
    test_trials = test_trials.merge(all_days, on=["SubNo", "date"], how="left")

    learning_sessions = learning_sessions.sort_values(["SubNo", "date", "session_index"]).reset_index(drop=True)
    learning_sessions["session_order"] = learning_sessions.groupby(["SubNo", "date"]).cumcount() + 1

    coord_order = learning_sessions[["SubNo", "date", "source", "session_order"]].drop_duplicates()
    coordinates = coordinates.merge(coord_order, on=["SubNo", "date", "source"], how="left")
    coordinates = coordinates.sort_values(["SubNo", "date", "session_index", "timestamp_s", "point_order"]).reset_index(drop=True)

    test_sessions = (
        test_trials[["SubNo", "date", "source", "session_index"]]
        .drop_duplicates()
        .sort_values(["SubNo", "date", "session_index", "source"])
    )
    test_sessions["test_session_order"] = test_sessions.groupby(["SubNo", "date"]).cumcount() + 1
    test_trials = test_trials.merge(test_sessions, on=["SubNo", "date", "source", "session_index"], how="left")
    test_trials = test_trials.sort_values(["SubNo", "date", "session_index", "source"]).reset_index(drop=True)
    return learning_sessions, coordinates, test_trials


def attach_square_side(
    learning_sessions: pd.DataFrame,
    coordinates: pd.DataFrame,
    test_trials: pd.DataFrame,
    subject_date_square_side: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scale_map = subject_date_square_side[["SubNo", "date", "square_side_px", "square_side_rmse_px", "square_side_max_abs_error_px"]]
    learning_sessions = learning_sessions.merge(scale_map, on=["SubNo", "date"], how="left")
    coordinates = coordinates.merge(scale_map, on=["SubNo", "date"], how="left")
    test_trials = test_trials.merge(scale_map, on=["SubNo", "date"], how="left")

    missing_scale = coordinates.loc[coordinates["square_side_px"].isna(), ["SubNo", "date"]].drop_duplicates()
    if not missing_scale.empty:
        raise ValueError(f"Missing EP squareSidePx estimates for learning coordinates:\n{missing_scale.to_string(index=False)}")

    coordinates["ability"] = pixels_to_true_space(coordinates["leftBar_px"], coordinates["square_side_px"])
    coordinates["warmth"] = pixels_to_true_space(coordinates["rightBar_px"], coordinates["square_side_px"])
    coordinates["out_of_bounds_0_to_10"] = ~(
        coordinates["ability"].between(0, 10) & coordinates["warmth"].between(0, 10)
    )
    return learning_sessions, coordinates, test_trials


def build_daily_summary(
    learning_sessions: pd.DataFrame,
    test_trials: pd.DataFrame,
    coordinates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    learning_session_summary = learning_sessions.sort_values(["SubNo", "date", "session_order"]).copy()
    test_session_summary = (
        test_trials.groupby(["SubNo", "date", "day_index", "source", "session_index", "test_session_order"], as_index=False)
        .agg(
            n_trials=("SubNo", "size"),
            mean_accuracy=("acc", "mean"),
            mean_rt=("rt", "mean"),
        )
        .sort_values(["SubNo", "date", "test_session_order"])
    )

    learning_day = (
        learning_sessions.groupby(["SubNo", "date", "day_index"], as_index=False)
        .agg(
            n_learning_sessions=("source", "nunique"),
            learning_time_s=("total_learning_time_s", "sum"),
            return_to_learn_count=("return_to_learn_count", "sum"),
            n_coordinate_points=("total_points", "sum"),
            square_side_px=("square_side_px", "first"),
            square_side_rmse_px=("square_side_rmse_px", "first"),
            square_side_max_abs_error_px=("square_side_max_abs_error_px", "first"),
        )
        .sort_values(["SubNo", "day_index"])
    )
    actual_coordinate_counts = (
        coordinates.groupby(["SubNo", "date", "day_index"], as_index=False)
        .agg(n_loaded_coordinate_points=("ability", "size"), n_out_of_bounds_points=("out_of_bounds_0_to_10", "sum"))
    )
    learning_day = learning_day.merge(actual_coordinate_counts, on=["SubNo", "date", "day_index"], how="left")

    test_day = (
        test_trials.groupby(["SubNo", "date", "day_index"], as_index=False)
        .agg(
            n_test_sessions=("source", "nunique"),
            raw_trial_count=("SubNo", "size"),
            mean_accuracy=("acc", "mean"),
            mean_rt=("rt", "mean"),
            square_side_px=("square_side_px", "first"),
        )
        .sort_values(["SubNo", "day_index"])
    )
    test_day["trial_count"] = test_day["raw_trial_count"].astype(float)
    test_day.loc[test_day["day_index"] == 3, "trial_count"] = (
        test_day.loc[test_day["day_index"] == 3, "trial_count"] / 3.0
    )

    day_summary = pd.merge(
        learning_day,
        test_day,
        on=["SubNo", "date", "day_index"],
        how="outer",
        suffixes=("", "_test"),
    ).sort_values(["SubNo", "day_index"])
    day_summary["square_side_px"] = day_summary["square_side_px"].combine_first(day_summary.get("square_side_px_test"))
    if "square_side_px_test" in day_summary.columns:
        day_summary = day_summary.drop(columns=["square_side_px_test"])

    count_columns = [
        "n_learning_sessions",
        "return_to_learn_count",
        "n_coordinate_points",
        "n_loaded_coordinate_points",
        "n_out_of_bounds_points",
        "n_test_sessions",
        "raw_trial_count",
    ]
    for column in count_columns:
        day_summary[column] = day_summary[column].fillna(0).astype(int)
    day_summary["trial_count"] = pd.to_numeric(day_summary["trial_count"], errors="coerce")
    day_summary["day_index"] = day_summary["day_index"].astype(int)
    day_summary["SubNo"] = day_summary["SubNo"].astype(int)
    return learning_session_summary, test_session_summary, learning_day, day_summary.reset_index(drop=True)


def build_group_day_summary(day_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for measure in ["learning_time_s", "trial_count"]:
        summary = (
            day_summary.dropna(subset=[measure])
            .groupby("day_index")[measure]
            .agg(n_subjects="count", mean="mean", median="median", sd="std")
            .reset_index()
        )
        summary["se"] = summary["sd"] / np.sqrt(summary["n_subjects"])
        summary["measure"] = measure
        rows.append(summary)
    return pd.concat(rows, ignore_index=True).sort_values(["measure", "day_index"])


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
    wide = (
        day_summary.loc[day_summary["day_index"].isin(DAY_ORDER), ["SubNo", "day_index", measure]]
        .pivot(index="SubNo", columns="day_index", values=measure)
        .reindex(columns=DAY_ORDER)
        .dropna()
        .astype(float)
    )
    if wide.empty:
        return MeasureStats(
            measure=measure,
            complete_n=0,
            omnibus_method="not enough complete cases",
            omnibus_statistic=np.nan,
            omnibus_p_value=np.nan,
            pairwise=pd.DataFrame(),
        )

    pairwise_rows = []
    normality_p_values = []
    for day_a, day_b in combinations(DAY_ORDER, 2):
        diff = wide[day_a] - wide[day_b]
        normality_p_values.append(stats.shapiro(diff).pvalue if len(diff) >= 3 else np.nan)
        pairwise_rows.append(paired_test_report(wide[day_a], wide[day_b], f"day{day_a}", f"day{day_b}"))
    pairwise_df = pd.DataFrame(pairwise_rows)

    valid_normality = [p_value for p_value in normality_p_values if not np.isnan(p_value)]
    if valid_normality and all(p_value >= 0.05 for p_value in valid_normality):
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
    if pd.isna(p_value):
        return "NA"
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "ns"


def format_trial_count(value: float) -> str:
    rounded_value = round(value)
    if np.isclose(value, rounded_value):
        return f"{int(rounded_value)}"
    return f"{value:.1f}"


def add_significance_annotations(ax: plt.Axes, pairwise_df: pd.DataFrame, y_max: float) -> None:
    if pairwise_df.empty:
        return
    height = max(y_max * 0.06, 1.0)
    start = y_max * 1.04 if y_max > 0 else 1.0
    ordered_pairwise = pairwise_df.assign(comparison_span=pairwise_df["day_b"] - pairwise_df["day_a"]).sort_values(
        ["comparison_span", "day_a", "day_b"]
    )
    y_levels = []
    for row in ordered_pairwise.itertuples(index=False):
        x1 = row.day_a - 1
        x2 = row.day_b - 1
        comparison_span = row.day_b - row.day_a
        x_padding = 0.11 if comparison_span == 1 else 0.0
        x1_plot = x1 + x_padding
        x2_plot = x2 - x_padding
        y_level = max(int(comparison_span) - 1, 0)
        y_levels.append(y_level)
        y = start + y_level * height
        ax.plot(
            [x1_plot, x1_plot, x2_plot, x2_plot],
            [y, y + height * 0.25, y + height * 0.25, y],
            color="#1F2933",
            linewidth=0.9,
        )
        ax.text((x1 + x2) / 2, y + height * 0.28, p_value_to_stars(row.p_value), ha="center", va="bottom", fontsize=9)
    top_needed = start + (max(y_levels, default=0) + 1) * height
    ax.set_ylim(top=max(ax.get_ylim()[1], top_needed))


def render_heatmap(points: pd.DataFrame, bins: int = 100, sigma: float = 1.6) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    x = points["ability"].to_numpy(dtype=float)
    y = points["warmth"].to_numpy(dtype=float)
    heatmap, x_edges, y_edges = np.histogram2d(x, y, bins=bins, range=[[0, 10], [0, 10]])
    heatmap = gaussian_filter(heatmap.T, sigma=sigma)
    return heatmap, (x_edges[0], x_edges[-1], y_edges[0], y_edges[-1])


def draw_density_heatmap(
    ax: plt.Axes,
    heatmap: np.ndarray,
    extent: tuple[float, float, float, float],
    *,
    alpha: float = 1.0,
) -> plt.AxesImage:
    heatmap = np.nan_to_num(heatmap, nan=0.0, posinf=0.0, neginf=0.0)
    max_density = float(np.max(heatmap)) if heatmap.size else 0.0
    norm: mcolors.Normalize
    if max_density > 0:
        norm = mcolors.PowerNorm(gamma=HEATMAP_LOW_DENSITY_GAMMA, vmin=0.0, vmax=max_density)
    else:
        norm = mcolors.Normalize(vmin=0.0, vmax=1.0)
    cmap = plt.get_cmap("magma").copy()
    cmap.set_bad("#000000")
    cmap.set_under("#000000")
    return ax.imshow(heatmap, extent=extent, origin="lower", cmap=cmap, norm=norm, alpha=alpha, aspect="equal")


def plot_subject_trajectory(points: pd.DataFrame, meta: pd.Series, language: str, output_dir: Path) -> None:
    configure_ep_style()
    fig, ax = plt.subplots(figsize=(5.6, 5.2))
    setup_true_space_axis(ax, labels=language)
    add_true_face_points_0_to_10(ax, labels=language)

    n_sessions = max(int(meta["n_learning_sessions"]), 1)
    session_palette = sns.color_palette("blend:#4C78A8,#B279A2", n_colors=max(n_sessions, 2))
    for session_order, session_points in points.groupby("session_order", sort=True):
        color = session_palette[int(session_order) - 1]
        ax.plot(
            session_points["ability"],
            session_points["warmth"],
            color=color,
            linewidth=1.0,
            alpha=0.72,
            label=TEXT[language]["session"].format(idx=int(session_order)),
            zorder=2,
        )
        first_point = session_points.iloc[0]
        last_point = session_points.iloc[-1]
        ax.scatter(first_point["ability"], first_point["warmth"], s=18, color=color, marker="o", zorder=3)
        ax.scatter(last_point["ability"], last_point["warmth"], s=22, color=color, marker="s", zorder=3)

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
            labels["points"].format(count=int(meta["n_loaded_coordinate_points"])),
            labels["square_side"].format(value=int(meta["square_side_px"])),
            f"{labels['learn_time']}: {float(meta['learning_time_s']):.1f}",
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
    setup_true_space_axis(ax, labels=language)
    heatmap, extent = render_heatmap(points, bins=96, sigma=1.8)
    image = draw_density_heatmap(ax, heatmap, extent, alpha=1.0)
    add_true_face_points_0_to_10(ax, labels=language)
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
            labels["points"].format(count=int(meta["n_loaded_coordinate_points"])),
            labels["square_side"].format(value=int(meta["square_side_px"])),
            f"{labels['learn_time']}: {float(meta['learning_time_s']):.1f}",
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
    max_day = max(DAY_ORDER + day_rows["day_index"].dropna().astype(int).tolist())
    ordered_days = list(range(1, max_day + 1))
    ordered = (
        pd.DataFrame({"day_index": ordered_days})
        .merge(day_rows.sort_values("day_index"), on="day_index", how="left")
        .assign(SubNo=lambda df: df["SubNo"].ffill().bfill())
    )
    x_positions = np.arange(len(ordered))
    missing_mask = ordered[measure].isna()
    colors = [
        DAY_COLORS.get(int(day_index), TASK_PALETTE["gray"]) if not is_missing else "#E5E7EB"
        for day_index, is_missing in zip(ordered["day_index"], missing_mask)
    ]
    values = ordered[measure].fillna(0).to_numpy(dtype=float)
    bars = ax.bar(x_positions, values, color=colors, edgecolor=BAR_EDGE_COLOR, linewidth=BAR_LINEWIDTH, width=BAR_WIDTH)

    for bar, value, is_missing in zip(bars, values, missing_mask):
        if is_missing:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                max(values.max() * 0.02, 0.6),
                labels["missing"],
                ha="center",
                va="bottom",
                fontsize=8,
                color="#6B7280",
            )
            bar.set_hatch("//")
            continue
        label = f"{value:.1f}" if measure == "learning_time_s" else format_trial_count(value)
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


def plot_group_heatmap(points: pd.DataFrame, language: str, output_dir: Path, day_index: int | None = None) -> None:
    configure_ep_style()
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    setup_true_space_axis(ax, labels=language)
    heatmap, extent = render_heatmap(points, bins=110, sigma=2.1)
    image = draw_density_heatmap(ax, heatmap, extent, alpha=1.0)
    add_true_face_points_0_to_10(ax, labels=language)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(TEXT[language]["density"])

    labels = TEXT[language]
    day_label = labels["all_days"] if day_index is None else labels["day"].format(day=day_index)
    ax.set_title(f"{labels['group_heatmap_title']}\n{day_label}", fontsize=11)
    ax.text(
        0.02,
        0.98,
        f"{labels['group_n']}: {points['SubNo'].nunique()}\n{labels['points'].format(count=len(points))}",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "#D1D5DB"},
    )
    stem = f"group_day-{day_index}_heatmap_{language}" if day_index is not None else f"group_all-days_heatmap_{language}"
    save_figure(fig, output_dir, stem)


def plot_group_measure(day_summary: pd.DataFrame, stats_result: MeasureStats, measure: str, language: str, output_dir: Path) -> None:
    configure_ep_style()
    labels = TEXT[language]
    title_label = labels["learning_time_title"] if measure == "learning_time_s" else labels["trial_count_title"]
    value_label = labels["learn_time"] if measure == "learning_time_s" else labels["trial_count"]

    figure_data = day_summary.loc[day_summary["day_index"].isin(DAY_ORDER)].dropna(subset=[measure]).copy()
    figure_data[measure] = pd.to_numeric(figure_data[measure], errors="coerce")
    summary = (
        figure_data.groupby("day_index")[measure]
        .agg(n_subjects="count", mean="mean", sd="std")
        .reindex(DAY_ORDER)
        .reset_index()
    )
    summary["se"] = summary["sd"] / np.sqrt(summary["n_subjects"])
    tick_labels = [
        f"{labels['day_short'].format(day=int(day_index))}\n(n={0 if pd.isna(n_subjects) else int(n_subjects)})"
        for day_index, n_subjects in zip(summary["day_index"], summary["n_subjects"])
    ]

    fig, ax = plt.subplots(figsize=(6.3, 4.5))
    x_positions = np.arange(len(DAY_ORDER))
    ax.bar(
        x_positions,
        summary["mean"].fillna(0).to_numpy(dtype=float),
        yerr=summary["se"].fillna(0).to_numpy(dtype=float),
        color=[DAY_COLORS[day_index] for day_index in DAY_ORDER],
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_LINEWIDTH,
        width=BAR_WIDTH,
        error_kw=bar_error_kw(),
        zorder=2,
    )
    rng = np.random.default_rng(20260418)
    for x_position, day_index in enumerate(DAY_ORDER):
        values = figure_data.loc[figure_data["day_index"] == day_index, measure].dropna().to_numpy(dtype=float)
        if len(values) == 0:
            continue
        ax.scatter(
            jittered_x(x_position, len(values), rng),
            values,
            **bar_scatter_kw(),
            zorder=3,
        )

    y_candidates = pd.concat([summary["mean"] + summary["se"], figure_data[measure]], ignore_index=True).dropna()
    y_max = float(y_candidates.max()) if not y_candidates.empty else 1.0
    add_significance_annotations(ax, stats_result.pairwise, y_max)
    ax.set_xlabel(labels["day_axis"])
    ax.set_ylabel(value_label)
    ax.set_xticks(x_positions, labels=tick_labels)
    ax.set_title(title_label, fontsize=11)
    legend = ax.get_legend()
    if legend is not None:
        legend.remove()
    sns.despine(ax=ax)

    stem = "group_learning_time_" + language if measure == "learning_time_s" else "group_test_trials_" + language
    save_figure(fig, output_dir, stem)


def export_tables(
    selected_test_files: pd.DataFrame,
    trial_axis_estimates: pd.DataFrame,
    file_square_side: pd.DataFrame,
    subject_date_square_side: pd.DataFrame,
    learning_session_summary: pd.DataFrame,
    test_session_summary: pd.DataFrame,
    learning_day: pd.DataFrame,
    day_summary: pd.DataFrame,
    group_day_summary: pd.DataFrame,
    coordinates: pd.DataFrame,
    test_trials: pd.DataFrame,
    stats_results: dict[str, MeasureStats],
) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    selected_test_files.to_csv(TABLES_DIR / "selected_test_files.csv", index=False)
    trial_axis_estimates.to_csv(TABLES_DIR / "trial_axis_square_side_estimates.csv", index=False)
    file_square_side.to_csv(TABLES_DIR / "file_square_side_summary.csv", index=False)
    subject_date_square_side.to_csv(TABLES_DIR / "subject_date_square_side_summary.csv", index=False)
    learning_session_summary.to_csv(TABLES_DIR / "learning_session_summary.csv", index=False)
    test_session_summary.to_csv(TABLES_DIR / "test_session_summary.csv", index=False)
    learning_day.to_csv(TABLES_DIR / "learning_day_summary.csv", index=False)
    day_summary.to_csv(TABLES_DIR / "subject_day_summary.csv", index=False)
    group_day_summary.to_csv(TABLES_DIR / "group_day_summary.csv", index=False)
    coordinates.to_csv(TABLES_DIR / "learning_coordinates_0_to_10.csv", index=False)
    test_trials.to_csv(TABLES_DIR / "test_trials_integrated.csv", index=False)

    pairwise_frames = []
    for measure, result in stats_results.items():
        pairwise = result.pairwise.copy()
        if pairwise.empty:
            continue
        pairwise["measure"] = measure
        pairwise["omnibus_method"] = result.omnibus_method
        pairwise["omnibus_statistic"] = result.omnibus_statistic
        pairwise["omnibus_p_value"] = result.omnibus_p_value
        pairwise["complete_n"] = result.complete_n
        pairwise_frames.append(pairwise)
    if pairwise_frames:
        pd.concat(pairwise_frames, ignore_index=True).to_csv(TABLES_DIR / "pairwise_stats.csv", index=False)


def generate_subject_figures(coordinates: pd.DataFrame, day_summary: pd.DataFrame) -> None:
    for sub_no, subject_days in day_summary.groupby("SubNo", sort=True):
        subject_days = subject_days.sort_values("day_index")
        subject_dir = SUBJECT_FIGURES_DIR / f"sub-{int(sub_no):02d}"
        subject_dir.mkdir(parents=True, exist_ok=True)
        for language in LANGUAGES:
            plot_subject_measure(subject_days, "learning_time_s", language, subject_dir)
            plot_subject_measure(subject_days, "trial_count", language, subject_dir)

        for meta in subject_days.itertuples(index=False):
            if pd.isna(meta.learning_time_s):
                continue
            day_points = coordinates.loc[(coordinates["SubNo"] == meta.SubNo) & (coordinates["day_index"] == meta.day_index)].copy()
            if day_points.empty:
                continue
            for language in LANGUAGES:
                plot_subject_trajectory(day_points, pd.Series(meta._asdict()), language, subject_dir)
                plot_subject_heatmap(day_points, pd.Series(meta._asdict()), language, subject_dir)


def generate_group_figures(coordinates: pd.DataFrame, day_summary: pd.DataFrame, stats_results: dict[str, MeasureStats]) -> None:
    GROUP_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for language in LANGUAGES:
        plot_group_heatmap(coordinates, language, GROUP_FIGURES_DIR)
    for day_index in DAY_ORDER:
        day_points = coordinates.loc[coordinates["day_index"] == day_index]
        if day_points.empty:
            continue
        for language in LANGUAGES:
            plot_group_heatmap(day_points, language, GROUP_FIGURES_DIR, day_index=day_index)

    for measure in ["learning_time_s", "trial_count"]:
        for language in LANGUAGES:
            plot_group_measure(day_summary, stats_results[measure], measure, language, GROUP_FIGURES_DIR)


def write_stats_report(
    day_summary: pd.DataFrame,
    subject_date_square_side: pd.DataFrame,
    stats_results: dict[str, MeasureStats],
    output_path: Path,
) -> None:
    included_subjects = sorted(day_summary["SubNo"].unique().tolist())
    mr_subjects = list(completed_all_task_subject_ids())
    excluded_after_mr = [sub_no for sub_no in mr_subjects if sub_no not in included_subjects]
    square_counts = subject_date_square_side["square_side_px"].value_counts().sort_index()
    lines = [
        "proc1 EP task learning/test analysis",
        "====================================",
        "",
        "Data integration rules",
        "- proc1 is interpreted as the explore / EP task.",
        "- Test files are deduplicated only across formats with the same stem; same-day `-1`, `-2`, ... files are appended.",
        "- Day 3 `trial_count` is divided by 3 because participants repeat the EP task three times on that day.",
        "- `squareSidePx` is inferred per SubNo × date from EP test `true_leftBar` / `true_rightBar` and canonical `FACE_TRUE_RAW`.",
        "- Learning `CoordinateData.leftBar/rightBar` pixels are converted with that SubNo × date `squareSidePx` into the shared 0-10 space.",
        f"- EP analyses use shared completed-subject filters; MR-complete reference subjects: {mr_subjects}.",
        "",
        f"Participants included: {len(included_subjects)}",
        f"Included SubNo values: {included_subjects}",
        f"MR-complete subjects with no EP rows after filtering: {excluded_after_mr if excluded_after_mr else 'None'}",
        "",
        "Subject-date counts by inferred squareSidePx:",
    ]
    for square_side, count in square_counts.items():
        lines.append(f"- {int(square_side)} px: {int(count)} subject-date rows")

    high_error = subject_date_square_side.loc[subject_date_square_side["square_side_max_abs_error_px"] > 1]
    lines.extend(["", "Scale inference quality:"])
    if high_error.empty:
        lines.append("- All subject-date integer squareSidePx estimates reproduce recorded targets within 1 px.")
    else:
        lines.append(high_error[["SubNo", "date", "square_side_px", "square_side_max_abs_error_px"]].to_string(index=False))
    lines.append("")

    for measure in ["learning_time_s", "trial_count"]:
        title = "Explore time (s)" if measure == "learning_time_s" else "Test trials"
        lines.extend([title, "-" * len(title)])
        descriptive = (
            day_summary.dropna(subset=[measure])
            .groupby("day_index")[measure]
            .agg(n="count", mean="mean", median="median", sd="std")
            .reindex(DAY_ORDER)
        )
        descriptive["se"] = descriptive["sd"] / np.sqrt(descriptive["n"])
        lines.append(descriptive.round(4).to_string())
        lines.append("")

        result = stats_results[measure]
        lines.append(
            f"Omnibus: {result.omnibus_method}, n = {result.complete_n}, "
            f"statistic = {result.omnibus_statistic:.4f}, p = {result.omnibus_p_value:.6g}"
        )
        lines.append("Pairwise comparisons:")
        if result.pairwise.empty:
            lines.append("  None")
        else:
            for row in result.pairwise.sort_values(["day_a", "day_b"]).itertuples(index=False):
                lines.append(
                    "  "
                    + f"Day {row.day_a} vs Day {row.day_b}: {row.method}, n = {row.n_subjects}, "
                    + f"mean diff = {row.mean_difference:.4f}, statistic = {row.statistic:.4f}, p = {row.p_value:.6g}, "
                    + f"Shapiro p = {row.normality_shapiro_p:.6g}"
                )
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    reset_proc_output_dir(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading EP learning data")
    learning_sessions, coordinates = load_learning_data()
    LOGGER.info("Loading EP test trials")
    test_trials, selected_test_files = load_test_trials()
    LOGGER.info("Inferring squareSidePx per subject-date from EP test targets")
    trial_axis_estimates = estimate_trial_axes(test_trials)
    file_square_side = summarize_square_side(test_trials, trial_axis_estimates, ["SubNo", "date", "source"])
    subject_date_square_side = summarize_square_side(test_trials, trial_axis_estimates, ["SubNo", "date"])

    learning_sessions, coordinates, test_trials = attach_day_index(learning_sessions, coordinates, test_trials)
    learning_sessions, coordinates, test_trials = attach_square_side(
        learning_sessions,
        coordinates,
        test_trials,
        subject_date_square_side,
    )
    learning_session_summary, test_session_summary, learning_day, day_summary = build_daily_summary(
        learning_sessions,
        test_trials,
        coordinates,
    )
    group_day_summary = build_group_day_summary(day_summary)
    stats_results = {
        "learning_time_s": compute_measure_stats(day_summary, "learning_time_s"),
        "trial_count": compute_measure_stats(day_summary, "trial_count"),
    }

    LOGGER.info("Exporting tables")
    export_tables(
        selected_test_files=selected_test_files,
        trial_axis_estimates=trial_axis_estimates,
        file_square_side=file_square_side,
        subject_date_square_side=subject_date_square_side,
        learning_session_summary=learning_session_summary,
        test_session_summary=test_session_summary,
        learning_day=learning_day,
        day_summary=day_summary,
        group_day_summary=group_day_summary,
        coordinates=coordinates,
        test_trials=test_trials,
        stats_results=stats_results,
    )

    LOGGER.info("Rendering subject figures")
    generate_subject_figures(coordinates, day_summary)
    LOGGER.info("Rendering group figures")
    generate_group_figures(coordinates, day_summary, stats_results)
    LOGGER.info("Writing statistics report")
    write_stats_report(day_summary, subject_date_square_side, stats_results, OUTPUT_DIR / "stats_report.txt")
    LOGGER.info("Done. Outputs written to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
