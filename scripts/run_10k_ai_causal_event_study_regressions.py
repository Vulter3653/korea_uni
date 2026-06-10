#!/usr/bin/env python3
"""Run event-study regressions for 10-K AI communication and market reactions.

The models are association/event-time regressions around 10-K filing dates. They
do not by themselves prove that AI disclosure causes market movement.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import statsmodels.formula.api as smf

REPO_ROOT = Path(__file__).resolve().parents[1]
AI_INPUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_final_ai_analysis_text_sample.csv"
ESTIMATES_INPUT = REPO_ROOT / "data" / "derived" / "market_extension" / "post_filing_market_reaction_estimates.csv"
DATASET_OUT = REPO_ROOT / "data" / "derived" / "causal" / "ai_10k_event_study_analysis_dataset.csv"
SUMMARY_OUT = REPO_ROOT / "data" / "derived" / "causal" / "causal_event_study_regression_summary.csv"
DIAGNOSTICS_OUT = REPO_ROOT / "data" / "derived" / "causal" / "causal_event_study_model_diagnostics.csv"
PLACEBO_OUT = REPO_ROOT / "data" / "derived" / "causal" / "placebo_pre_filing_checks.csv"

MAIN_IVS = ["AI_Related_Disclosure_Intensity", "AI_RiskRelated_Topic_Share", "AI_Risk_Orientation_Proxy"]
MAIN_DVS = [
    "CAR_m1_p1",
    "CAR_0_p1",
    "CAR_0_p3",
    "CAR_0_p5",
    "AbnormalVolume_0_p1",
    "AbnormalVolume_0_p3",
    "AbnormalVolume_0_p5",
]
PLACEBO_DVS = ["CAR_m10_m6", "CAR_m5_m2", "AbnormalVolume_m5_m2"]


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_ticker(ticker: object) -> str:
    return str(ticker or "").strip().replace(".", "-")


def event_id_from_ai(row: pd.Series) -> str:
    return f"{normalize_ticker(row.get('ticker', ''))}_{str(row.get('target_report_year', '')).strip()}_{str(row.get('cik_padded', '')).strip()}"


def to_numeric(df: pd.DataFrame, cols: Iterable[str]) -> None:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def build_dataset() -> pd.DataFrame:
    ai = pd.read_csv(AI_INPUT)
    estimates = pd.read_csv(ESTIMATES_INPUT)
    if estimates.empty:
        estimates = pd.DataFrame(columns=["event_id", "market_data_status", "failure_reason"] + MAIN_DVS + PLACEBO_DVS)
    ai["event_id"] = ai.apply(event_id_from_ai, axis=1)
    ai["AI_Related_Disclosure_Intensity"] = pd.to_numeric(ai.get("AI_Related_Disclosure_Intensity", ai.get("ai_keyword_per_10k_words")), errors="coerce")
    ai["AI_RiskRelated_Topic_Share"] = pd.to_numeric(ai.get("AI_RiskRelated_Topic_Share", ai.get("AI_NegativeSensitive_Topic_Share")), errors="coerce").fillna(0)
    ai["AI_Risk_Orientation_Proxy"] = pd.to_numeric(ai.get("AI_Risk_Orientation_Proxy", ai.get("AI_Negative_Orientation")), errors="coerce").fillna(0)
    ai["filing_year"] = pd.to_datetime(ai["filing_date"], errors="coerce").dt.year
    ai["log_total_words"] = pd.to_numeric(ai["total_words"], errors="coerce").map(lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan"))
    ai["AI_Mention_Count"] = pd.to_numeric(ai["ai_keyword_count"], errors="coerce").fillna(0)
    ai["Topic_Entropy"] = 0.0
    topic_share_cols = [col for col in ai.columns if col.startswith("topic_") and col.endswith("_share")]
    if topic_share_cols:
        shares = ai[topic_share_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        ai["Topic_Entropy"] = shares.apply(lambda row: -sum(float(v) * math.log(float(v)) for v in row if float(v) > 0), axis=1)
    keep_ai = [
        "event_id", "fortune_rank_2025", "company_name", "ticker", "cik_padded", "target_report_year",
        "filing_date", "report_date", "naics_sector_code", "naics_sector_name", "AI_Related_Disclosure_Intensity",
        "AI_RiskRelated_Topic_Share", "AI_Risk_Orientation_Proxy", "log_total_words", "AI_Mention_Count",
        "Topic_Entropy", "filing_year",
    ]
    merged = ai[keep_ai].merge(estimates, on="event_id", how="left", suffixes=("", "_estimate"))
    numeric_cols = MAIN_IVS + ["log_total_words", "AI_Mention_Count", "Topic_Entropy"] + MAIN_DVS + PLACEBO_DVS
    to_numeric(merged, numeric_cols)
    return merged


def formula_for(dv: str, fe_spec: str, controls: List[str]) -> str:
    rhs = MAIN_IVS + controls
    if fe_spec == "firm_year_fe":
        rhs += ["C(company_name)", "C(target_report_year)"]
    elif fe_spec == "year_fe":
        rhs += ["C(target_report_year)"]
    elif fe_spec == "sector_year_fe":
        rhs += ["C(naics_sector_code)", "C(target_report_year)"]
    return f"{dv} ~ " + " + ".join(rhs)


def fit_model(df: pd.DataFrame, dv: str) -> Tuple[object, str, str]:
    controls = [col for col in ["log_total_words", "AI_Mention_Count", "Topic_Entropy"] if col in df.columns]
    specs = ["firm_year_fe", "year_fe", "sector_year_fe", "no_fe_baseline"]
    needed = [dv] + MAIN_IVS + controls
    model_df = df[df["market_data_status"].isin(["success", "partial"])].dropna(subset=needed).copy()
    if len(model_df) < 20:
        raise ValueError(f"insufficient_regression_rows={len(model_df)}")
    for spec in specs:
        try:
            formula = formula_for(dv, spec, controls)
            base_model = smf.ols(formula, data=model_df)
            if model_df["company_name"].nunique() > 1:
                result = base_model.fit(cov_type="cluster", cov_kwds={"groups": model_df["company_name"]})
                se_spec = "firm_clustered"
            else:
                result = base_model.fit(cov_type="HC1")
                se_spec = "HC1"
            if result.df_resid <= 0:
                continue
            return result, spec, se_spec
        except Exception:
            continue
    result = smf.ols(formula_for(dv, "no_fe_baseline", controls), data=model_df).fit(cov_type="HC1")
    return result, "no_fe_baseline", "HC1"


def coefficient_rows(result: object, dv: str, fe_spec: str, se_spec: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for term in MAIN_IVS:
        rows.append(
            {
                "outcome": dv,
                "term": term,
                "coef": result.params.get(term, float("nan")),
                "std_error": result.bse.get(term, float("nan")),
                "t_stat": result.tvalues.get(term, float("nan")),
                "p_value": result.pvalues.get(term, float("nan")),
                "n_obs": int(result.nobs),
                "r_squared": float(result.rsquared),
                "fe_specification": fe_spec,
                "se_specification": se_spec,
                "interpretation": "association estimate; not a standalone causal-effect claim",
            }
        )
    return rows


def diagnostic_row(result: object, dv: str, fe_spec: str, se_spec: str) -> Dict[str, object]:
    return {
        "outcome": dv,
        "n_obs": int(result.nobs),
        "df_resid": float(result.df_resid),
        "r_squared": float(result.rsquared),
        "adj_r_squared": float(result.rsquared_adj),
        "fe_specification": fe_spec,
        "se_specification": se_spec,
        "model_status": "estimated",
        "warning": "",
    }


def failed_rows(dv: str, error: Exception) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    rows = [
        {
            "outcome": dv,
            "term": term,
            "coef": "",
            "std_error": "",
            "t_stat": "",
            "p_value": "",
            "n_obs": 0,
            "r_squared": "",
            "fe_specification": "not_estimated",
            "se_specification": "not_estimated",
            "interpretation": f"model failed: {error}",
        }
        for term in MAIN_IVS
    ]
    diag = {
        "outcome": dv,
        "n_obs": 0,
        "df_resid": "",
        "r_squared": "",
        "adj_r_squared": "",
        "fe_specification": "not_estimated",
        "se_specification": "not_estimated",
        "model_status": "failed",
        "warning": str(error),
    }
    return rows, diag


def run_models(df: pd.DataFrame, dvs: List[str]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    summary_rows: List[Dict[str, object]] = []
    diagnostics: List[Dict[str, object]] = []
    for dv in dvs:
        try:
            result, fe_spec, se_spec = fit_model(df, dv)
            summary_rows.extend(coefficient_rows(result, dv, fe_spec, se_spec))
            diagnostics.append(diagnostic_row(result, dv, fe_spec, se_spec))
        except Exception as exc:
            rows, diag = failed_rows(dv, exc)
            summary_rows.extend(rows)
            diagnostics.append(diag)
    return summary_rows, diagnostics


def main() -> int:
    if not ESTIMATES_INPUT.exists():
        raise SystemExit(f"Missing input: {ESTIMATES_INPUT.relative_to(REPO_ROOT)}")
    dataset = build_dataset()
    DATASET_OUT.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(DATASET_OUT, index=False)

    main_rows, diagnostics = run_models(dataset, MAIN_DVS)
    placebo_rows, placebo_diags = run_models(dataset, PLACEBO_DVS)

    summary_fields = [
        "outcome", "term", "coef", "std_error", "t_stat", "p_value", "n_obs",
        "r_squared", "fe_specification", "se_specification", "interpretation",
    ]
    diagnostic_fields = [
        "outcome", "n_obs", "df_resid", "r_squared", "adj_r_squared",
        "fe_specification", "se_specification", "model_status", "warning",
    ]
    write_csv(SUMMARY_OUT, main_rows, summary_fields)
    write_csv(DIAGNOSTICS_OUT, diagnostics + placebo_diags, diagnostic_fields)
    write_csv(PLACEBO_OUT, placebo_rows, summary_fields)
    print(f"Causal event-study analysis dataset: {DATASET_OUT.relative_to(REPO_ROOT)} ({len(dataset)} rows)")
    print(f"Regression summary: {SUMMARY_OUT.relative_to(REPO_ROOT)}")
    print(f"Model diagnostics: {DIAGNOSTICS_OUT.relative_to(REPO_ROOT)}")
    print(f"Placebo checks: {PLACEBO_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
