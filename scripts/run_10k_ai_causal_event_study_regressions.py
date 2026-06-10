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
    if pd.isna(ticker):
        return ""
    return str(ticker).strip().upper().replace(".", "-")

def normalize_cik(value: object) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = "".join(ch for ch in s if ch.isdigit())
    return s.zfill(10) if s else ""

def normalize_date(value: object) -> str:
    if pd.isna(value):
        return ""
    return pd.to_datetime(value, errors="coerce").strftime("%Y-%m-%d")

def event_id_from_ai(row: pd.Series) -> str:
    return f"{normalize_ticker(row.get('ticker', ''))}_{str(row.get('target_report_year', '')).strip()}_{str(row.get('cik_padded', '')).strip()}"


def to_numeric(df: pd.DataFrame, cols: Iterable[str]) -> None:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


def build_dataset() -> Tuple[pd.DataFrame, Dict[str, object]]:
    ai = pd.read_csv(AI_INPUT)
    estimates = pd.read_csv(ESTIMATES_INPUT)
    if estimates.empty:
        estimates = pd.DataFrame(columns=["event_id", "market_data_status", "failure_reason", "ticker_original", "ticker", "filing_date"] + MAIN_DVS + PLACEBO_DVS)

    ai["event_id"] = ai.apply(event_id_from_ai, axis=1)

    ai["norm_cik"] = ai["cik_padded"].apply(normalize_cik)
    ai["norm_ticker"] = ai["ticker"].apply(normalize_ticker)
    ai["norm_date"] = ai["filing_date"].apply(normalize_date)
    ai["fiscal_year"] = ai["target_report_year"].astype(str)

    estimates["norm_cik"] = estimates.get("cik", pd.Series(dtype=str)).apply(normalize_cik)
    estimates["norm_ticker"] = estimates.get("ticker_original", estimates.get("ticker")).apply(normalize_ticker)
    estimates["norm_date"] = estimates["filing_date"].apply(normalize_date)

    merged = pd.DataFrame()
    merge_key_used = ""
    duplicate_ai = 0
    duplicate_est = 0

    # 1. event_id
    if "event_id" in ai.columns and "event_id" in estimates.columns and len(set(ai["event_id"]).intersection(set(estimates["event_id"]))) > 0:
        merged = ai.merge(estimates, on="event_id", how="left", suffixes=("", "_estimate"))
        merge_key_used = "event_id"
        duplicate_ai = ai.duplicated(subset=["event_id"]).sum()
        duplicate_est = estimates.duplicated(subset=["event_id"]).sum()
    else:
        # 2. norm_cik + norm_date
        ai["key_cik_date"] = ai["norm_cik"] + "_" + ai["norm_date"]
        estimates["key_cik_date"] = estimates["norm_cik"] + "_" + estimates["norm_date"]
        if len(set(ai["key_cik_date"]).intersection(set(estimates["key_cik_date"]))) > 0:
            merged = ai.merge(estimates, on="key_cik_date", how="left", suffixes=("", "_estimate"))
            merge_key_used = "cik_filing_date"
            duplicate_ai = ai.duplicated(subset=["key_cik_date"]).sum()
            duplicate_est = estimates.duplicated(subset=["key_cik_date"]).sum()
        else:
            # 3. norm_ticker + norm_date
            ai["key_ticker_date"] = ai["norm_ticker"] + "_" + ai["norm_date"]
            estimates["key_ticker_date"] = estimates["norm_ticker"] + "_" + estimates["norm_date"]
            if len(set(ai["key_ticker_date"]).intersection(set(estimates["key_ticker_date"]))) > 0:
                merged = ai.merge(estimates, on="key_ticker_date", how="left", suffixes=("", "_estimate"))
                merge_key_used = "ticker_filing_date"
                duplicate_ai = ai.duplicated(subset=["key_ticker_date"]).sum()
                duplicate_est = estimates.duplicated(subset=["key_ticker_date"]).sum()
            else:
                # 4. norm_ticker + fiscal_year (fallback if dates mismatch)
                if "target_report_year" in estimates.columns:
                     estimates["fiscal_year"] = estimates["target_report_year"].astype(str)
                else:
                    # attempt to extract year from event_id if available, else date
                    estimates["fiscal_year"] = estimates["event_id"].astype(str).str.split("_").str[1]

                ai["key_ticker_fy"] = ai["norm_ticker"] + "_" + ai["fiscal_year"]
                estimates["key_ticker_fy"] = estimates["norm_ticker"] + "_" + estimates["fiscal_year"]
                if len(set(ai["key_ticker_fy"]).intersection(set(estimates["key_ticker_fy"]))) > 0:
                    merged = ai.merge(estimates, on="key_ticker_fy", how="left", suffixes=("", "_estimate"))
                    merge_key_used = "ticker_fiscal_year"
                    duplicate_ai = ai.duplicated(subset=["key_ticker_fy"]).sum()
                    duplicate_est = estimates.duplicated(subset=["key_ticker_fy"]).sum()

    if merged.empty:
        merged = ai.copy()
        for col in MAIN_DVS + PLACEBO_DVS + ["market_data_status", "failure_reason"]:
            merged[col] = float("nan") if col not in ["market_data_status", "failure_reason"] else ""
        merge_key_used = "failed"

    merged["AI_Related_Disclosure_Intensity"] = pd.to_numeric(merged.get("AI_Related_Disclosure_Intensity", merged.get("ai_keyword_per_10k_words")), errors="coerce")
    merged["AI_RiskRelated_Topic_Share"] = pd.to_numeric(merged.get("AI_RiskRelated_Topic_Share", merged.get("AI_NegativeSensitive_Topic_Share")), errors="coerce").fillna(0)
    merged["AI_Risk_Orientation_Proxy"] = pd.to_numeric(merged.get("AI_Risk_Orientation_Proxy", merged.get("AI_Negative_Orientation")), errors="coerce").fillna(0)
    merged["filing_year"] = pd.to_datetime(merged["filing_date"], errors="coerce").dt.year
    merged["log_total_words"] = pd.to_numeric(merged["total_words"], errors="coerce").map(lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan"))
    merged["AI_Mention_Count"] = pd.to_numeric(merged["ai_keyword_count"], errors="coerce").fillna(0)
    merged["Topic_Entropy"] = 0.0
    topic_share_cols = [col for col in merged.columns if col.startswith("topic_") and col.endswith("_share")]
    if topic_share_cols:
        shares = merged[topic_share_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        merged["Topic_Entropy"] = shares.apply(lambda row: -sum(float(v) * math.log(float(v)) for v in row if float(v) > 0), axis=1)

    # ensure market data cols exist
    for col in MAIN_DVS + PLACEBO_DVS:
        if col not in merged.columns:
            merged[col] = float("nan")

    numeric_cols = MAIN_IVS + ["log_total_words", "AI_Mention_Count", "Topic_Entropy"] + MAIN_DVS + PLACEBO_DVS
    to_numeric(merged, numeric_cols)

    diag = {
        "ai_rows": len(ai),
        "estimate_rows": len(estimates),
        "merge_key_used": merge_key_used,
        "merged_rows": len(merged),
        "duplicate_key_rows_ai": int(duplicate_ai),
        "duplicate_key_rows_estimates": int(duplicate_est),
        "failure_reason": "" if merge_key_used != "failed" else "no_overlapping_keys"
    }
    for col in MAIN_DVS:
        diag[f"rows_with_numeric_{col}"] = int(merged[col].notna().sum())

    return merged, diag


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


MERGE_DIAGNOSTICS_OUT = REPO_ROOT / "data" / "derived" / "causal" / "event_study_merge_diagnostics.csv"

def main() -> int:
    if not ESTIMATES_INPUT.exists():
        raise SystemExit(f"Missing input: {ESTIMATES_INPUT.relative_to(REPO_ROOT)}")
    dataset, merge_diag = build_dataset()
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

    merge_diag_fields = ["ai_rows", "estimate_rows", "merge_key_used", "merged_rows", "duplicate_key_rows_ai", "duplicate_key_rows_estimates", "failure_reason"] + [f"rows_with_numeric_{c}" for c in MAIN_DVS]
    write_csv(MERGE_DIAGNOSTICS_OUT, [merge_diag], merge_diag_fields)

    print(f"Causal event-study analysis dataset: {DATASET_OUT.relative_to(REPO_ROOT)} ({len(dataset)} rows)")
    print(f"Regression summary: {SUMMARY_OUT.relative_to(REPO_ROOT)}")
    print(f"Model diagnostics: {DIAGNOSTICS_OUT.relative_to(REPO_ROOT)}")
    print(f"Placebo checks: {PLACEBO_OUT.relative_to(REPO_ROOT)}")
    print(f"Merge diagnostics: {MERGE_DIAGNOSTICS_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
