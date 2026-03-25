from __future__ import annotations

import logging
import os
import warnings
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
import statsmodels.formula.api as smf


DATA_DIR = ROOT / "data" / "PDtask_data"
OUTPUT_DIR = ROOT / "results" / "pdtask_d_error_analysis"
LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def mat_to_df(path: Path) -> pd.DataFrame:
    arr = sio.loadmat(path, squeeze_me=True, struct_as_record=False)["ret"]
    cols = list(arr[0, :])
    data = arr[1:, :]
    df = pd.DataFrame(data, columns=cols)
    return df.map(lambda x: np.nan if isinstance(x, np.ndarray) and x.size == 0 else x)


def load_raw_data(data_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    mat_files = sorted(data_dir.glob("*.mat"))

    if mat_files:
        for path in mat_files:
            df = mat_to_df(path)
            df["source"] = path.name
            frames.append(df)
    else:
        for path in sorted(data_dir.glob("*.xlsx")):
            df = pd.read_excel(path)
            df["source"] = path.name
            frames.append(df)
        for path in sorted(data_dir.glob("*.csv")):
            df = pd.read_csv(path, encoding="gbk")
            df["source"] = path.name
            frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No PDtask files found in {data_dir}")

    raw = pd.concat(frames, ignore_index=True)
    for col in ["SubNo", "F1V", "F2V", "F1X", "F1Y", "F2X", "F2Y", "D", "ans_D"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    missing_d = raw["D"].isna()
    if missing_d.any():
        raw.loc[missing_d, "D"] = np.sqrt(
            (raw.loc[missing_d, "F1X"] - raw.loc[missing_d, "F2X"]) ** 2
            + (raw.loc[missing_d, "F1Y"] - raw.loc[missing_d, "F2Y"]) ** 2
        )

    raw = raw.dropna(subset=["SubNo", "F1V", "F2V", "D", "ans_D"]).copy()
    raw["SubNo"] = raw["SubNo"].astype(int)
    return raw


def classify_condition(row: pd.Series) -> str | None:
    villages = frozenset((int(row["F1V"]), int(row["F2V"])))
    if len(villages) == 1:
        return "same"

    mapping = {
        frozenset((1, 2)): "AB",
        frozenset((1, 3)): "AC",
        frozenset((2, 3)): "BC",
    }
    return mapping.get(villages)


def prepare_analysis_frame(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["condition"] = df.apply(classify_condition, axis=1)
    df = df.dropna(subset=["condition"]).copy()
    df["relationship"] = np.where(df["condition"] == "same", "same", "different")
    df["distance_nested"] = df["condition"].where(df["condition"] != "same")
    df["d_error"] = df["ans_D"] - df["D"]
    return df


def fit_mixedlm(formula: str, data: pd.DataFrame):
    model = smf.mixedlm(formula, data=data, groups=data["SubNo"])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = model.fit(reml=False, method="lbfgs")

    for warning in caught:
        if "singular" in str(warning.message).lower():
            LOGGER.warning("MixedLM reported a singular random-effects covariance for %s", formula)
        else:
            warnings.warn_explicit(
                message=warning.message,
                category=warning.category,
                filename=warning.filename,
                lineno=warning.lineno,
            )
    return result


def save_descriptive_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    subject_condition = (
        df.groupby(["SubNo", "condition"], as_index=False)["d_error"].mean().sort_values(["SubNo", "condition"])
    )
    subject_condition.to_csv(output_dir / "subject_condition_means.csv", index=False)

    summary = (
        df.groupby("condition")["d_error"]
        .agg(n_trials="size", mean="mean", sd="std")
        .assign(se=lambda x: x["sd"] / np.sqrt(x["n_trials"]))
        .reset_index()
    )
    summary.to_csv(output_dir / "condition_summary.csv", index=False)

    sns.set_theme(
        style="whitegrid",
        context="talk",
        rc={"axes.edgecolor": "0.2", "axes.linewidth": 0.8},
    )
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=200)
    order = ["same", "AB", "AC", "BC"]
    palette = ["#486581", "#B44C43", "#D98F39", "#7A8E3A"]
    sns.barplot(
        data=subject_condition,
        x="condition",
        y="d_error",
        order=order,
        estimator="mean",
        errorbar="se",
        hue="condition",
        palette=palette,
        legend=False,
        capsize=0.15,
        edgecolor="0.25",
        linewidth=1.0,
        ax=ax,
    )
    sns.stripplot(
        data=subject_condition,
        x="condition",
        y="d_error",
        order=order,
        color="0.2",
        size=4,
        alpha=0.75,
        ax=ax,
    )
    ax.set_xlabel("Observed nested condition")
    ax.set_ylabel("d_error (ans_D - D)")
    ax.set_title("PDtask d_error by observed condition")
    sns.despine()
    plt.tight_layout()
    fig.savefig(output_dir / "condition_means.png", bbox_inches="tight")
    plt.close(fig)


def write_model_report(
    strategy1_overall,
    strategy1_within_different,
    strategy2_condition,
    output_dir: Path,
) -> None:
    lines = [
        "PDtask d_error analysis",
        "=======================",
        "",
        "Design note",
        "-----------",
        "Distance and village relationship are partially confounded due to design constraints.",
        "Independent main effects should not be reported.",
        "",
        "Strategy 1A: overall relationship effect",
        "---------------------------------------",
        "Model: d_error ~ relationship + (1 | Subject)",
        str(strategy1_overall.summary()),
        "",
        "Strategy 1B: nested comparison within different-village trials",
        "-------------------------------------------------------------",
        "Model: d_error ~ distance_nested + (1 | Subject)",
        str(strategy1_within_different.summary()),
        "",
        "Strategy 2: single-factor observed condition model",
        "--------------------------------------------------",
        "Model: d_error ~ condition + (1 | Subject)",
        str(strategy2_condition.summary()),
    ]
    (output_dir / "model_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    configure_logging()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw_data(DATA_DIR)
    df = prepare_analysis_frame(raw)
    save_descriptive_outputs(df, OUTPUT_DIR)

    LOGGER.info("Starting PDtask d_error analysis")
    LOGGER.info(
        "Distance and village relationship are partially confounded; applying the documented nested-design strategies"
    )
    LOGGER.info("Observed cell counts:\n%s", df.groupby(["relationship", "condition"]).size().to_string())

    LOGGER.info(
        "Condition means by subject (first 12 rows):\n%s",
        (
            df.groupby(["SubNo", "condition"], as_index=False)["d_error"]
            .mean()
            .sort_values(["SubNo", "condition"])
            .head(12)
            .to_string(index=False)
        ),
    )

    strategy1_overall = fit_mixedlm(
        "d_error ~ C(relationship, Treatment(reference='same'))",
        df,
    )
    LOGGER.info("Completed strategy 1A model: d_error ~ relationship + (1 | Subject)")

    different_only = df[df["relationship"] == "different"].copy()
    strategy1_within_different = fit_mixedlm(
        "d_error ~ C(distance_nested, Treatment(reference='AB'))",
        different_only,
    )
    LOGGER.info("Completed strategy 1B model: d_error ~ distance_nested + (1 | Subject)")

    strategy2_condition = fit_mixedlm(
        "d_error ~ C(condition, Treatment(reference='same'))",
        df,
    )
    LOGGER.info("Completed strategy 2 model: d_error ~ condition + (1 | Subject)")

    contrast_labels = [
        ("same vs AB", "C(condition, Treatment(reference='same'))[T.AB] = 0"),
        ("same vs AC", "C(condition, Treatment(reference='same'))[T.AC] = 0"),
        ("same vs BC", "C(condition, Treatment(reference='same'))[T.BC] = 0"),
        (
            "AB vs AC",
            "C(condition, Treatment(reference='same'))[T.AB] - "
            "C(condition, Treatment(reference='same'))[T.AC] = 0",
        ),
        (
            "AB vs BC",
            "C(condition, Treatment(reference='same'))[T.AB] - "
            "C(condition, Treatment(reference='same'))[T.BC] = 0",
        ),
        (
            "AC vs BC",
            "C(condition, Treatment(reference='same'))[T.AC] - "
            "C(condition, Treatment(reference='same'))[T.BC] = 0",
        ),
    ]
    contrast_text = []
    for label, expression in contrast_labels:
        constraint = strategy2_condition.model.data.design_info.linear_constraint(expression)
        contrast_text.append(label)
        contrast_text.append(str(strategy2_condition.t_test(constraint.coefs)))
        contrast_text.append("")
    LOGGER.info("Completed planned contrasts for strategy 2")

    write_model_report(
        strategy1_overall=strategy1_overall,
        strategy1_within_different=strategy1_within_different,
        strategy2_condition=strategy2_condition,
        output_dir=OUTPUT_DIR,
    )
    LOGGER.info("Saved outputs to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
