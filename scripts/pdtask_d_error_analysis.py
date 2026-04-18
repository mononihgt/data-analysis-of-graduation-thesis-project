from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from analysis_common import (
    CACHE_DIR,
    CONDITION_PALETTE,
    DATA_DIR as RAW_DATA_DIR,
    FACE_TRUE_400,
    PD_RECORDED_FACE_TRUE_400,
    RESULTS_DIR,
    completed_all_task_subject_ids,
    configure_plot_style,
    filter_completed_subjects,
    filter_excluded_subjects,
    load_task_tables,
    paired_test_report,
    raw_pair_condition,
    recode_distance_condition,
    save_figure,
)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from statsmodels.stats.anova import AnovaRM

DATA_DIR = RAW_DATA_DIR / "PDtask_data"
OUTPUT_DIR = RESULTS_DIR / "pdtask_d_error_analysis"
LOGGER = logging.getLogger(__name__)


@dataclass
class TrialModelReport:
    label: str
    formula: str
    re_formula: str
    result: object | None
    notes: list[str]


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_raw_data(data_dir: Path) -> pd.DataFrame:
    raw = load_task_tables(data_dir, "PDtask")
    numeric_columns = [
        "SubNo",
        "F1",
        "F2",
        "F1V",
        "F2V",
        "F1X",
        "F1Y",
        "F2X",
        "F2Y",
        "D",
        "ans_D",
    ]
    for col in numeric_columns:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    missing_d = raw["D"].isna()
    if missing_d.any():
        raw.loc[missing_d, "D"] = np.sqrt(
            (raw.loc[missing_d, "F1X"] - raw.loc[missing_d, "F2X"]) ** 2
            + (raw.loc[missing_d, "F1Y"] - raw.loc[missing_d, "F2Y"]) ** 2
        )

    raw = raw.dropna(subset=["SubNo", "F1", "F2", "F1V", "F2V", "D", "ans_D"]).copy()
    raw["SubNo"] = raw["SubNo"].astype(int)
    raw["F1"] = raw["F1"].astype(int)
    raw["F2"] = raw["F2"].astype(int)
    raw = filter_excluded_subjects(raw)
    return filter_completed_subjects(raw)


def classify_raw_condition(row: pd.Series) -> str | None:
    return raw_pair_condition(int(row["F1V"]), int(row["F2V"]))


def recode_observed_condition(sub_no: int, raw_condition: str) -> str:
    return recode_distance_condition(sub_no, raw_condition)


def face_coordinate_template(subject_df: pd.DataFrame) -> dict[int, tuple[float, float]]:
    coords: dict[int, tuple[float, float]] = {}
    for face in range(1, 7):
        face_coords: list[tuple[float, float]] = []
        for prefix in ["F1", "F2"]:
            face_coords.extend(
                map(
                    tuple,
                    subject_df.loc[
                        subject_df[prefix] == face,
                        [f"{prefix}X", f"{prefix}Y"],
                    ]
                    .dropna()
                    .to_numpy(),
                )
            )
        if not face_coords:
            raise ValueError(f"Missing face coordinates for subject {int(subject_df['SubNo'].iloc[0])}, face {face}")
        coords[face] = tuple(np.median(np.array(face_coords, dtype=float), axis=0))
    return coords


def subject_scale_factor(subject_df: pd.DataFrame) -> float:
    template = face_coordinate_template(subject_df)
    raw_vector = np.array([coord for face in range(1, 7) for coord in template[face]], dtype=float)
    target_vector = np.array(
        [coord for face in range(1, 7) for coord in PD_RECORDED_FACE_TRUE_400[face]],
        dtype=float,
    )
    return float(np.dot(raw_vector, target_vector) / np.dot(raw_vector, raw_vector))


def subject_scale_table(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sub_no, subject_df in raw.groupby("SubNo", sort=True):
        rows.append({"SubNo": int(sub_no), "scale_to_canonical": subject_scale_factor(subject_df)})
    return pd.DataFrame(rows)


def learned_pair_distance(face_a: int, face_b: int) -> float:
    x_a, y_a = FACE_TRUE_400[int(face_a)]
    x_b, y_b = FACE_TRUE_400[int(face_b)]
    return float(np.hypot(x_a - x_b, y_a - y_b))


def prepare_analysis_frame(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.merge(subject_scale_table(raw), on="SubNo", how="left")
    df["raw_condition"] = df.apply(classify_raw_condition, axis=1)
    df = df.dropna(subset=["raw_condition"]).copy()
    df["condition"] = df.apply(
        lambda row: recode_observed_condition(int(row["SubNo"]), row["raw_condition"]),
        axis=1,
    )
    df["relationship"] = np.where(df["condition"] == "same", "same", "different")
    df["distance_nested"] = df["condition"].where(df["condition"] != "same")
    df["recorded_D_norm"] = df["D"] * df["scale_to_canonical"]
    df["ans_D_norm"] = df["ans_D"] * df["scale_to_canonical"]
    df["learned_D"] = [
        learned_pair_distance(face_a, face_b)
        for face_a, face_b in zip(df["F1"], df["F2"])
    ]
    df["d_error"] = df["ans_D_norm"] - df["learned_D"]
    return df


def subject_cell_means(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return (
        df.groupby(["SubNo", *columns], as_index=False)["d_error"]
        .agg(d_error="mean", n_trials="size")
        .sort_values(["SubNo", *columns])
    )


def fit_trial_mixedlm(label: str, formula: str, re_formula: str, data: pd.DataFrame) -> TrialModelReport:
    model = smf.mixedlm(formula, data=data, groups=data["SubNo"], re_formula=re_formula)
    notes: list[str] = []
    result = None

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = model.fit(reml=False, method="powell", maxiter=2000, disp=False)
        except Exception as exc:
            notes.append(f"Fit failed: {type(exc).__name__}: {exc}")

    for warning in caught:
        notes.append(f"{warning.category.__name__}: {warning.message}")

    if result is not None and not result.converged:
        notes.append("MixedLM did not converge.")

    return TrialModelReport(
        label=label,
        formula=formula,
        re_formula=re_formula,
        result=result,
        notes=list(dict.fromkeys(notes)),
    )


def fit_rm_anova(data: pd.DataFrame, within: str):
    return AnovaRM(data=data, depvar="d_error", subject="SubNo", within=[within]).fit()


def paired_contrasts(
    data: pd.DataFrame,
    within: str,
    comparisons: list[tuple[str, str, str]],
    strategy: str,
) -> pd.DataFrame:
    wide = data.pivot(index="SubNo", columns=within, values="d_error")
    rows = []

    for label, numerator, denominator in comparisons:
        result = paired_test_report(wide[numerator], wide[denominator], numerator, denominator)
        rows.append(
            {
                "strategy": strategy,
                "contrast": label,
                "n_subjects": result["n_subjects"],
                "method": result["method"],
                "mean_diff": result["mean_difference"],
                "sd_diff": result["sd_difference"],
                "normality_shapiro_p": result["normality_shapiro_p"],
                "statistic": result["statistic"],
                "p_value": result["p_value"],
            }
        )

    return pd.DataFrame(rows)


CONDITION_FIGURE_LABELS = {
    "en": {
        "xlabel": "Distance condition",
        "ylabel": r"$\Delta$ distance",
        "title": "PD task distance error by observed condition",
        "xticklabels": ["same", "near", "far", "unknown"],
        "stem": "condition_means",
    },
    "zh": {
        "xlabel": "距离条件",
        "ylabel": "距离误差",
        "title": "PD 任务各条件距离误差",
        "xticklabels": ["同村庄", "近", "远", "未知"],
        "stem": "condition_means_zh",
    },
}


def save_condition_figure(subject_condition: pd.DataFrame, output_dir: Path, labels: str) -> None:
    label_map = CONDITION_FIGURE_LABELS[labels]
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=200)
    order = ["same", "near", "far", "unknown"]
    sns.barplot(
        data=subject_condition,
        x="condition",
        y="d_error",
        order=order,
        estimator="mean",
        errorbar="se",
        hue="condition",
        palette={key: CONDITION_PALETTE[key] for key in order},
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
    ax.set_xlabel(label_map["xlabel"])
    ax.set_xticks(range(len(order)), labels=label_map["xticklabels"])
    ax.set_ylabel(label_map["ylabel"])
    ax.set_title(label_map["title"])
    plt.tight_layout()
    save_figure(fig, output_dir, label_map["stem"])


def save_descriptive_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df[["SubNo", "scale_to_canonical"]].drop_duplicates().sort_values("SubNo").to_csv(
        output_dir / "subject_coordinate_scales.csv",
        index=False,
    )

    subject_condition = (
        df.groupby(["SubNo", "condition"], as_index=False)["d_error"].mean().sort_values(["SubNo", "condition"])
    )
    subject_condition.to_csv(output_dir / "subject_condition_means.csv", index=False)
    subject_cell_means(df, ["relationship"]).to_csv(output_dir / "subject_relationship_means.csv", index=False)
    subject_cell_means(df[df["relationship"] == "different"], ["distance_nested"]).to_csv(
        output_dir / "subject_distance_nested_means.csv",
        index=False,
    )

    summary = (
        df.groupby("condition")["d_error"]
        .agg(n_trials="size", mean="mean", sd="std")
        .assign(se=lambda x: x["sd"] / np.sqrt(x["n_trials"]))
        .reset_index()
    )
    summary.to_csv(output_dir / "condition_summary.csv", index=False)

    configure_plot_style(context="talk")
    plt.rcParams["font.family"] = "Arial Unicode MS"
    plt.rcParams["axes.unicode_minus"] = False
    for labels in ["en", "zh"]:
        save_condition_figure(subject_condition, output_dir, labels)


def write_model_report(
    trial_models: list[TrialModelReport],
    subject_anovas: list[tuple[str, object]],
    subject_contrasts: pd.DataFrame,
    output_dir: Path,
) -> None:
    lines = [
        "PDtask d_error analysis",
        "=======================",
        "",
        "Design note",
        "-----------",
        "Distance and village relationship are partially confounded due to design constraints.",
        "Raw AB and AC labels are recoded to near/far by participant parity before condition summaries and models.",
        "Distance errors use the learned EP/MR face coordinates as the psychological ground truth.",
        "PD source-code face coordinates are used only to infer each subject's square-size scale.",
        f"Included subject pool follows completed-all-task participants: {list(completed_all_task_subject_ids())}.",
        "Independent main effects should not be reported.",
        "",
        "Modeling note",
        "-------------",
        "Trial-level analyses use raw trials with MixedLM random subject intercepts and random condition slopes.",
        "Subject-level analyses use subject cell means with repeated-measures ANOVA and paired planned contrasts.",
        "Do not run MixedLM on already-aggregated subject means.",
        "",
        "Trial-level MixedLM analyses",
        "----------------------------",
    ]

    for model in trial_models:
        note_lines = [f"- {note}" for note in model.notes] if model.notes else ["- None"]
        lines.extend(
            [
                "",
                model.label,
                "~" * len(model.label),
                f"Formula: {model.formula}",
                f"Random effects: {model.re_formula} | SubNo",
                "Fit notes:",
                *note_lines,
                "",
                str(model.result.summary()) if model.result is not None else "No model result.",
            ]
        )

    lines.extend(
        [
            "",
            "Subject-level repeated-measures analyses",
            "----------------------------------------",
        ]
    )

    for label, anova in subject_anovas:
        lines.extend(
            [
                "",
                label,
                "~" * len(label),
                str(anova.summary()),
            ]
        )

    lines.extend(
        [
            "",
            "Subject-level planned paired contrasts",
            "--------------------------------------",
            *subject_contrasts.to_string(index=False, float_format=lambda x: f"{x:.4f}").splitlines(),
        ]
    )

    (output_dir / "model_report.txt").write_text("\n".join(lines), encoding="utf-8")


def save_subject_level_outputs(
    relationship_means: pd.DataFrame,
    distance_nested_means: pd.DataFrame,
    condition_means: pd.DataFrame,
    output_dir: Path,
) -> tuple[list[tuple[str, object]], pd.DataFrame]:
    subject_anovas = [
        ("Strategy 1A: relationship RM-ANOVA", fit_rm_anova(relationship_means, "relationship")),
        (
            "Strategy 1B: distance within different-village RM-ANOVA",
            fit_rm_anova(distance_nested_means, "distance_nested"),
        ),
        ("Strategy 2: observed condition RM-ANOVA", fit_rm_anova(condition_means, "condition")),
    ]

    subject_contrasts = pd.concat(
        [
            paired_contrasts(
                relationship_means,
                "relationship",
                [("different - same", "different", "same")],
                "Strategy 1A",
            ),
            paired_contrasts(
                distance_nested_means,
                "distance_nested",
                [
                    ("far - near", "far", "near"),
                    ("unknown - near", "unknown", "near"),
                    ("unknown - far", "unknown", "far"),
                ],
                "Strategy 1B",
            ),
            paired_contrasts(
                condition_means,
                "condition",
                [
                    ("near - same", "near", "same"),
                    ("far - same", "far", "same"),
                    ("unknown - same", "unknown", "same"),
                    ("far - near", "far", "near"),
                    ("unknown - near", "unknown", "near"),
                    ("unknown - far", "unknown", "far"),
                ],
                "Strategy 2",
            ),
        ],
        ignore_index=True,
    )
    subject_contrasts.to_csv(output_dir / "subject_planned_contrasts.csv", index=False)

    return subject_anovas, subject_contrasts


def fit_trial_level_models(df: pd.DataFrame) -> list[TrialModelReport]:
    different_only = df[df["relationship"] == "different"].copy()
    return [
        fit_trial_mixedlm(
            label="Strategy 1A: relationship, raw trial-level MixedLM",
            formula="d_error ~ C(relationship, Treatment(reference='same'))",
            re_formula="~ C(relationship, Treatment(reference='same'))",
            data=df,
        ),
        fit_trial_mixedlm(
            label="Strategy 1B: distance within different-village, raw trial-level MixedLM",
            formula="d_error ~ C(distance_nested, Treatment(reference='near'))",
            re_formula="~ C(distance_nested, Treatment(reference='near'))",
            data=different_only,
        ),
        fit_trial_mixedlm(
            label="Strategy 2: observed condition, raw trial-level MixedLM",
            formula="d_error ~ C(condition, Treatment(reference='same'))",
            re_formula="~ C(condition, Treatment(reference='same'))",
            data=df,
        ),
    ]


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

    relationship_means = subject_cell_means(df, ["relationship"])
    different_only = df[df["relationship"] == "different"].copy()
    distance_nested_means = subject_cell_means(different_only, ["distance_nested"])
    condition_means = subject_cell_means(df, ["condition"])

    trial_models = fit_trial_level_models(df)
    LOGGER.info("Completed trial-level MixedLM models")

    subject_anovas, subject_contrasts = save_subject_level_outputs(
        relationship_means=relationship_means,
        distance_nested_means=distance_nested_means,
        condition_means=condition_means,
        output_dir=OUTPUT_DIR,
    )
    LOGGER.info("Completed subject-level RM-ANOVA and planned paired contrasts")

    write_model_report(
        trial_models=trial_models,
        subject_anovas=subject_anovas,
        subject_contrasts=subject_contrasts,
        output_dir=OUTPUT_DIR,
    )
    LOGGER.info("Saved outputs to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
