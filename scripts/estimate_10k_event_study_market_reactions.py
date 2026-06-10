#!/usr/bin/env python3
"""Estimate 10-K filing event-study market reactions.

Inputs are daily event-panel rows generated from yfinance data. Outputs contain
firm-year CARs, abnormal-volume outcomes, placebo windows, and diagnostics.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DAILY_IN = REPO_ROOT / "data" / "derived" / "market_extension" / "daily_market_data_10k_events.csv"
ESTIMATES_OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "post_filing_market_reaction_estimates.csv"
DIAGNOSTICS_OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "event_study_estimation_diagnostics.csv"

ESTIMATION_WINDOW = (-250, -30)
CAR_WINDOWS = {
    "CAR_m1_p1": (-1, 1),
    "CAR_0_p1": (0, 1),
    "CAR_0_p3": (0, 3),
    "CAR_0_p5": (0, 5),
    "CAR_m10_m6": (-10, -6),
    "CAR_m5_m2": (-5, -2),
}
VOLUME_WINDOWS = {
    "AbnormalVolume_0_p1": (0, 1),
    "AbnormalVolume_0_p3": (0, 3),
    "AbnormalVolume_0_p5": (0, 5),
    "AbnormalVolume_m5_m2": (-5, -2),
}
MIN_ESTIMATION_N = 60

ESTIMATE_FIELDS = [
    "event_id", "ticker", "company", "filing_date", "event_trading_date", "market_benchmark",
    "market_data_status", "failure_reason", "CAR_m1_p1", "CAR_0_p1", "CAR_0_p3", "CAR_0_p5",
    "AbnormalVolume_0_p1", "AbnormalVolume_0_p3", "AbnormalVolume_0_p5",
    "CAR_m10_m6", "CAR_m5_m2", "AbnormalVolume_m5_m2",
]
DIAGNOSTIC_FIELDS = [
    "event_id", "ticker", "company", "filing_date", "estimation_n", "event_window_n",
    "market_model_alpha", "market_model_beta", "market_model_r2", "CAR_m1_p1", "CAR_0_p1",
    "CAR_0_p3", "CAR_0_p5", "AbnormalVolume_0_p1", "AbnormalVolume_0_p3",
    "AbnormalVolume_0_p5", "market_data_status", "failure_reason",
]


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def fit_market_model(est: pd.DataFrame) -> Tuple[float, float, float]:
    clean = est[["firm_return", "market_return"]].dropna()
    if len(clean) < MIN_ESTIMATION_N:
        return float("nan"), float("nan"), float("nan")
    x = clean["market_return"].to_numpy(dtype=float)
    y = clean["firm_return"].to_numpy(dtype=float)
    beta, alpha = np.polyfit(x, y, deg=1)
    y_hat = alpha + beta * x
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
    return float(alpha), float(beta), float(r2)


def window_sum(df: pd.DataFrame, col: str, start: int, end: int) -> Tuple[float, int]:
    window = df[(df["relative_trading_day"] >= start) & (df["relative_trading_day"] <= end)]
    vals = window[col].dropna()
    return (float(vals.sum()) if len(vals) else float("nan"), int(len(vals)))


def window_mean(df: pd.DataFrame, col: str, start: int, end: int) -> Tuple[float, int]:
    window = df[(df["relative_trading_day"] >= start) & (df["relative_trading_day"] <= end)]
    vals = window[col].dropna()
    return (float(vals.mean()) if len(vals) else float("nan"), int(len(vals)))


def estimate_event(event_id: str, event_rows: pd.DataFrame) -> Dict[str, object]:
    event_rows = event_rows.sort_values("relative_trading_day").copy()
    first = event_rows.iloc[0].to_dict()
    base: Dict[str, object] = {
        "event_id": event_id,
        "ticker": first.get("ticker_used", first.get("ticker_original", "")),
        "company": first.get("company", ""),
        "filing_date": first.get("filing_date", ""),
        "event_trading_date": first.get("event_trading_day", ""),
        "market_benchmark": first.get("benchmark_symbol", ""),
    }
    est = event_rows[
        (event_rows["relative_trading_day"] >= ESTIMATION_WINDOW[0])
        & (event_rows["relative_trading_day"] <= ESTIMATION_WINDOW[1])
    ].copy()
    est_clean = est[["firm_return", "market_return", "firm_log_volume"]].dropna()
    alpha, beta, r2 = fit_market_model(est)
    diagnostics: Dict[str, object] = {
        **base,
        "estimation_n": int(est[["firm_return", "market_return"]].dropna().shape[0]),
        "event_window_n": int(event_rows[(event_rows["relative_trading_day"] >= -1) & (event_rows["relative_trading_day"] <= 5)].shape[0]),
        "market_model_alpha": alpha,
        "market_model_beta": beta,
        "market_model_r2": r2,
    }
    if np.isnan(alpha) or np.isnan(beta):
        return {
            **diagnostics,
            "market_data_status": "failed",
            "failure_reason": f"insufficient_estimation_window_n={diagnostics['estimation_n']}",
        }

    event_rows["expected_return"] = alpha + beta * event_rows["market_return"]
    event_rows["abnormal_return"] = event_rows["firm_return"] - event_rows["expected_return"]
    volume_mean = float(est_clean["firm_log_volume"].mean()) if len(est_clean) else float("nan")
    volume_sd = float(est_clean["firm_log_volume"].std(ddof=1)) if len(est_clean) > 1 else float("nan")
    event_rows["abnormal_volume_z"] = (event_rows["firm_log_volume"] - volume_mean) / volume_sd if volume_sd and not np.isnan(volume_sd) else float("nan")

    out: Dict[str, object] = {**diagnostics}
    all_windows_ok = True
    for name, (start, end) in CAR_WINDOWS.items():
        value, n = window_sum(event_rows, "abnormal_return", start, end)
        out[name] = value
        out[f"{name}_n"] = n
        if name in {"CAR_m1_p1", "CAR_0_p1", "CAR_0_p3", "CAR_0_p5"} and n < (end - start + 1):
            all_windows_ok = False
    for name, (start, end) in VOLUME_WINDOWS.items():
        value, n = window_mean(event_rows, "abnormal_volume_z", start, end)
        out[name] = value
        out[f"{name}_n"] = n
        if name in {"AbnormalVolume_0_p1", "AbnormalVolume_0_p3", "AbnormalVolume_0_p5"} and n < (end - start + 1):
            all_windows_ok = False
    out["market_data_status"] = "success" if all_windows_ok else "partial"
    out["failure_reason"] = "" if all_windows_ok else "one_or_more_event_windows_incomplete"
    return out


def main() -> int:
    if not DAILY_IN.exists():
        raise SystemExit(f"Missing input: {DAILY_IN.relative_to(REPO_ROOT)}")
    daily = pd.read_csv(DAILY_IN)
    if daily.empty:
        write_csv(ESTIMATES_OUT, [], ESTIMATE_FIELDS)
        write_csv(DIAGNOSTICS_OUT, [], DIAGNOSTIC_FIELDS)
        print("No daily market rows available")
        return 0
    for col in ["relative_trading_day", "firm_return", "market_return", "firm_log_volume"]:
        daily[col] = pd.to_numeric(daily[col], errors="coerce")

    rows = [estimate_event(str(event_id), group) for event_id, group in daily.groupby("event_id", sort=True)]
    write_csv(ESTIMATES_OUT, rows, ESTIMATE_FIELDS)
    write_csv(DIAGNOSTICS_OUT, rows, DIAGNOSTIC_FIELDS)
    print(f"Event-study estimates: {ESTIMATES_OUT.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    print(f"Event-study diagnostics: {DIAGNOSTICS_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
