#!/usr/bin/env python3
"""Collect daily market data for the 10-K filing event-study panel.

The script uses 10-K filing_date as the event date, downloads firm-level price
and volume data plus a market benchmark, and writes a trading-day event panel.
It does not estimate CARs or regressions.
"""

from __future__ import annotations

import csv
import math
import sys
import time
from datetime import timedelta
from urllib.parse import urlencode
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Any

import pandas as pd
import yfinance as yf
try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "data" / "derived" / "market_extension" / "post_filing_market_reaction_scaffold.csv"
DAILY_OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "daily_market_data_10k_events.csv"
REPORT_OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "market_data_collection_report.csv"

LOCAL_PRICES_DIR = REPO_ROOT / "data" / "raw" / "market_data" / "prices"
LOCAL_BENCHMARKS_DIR = REPO_ROOT / "data" / "raw" / "market_data" / "benchmarks"

REL_START = -260
REL_END = 10


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_yfinance_ticker(ticker: str) -> str:
    if not isinstance(ticker, str) or not ticker.strip():
        return ""
    ticker = ticker.strip().upper()
    if ticker.startswith("^"):
        return ticker
    return ticker.replace(".", "-")


def event_id(row: Dict[str, str]) -> str:
    ticker = row.get("ticker", "").strip()
    year = str(row.get("target_report_year", "")).strip()
    cik = str(row.get("cik_padded", "")).strip()
    return f"{ticker}_{year}_{cik}"


def normalize_history(data: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    if "Date" not in data.columns and "date" not in data.columns:
        if data.index.name is None:
            data.index.name = "date"
        data = data.reset_index()
    else:
        data = data.copy()
    data.columns = [str(col).lower().replace(" ", "_") for col in data.columns]

    price_col = "adj_close" if "adj_close" in data.columns else "close"
    if price_col not in data.columns and "adj close" in data.columns:
         data = data.rename(columns={"adj close": "adj_close"})
         price_col = "adj_close"

    if price_col not in data.columns:
        return pd.DataFrame()

    has_volume = "volume" in data.columns
    keep_cols = ["date", price_col]
    if has_volume:
        keep_cols.append("volume")
    if "close" in data.columns:
        keep_cols.append("close")

    keep = data[list(set(keep_cols).intersection(data.columns))].copy().rename(columns={price_col: "adj_close"})
    if "close" not in keep.columns:
        keep["close"] = keep["adj_close"]

    keep["date"] = pd.to_datetime(keep["date"], utc=True).dt.tz_localize(None).dt.normalize()

    subset_dropna = ["adj_close", "volume"] if has_volume else ["adj_close"]
    keep = keep.dropna(subset=subset_dropna).sort_values("date")

    keep["return"] = (keep["adj_close"].astype(float) / keep["adj_close"].astype(float).shift(1)).map(
        lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan")
    )
    if has_volume:
        keep["log_volume"] = keep["volume"].astype(float).map(lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan"))
    else:
        keep["volume"] = float("nan")
        keep["log_volume"] = float("nan")

    keep["data_source"] = source_name
    return keep


def load_local_history(ticker: str, is_benchmark: bool = False) -> pd.DataFrame:
    dir_path = LOCAL_BENCHMARKS_DIR if is_benchmark else LOCAL_PRICES_DIR
    if not dir_path.exists():
        return pd.DataFrame()
    for p in dir_path.glob("*.csv"):
        if p.stem.upper() == normalize_yfinance_ticker(ticker).upper() or p.stem.upper() == ticker.upper():
            try:
                df = pd.read_csv(p)
                return normalize_history(df, "local_csv")
            except Exception:
                continue
    return pd.DataFrame()


def download_history_yfinance(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    try:
        data = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=False,
            threads=False,
            ignore_tz=True
        )
    except Exception:
        return pd.DataFrame()
    return normalize_history(data, "yfinance")


def fetch_with_finance_datareader(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if fdr is None:
        return pd.DataFrame()
    try:
        df = fdr.DataReader(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df.empty:
            return pd.DataFrame()
        return normalize_history(df, "finance_datareader")
    except Exception:
        return pd.DataFrame()


def download_firm_history(ticker_original: str, ticker_yfinance: str, start: pd.Timestamp, end: pd.Timestamp) -> Tuple[pd.DataFrame, str]:
    # 1. Local CSV
    local_df = load_local_history(ticker_yfinance, is_benchmark=False)
    if not local_df.empty:
        return local_df, ticker_yfinance

    # 2. FinanceDataReader original ticker
    fdr_df1 = fetch_with_finance_datareader(ticker_original, start, end)
    if not fdr_df1.empty:
        return fdr_df1, ticker_original

    # 3. FinanceDataReader yfinance ticker
    fdr_df2 = fetch_with_finance_datareader(ticker_yfinance, start, end)
    if not fdr_df2.empty:
        return fdr_df2, ticker_yfinance

    # 4. yfinance with yfinance ticker
    yf_df = download_history_yfinance(ticker_yfinance, start, end)
    if not yf_df.empty:
        return yf_df, ticker_yfinance

    return pd.DataFrame(), ""


def select_benchmark(start: pd.Timestamp, end: pd.Timestamp) -> Tuple[str, pd.DataFrame, str]:
    # Priority:
    # 1. US500 via FinanceDataReader
    # 2. SPY via FinanceDataReader
    # 3. SPY via yfinance
    # 4. ^GSPC via yfinance
    # 5. IVV via yfinance
    # 6. VOO via yfinance

    candidates = [
        ("US500", "fdr"),
        ("SPY", "fdr"),
        ("SPY", "yf"),
        ("^GSPC", "yf"),
        ("IVV", "yf"),
        ("VOO", "yf")
    ]

    for symbol, source_type in candidates:
        local_df = load_local_history(symbol, is_benchmark=True)
        if not local_df.empty:
            return symbol, local_df, "local_csv"

        if source_type == "fdr":
            df = fetch_with_finance_datareader(symbol, start, end)
            if not df.empty:
                return symbol, df, "finance_datareader"
        elif source_type == "yf":
            df = download_history_yfinance(symbol, start, end)
            if not df.empty:
                return symbol, df, "yfinance"

    return "", pd.DataFrame(), ""


def build_event_rows(event: Dict[str, str], firm_data: pd.DataFrame, ticker_used: str, market_data: pd.DataFrame, benchmark: str, benchmark_source: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    filing_date_str = event.get("event_date", "")
    filing_date = pd.to_datetime(filing_date_str, errors="coerce")

    firm_source = firm_data["data_source"].iloc[0] if not firm_data.empty and "data_source" in firm_data.columns else ""

    base = {
        "event_id": event_id(event),
        "company": event.get("company_name", ""),
        "ticker_original": event.get("ticker", ""),
        "ticker_yfinance": normalize_yfinance_ticker(event.get("ticker", "")),
        "ticker_used": ticker_used,
        "firm_data_source": firm_source,
        "benchmark_symbol": benchmark,
        "benchmark_data_source": benchmark_source,
        "filing_date": filing_date_str,
    }

    if pd.isna(filing_date):
        return [], {**base, "market_data_status": "failed", "failure_reason": "missing_or_invalid_filing_date", "event_trading_day": "", "estimation_window_mode": "insufficient"}

    if firm_data.empty:
        return [], {**base, "market_data_status": "missing_firm_data", "failure_reason": "missing_firm_data", "event_trading_day": "", "estimation_window_mode": "insufficient"}

    if market_data.empty:
        return [], {**base, "market_data_status": "missing_benchmark_data", "failure_reason": "missing_benchmark_data", "event_trading_day": "", "estimation_window_mode": "insufficient"}

    firm = firm_data[["date", "adj_close", "close", "volume", "return", "log_volume"]].rename(
        columns={
            "adj_close": "firm_adj_close",
            "close": "firm_close",
            "volume": "firm_volume",
            "return": "firm_return",
            "log_volume": "firm_log_volume",
        }
    )
    market = market_data[["date", "adj_close", "volume", "return"]].rename(
        columns={
            "adj_close": "benchmark_adj_close",
            "volume": "benchmark_volume",
            "return": "market_return"
        }
    )

    merged = firm.merge(market, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if merged.empty:
        return [], {**base, "market_data_status": "failed", "failure_reason": "no_common_firm_market_trading_days", "event_trading_day": "", "estimation_window_mode": "insufficient"}

    end_calendar_date = filing_date + pd.Timedelta(days=5)
    event_candidates = merged[(merged["date"] >= filing_date) & (merged["date"] <= end_calendar_date)]
    if event_candidates.empty:
        return [], {**base, "market_data_status": "no_event_trading_day", "failure_reason": "no_trading_date_within_5_days_after_filing", "event_trading_day": "", "estimation_window_mode": "insufficient"}

    event_pos = int(event_candidates.index[0])
    event_trading_day = merged.loc[event_pos, "date"]

    start_pos = max(0, event_pos + REL_START)
    end_pos = min(len(merged) - 1, event_pos + REL_END)
    window = merged.loc[start_pos:end_pos].copy()
    window["relative_trading_day"] = window.index - event_pos

    estimation_n = int(window[(window["relative_trading_day"] >= -250) & (window["relative_trading_day"] <= -30)]["firm_return"].dropna().shape[0])
    has_event_rows = all(day in set(window["relative_trading_day"]) for day in [0, 1, 3, 5])

    if estimation_n >= 220:
        window_mode = "full_250_30"
        status = "success"
    elif estimation_n >= 120:
        window_mode = "fallback_120"
        status = "success"
    elif estimation_n >= 60:
        window_mode = "fallback_60"
        status = "success"
    else:
        window_mode = "insufficient"
        status = "insufficient_estimation_window"

    if not has_event_rows and status == "success":
        status = "failed"

    reason = "" if status == "success" else f"estimation_n={estimation_n}; has_event_rows={has_event_rows}"

    rows: List[Dict[str, object]] = []
    for _, row in window.iterrows():
        rows.append(
            {
                **base,
                "event_trading_day": event_trading_day.strftime("%Y-%m-%d"),
                "date": row["date"].strftime("%Y-%m-%d"),
                "relative_trading_day": int(row["relative_trading_day"]),
                "firm_close": row["firm_close"],
                "firm_adj_close": row["firm_adj_close"],
                "firm_volume": row["firm_volume"],
                "firm_log_volume": row["firm_log_volume"],
                "benchmark_close": row.get("benchmark_close", row["benchmark_adj_close"]),
                "benchmark_adj_close": row["benchmark_adj_close"],
                "benchmark_volume": row["benchmark_volume"],
                "firm_return": row["firm_return"],
                "market_return": row["market_return"]
            }
        )
    diag = {
        **base,
        "market_data_status": status,
        "failure_reason": reason,
        "event_trading_day": event_trading_day.strftime("%Y-%m-%d"),
        "daily_event_rows": len(rows),
        "estimation_window_mode": window_mode,
        "firm_rows_raw": len(firm_data),
        "benchmark_rows_raw": len(market_data)
    }
    return rows, diag


def main() -> int:
    events = read_csv(INPUT)
    dated = [pd.to_datetime(row.get("event_date", ""), errors="coerce") for row in events]
    valid_dates = [date for date in dated if pd.notna(date)]
    if not valid_dates:
        raise SystemExit("No valid event dates found")
    start = min(valid_dates) - timedelta(days=430)
    end = max(valid_dates) + timedelta(days=45)

    benchmark, market_data, benchmark_source = select_benchmark(start, end)

    all_rows: List[Dict[str, object]] = []
    diags: List[Dict[str, object]] = []

    for event in events:
        ticker_orig = event.get("ticker", "").strip()
        ticker_yf = normalize_yfinance_ticker(ticker_orig)

        if not ticker_orig:
            diags.append({
                "event_id": event_id(event), "company": event.get("company_name", ""),
                "ticker_original": "", "ticker_yfinance": "", "ticker_used": "",
                "filing_date": event.get("event_date", ""), "event_trading_day": "",
                "firm_data_source": "", "benchmark_symbol": benchmark, "benchmark_data_source": benchmark_source,
                "firm_rows_raw": 0, "benchmark_rows_raw": len(market_data) if not market_data.empty else 0,
                "daily_event_rows": 0, "estimation_window_mode": "insufficient",
                "market_data_status": "missing_firm_or_benchmark_data", "failure_reason": "missing_ticker"
            })
            continue

        firm_data, ticker_used = download_firm_history(ticker_orig, ticker_yf, start, end)

        if firm_data.empty or market_data.empty:
            status = "missing_firm_or_benchmark_data"
            if firm_data.empty and not market_data.empty:
                status = "missing_firm_data"
            elif not firm_data.empty and market_data.empty:
                status = "missing_benchmark_data"

            diags.append({
                "event_id": event_id(event), "company": event.get("company_name", ""),
                "ticker_original": ticker_orig, "ticker_yfinance": ticker_yf, "ticker_used": ticker_used,
                "filing_date": event.get("event_date", ""), "event_trading_day": "",
                "firm_data_source": firm_data["data_source"].iloc[0] if not firm_data.empty and "data_source" in firm_data.columns else "",
                "benchmark_symbol": benchmark, "benchmark_data_source": benchmark_source,
                "firm_rows_raw": len(firm_data), "benchmark_rows_raw": len(market_data) if not market_data.empty else 0,
                "daily_event_rows": 0, "estimation_window_mode": "insufficient",
                "market_data_status": status, "failure_reason": status
            })
            continue

        rows, diag = build_event_rows(event, firm_data, ticker_used, market_data, benchmark, benchmark_source)
        all_rows.extend(rows)
        diags.append(diag)
        time.sleep(0.05)

    daily_fields = [
        "event_id", "company", "ticker_original", "ticker_yfinance", "ticker_used",
        "firm_data_source", "benchmark_symbol", "benchmark_data_source",
        "filing_date", "event_trading_day", "date", "relative_trading_day",
        "firm_close", "firm_adj_close", "firm_volume", "firm_log_volume",
        "benchmark_close", "benchmark_adj_close", "benchmark_volume",
        "firm_return", "market_return"
    ]
    write_csv(DAILY_OUT, all_rows, daily_fields)

    report_fields = [
        "event_id", "company", "ticker_original", "ticker_yfinance", "ticker_used",
        "filing_date", "event_trading_day", "firm_data_source", "benchmark_symbol",
        "benchmark_data_source", "firm_rows_raw", "benchmark_rows_raw",
        "daily_event_rows", "estimation_window_mode", "market_data_status", "failure_reason"
    ]
    write_csv(REPORT_OUT, diags, report_fields)

    print(f"Daily market event panel: {DAILY_OUT.relative_to(REPO_ROOT)} ({len(all_rows)} rows)")
    print(f"Market data collection report: {REPORT_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
