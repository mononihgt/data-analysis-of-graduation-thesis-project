from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".cache"
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io as sio
import seaborn as sns


DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
EXCLUDED_SUBNOS = {1, 15, 17}

FACE_TRUE_400 = {
    1: (97.0, 192.0),
    2: (112.0, 311.0),
    3: (257.0, 341.0),
    4: (353.0, 269.0),
    5: (196.0, 81.0),
    6: (306.0, 127.0),
}
PD_RECORDED_FACE_TRUE_400 = {
    1: (24.0, 248.0),
    2: (184.0, 254.0),
    3: (267.6, 234.0),
    4: (342.0, 375.6),
    5: (208.4, 172.0),
    6: (293.6, 36.4),
}
FACE_TRUE_RAW = {
    1: (2.416, 4.788),
    2: (2.789, 7.765),
    3: (6.426, 8.527),
    4: (8.817, 6.716),
    5: (4.894, 2.020),
    6: (7.659, 3.185),
}
FACE_VILLAGE = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3}
VILLAGE_LABELS = {1: "A", 2: "B", 3: "C"}
VILLAGE_PAIRS = {
    "AB": (1, 2),
    "AC": (1, 3),
    "BC": (2, 3),
}

TASK_PALETTE = {
    "blue": "#4C78A8",
    "orange": "#F58518",
    "green": "#54A24B",
    "red": "#E45756",
    "purple": "#B279A2",
    "brown": "#9D755D",
    "gray": "#6B7280",
    "cyan": "#72B7B2",
}
FACE_PALETTE = {
    1: "#4C78A8",
    2: "#72B7B2",
    3: "#54A24B",
    4: "#F58518",
    5: "#E45756",
    6: "#B279A2",
}
CONDITION_PALETTE = {
    "same": "#54A24B",
    "near": "#4C78A8",
    "far": "#E45756",
    "unknown": "#F58518",
}


def configure_plot_style(context: str = "paper") -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(
        style="whitegrid",
        context=context,
        font="Arial",
        rc={
            "axes.edgecolor": "#2F3437",
            "axes.linewidth": 0.9,
            "axes.labelcolor": "#1F2933",
            "axes.titlecolor": "#1F2933",
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "grid.color": "#E5E7EB",
            "grid.linewidth": 0.7,
            "legend.frameon": False,
            "patch.edgecolor": "#2F3437",
            "patch.linewidth": 0.9,
            "xtick.color": "#1F2933",
            "ytick.color": "#1F2933",
        },
    )


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{stem}.png", bbox_inches="tight")
    # fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def add_true_face_points(
    ax: plt.Axes,
    *,
    labels: str = "en",
    size: float = 52,
    marker: str = "X",
    zorder: int = 5,
) -> None:
    for face, (x_coord, y_coord) in FACE_TRUE_400.items():
        ax.scatter(
            x_coord,
            y_coord,
            s=size,
            marker=marker,
            color=FACE_PALETTE[face],
            edgecolor="#1F2933",
            linewidth=0.8,
            zorder=zorder,
        )
        prefix = "面孔" if labels == "zh" else "F"
        ax.text(x_coord + 6, y_coord + 6, f"{prefix}{face}", fontsize=8, zorder=zorder + 1)


def setup_square_axis(ax: plt.Axes, *, labels: str = "en") -> None:
    ax.set_xlim(0, 400)
    ax.set_ylim(0, 400)
    ax.set_aspect("equal", adjustable="box")
    if labels == "zh":
        ax.set_xlabel("能力值")
        ax.set_ylabel("温暖值")
    else:
        ax.set_xlabel("Ability")
        ax.set_ylabel("Warmth")
    sns.despine(ax=ax)


def infer_subno_from_path(path: Path) -> int | None:
    match = re.search(r"-(\d+)-\d{4}-\d{2}-\d{2}", path.name)
    return int(match.group(1)) if match else None


def infer_date_from_path(path: Path) -> str | None:
    match = re.search(r"-(\d{4}-\d{2}-\d{2})(?:-\d+)?\.", path.name)
    return match.group(1) if match else None


def mat_ret_to_df(path: Path) -> pd.DataFrame:
    arr = sio.loadmat(path, squeeze_me=True, struct_as_record=False)["ret"]
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    cols = list(arr[0, :])
    data = arr[1:, :]
    df = pd.DataFrame(data, columns=cols)
    return df.map(lambda x: np.nan if isinstance(x, np.ndarray) and x.size == 0 else x)


def read_table_file(path: Path) -> pd.DataFrame:
    if path.suffix == ".mat":
        df = mat_ret_to_df(path)
    elif path.suffix == ".xlsx":
        df = pd.read_excel(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"Unsupported table file: {path}")
    df["source"] = path.name
    return df


def load_task_tables(data_dir: Path, prefix: str, *, prefer: Iterable[str] = (".mat", ".xlsx", ".csv")) -> pd.DataFrame:
    files = [path for path in data_dir.iterdir() if path.is_file() and path.name.startswith(prefix)]
    by_stem: dict[str, list[Path]] = {}
    for path in files:
        by_stem.setdefault(path.stem, []).append(path)

    priority = {suffix: index for index, suffix in enumerate(prefer)}
    selected = []
    for paths in by_stem.values():
        selected.append(sorted(paths, key=lambda path: priority.get(path.suffix, 99))[0])

    frames = [read_table_file(path) for path in sorted(selected)]
    if not frames:
        raise FileNotFoundError(f"No files matching {prefix} in {data_dir}")
    return pd.concat(frames, ignore_index=True)


def coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def filter_excluded_subjects(df: pd.DataFrame, sub_col: str = "SubNo") -> pd.DataFrame:
    if sub_col not in df.columns:
        return df
    numeric_sub = pd.to_numeric(df[sub_col], errors="coerce")
    return df.loc[~numeric_sub.isin(EXCLUDED_SUBNOS)].copy()


@lru_cache(maxsize=1)
def mr_completed_subject_ids() -> tuple[int, ...]:
    mr_data_dir = DATA_DIR / "MRtask_data"
    mr = load_task_tables(mr_data_dir, "MRtask")
    if "SubNo" not in mr.columns:
        return tuple()
    mr["SubNo"] = pd.to_numeric(mr["SubNo"], errors="coerce")
    mr = mr.dropna(subset=["SubNo"]).copy()
    mr["SubNo"] = mr["SubNo"].astype(int)
    mr = filter_excluded_subjects(mr)
    return tuple(sorted(mr["SubNo"].unique().tolist()))


def completed_all_task_subject_ids() -> tuple[int, ...]:
    return mr_completed_subject_ids()


def filter_mr_completed_subjects(df: pd.DataFrame, sub_col: str = "SubNo") -> pd.DataFrame:
    if sub_col not in df.columns:
        return df
    included = set(mr_completed_subject_ids())
    numeric_sub = pd.to_numeric(df[sub_col], errors="coerce")
    return df.loc[numeric_sub.isin(included)].copy()


def filter_completed_subjects(df: pd.DataFrame, sub_col: str = "SubNo") -> pd.DataFrame:
    return filter_mr_completed_subjects(df, sub_col=sub_col)


def raw_pair_condition(village_a: int, village_b: int) -> str:
    villages = frozenset((int(village_a), int(village_b)))
    if len(villages) == 1:
        return "same"
    for label, pair in VILLAGE_PAIRS.items():
        if villages == frozenset(pair):
            return label
    return "unknown"


def recode_distance_condition(sub_no: int, raw_condition: str) -> str:
    if raw_condition == "same":
        return "same"
    if raw_condition == "BC":
        return "unknown"
    if int(sub_no) % 2 == 0:
        return {"AC": "near", "AB": "far"}.get(raw_condition, "unknown")
    return {"AB": "near", "AC": "far"}.get(raw_condition, "unknown")


def paired_test_report(values_a: pd.Series, values_b: pd.Series, label_a: str, label_b: str) -> dict[str, float | str | int]:
    from scipy import stats

    paired = pd.concat([values_a.rename(label_a), values_b.rename(label_b)], axis=1).dropna()
    diff = paired[label_a] - paired[label_b]
    normal = stats.shapiro(diff) if len(diff) >= 3 else None
    if normal is not None and normal.pvalue >= 0.05:
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
        "comparison": f"{label_a} - {label_b}",
        "n_subjects": int(len(paired)),
        "method": method,
        "mean_difference": float(diff.mean()),
        "sd_difference": float(diff.std(ddof=1)),
        "normality_shapiro_p": float(normal.pvalue) if normal is not None else np.nan,
        "statistic": statistic,
        "p_value": p_value,
    }
