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
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "data" / "derived" / "market_extension" / "post_filing_market_reaction_scaffold.csv"
DAILY_OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "daily_market_data_10k_events.csv"
REPORT_OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "market_data_collection_report.csv"

BENCHMARK_CANDIDATES = ["SPY", "^GSPC"]
REL_START = -260
REL_END = 10
MIN_ESTIMATION_DAYS = 120


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_ticker(ticker: str) -> str:
    return str(ticker or "").strip().replace(".", "-")


def event_id(row: Dict[str, str]) -> str:
    ticker = normalize_ticker(row.get("ticker", ""))
    year = str(row.get("target_report_year", "")).strip()
    cik = str(row.get("cik_padded", "")).strip()
    return f"{ticker}_{year}_{cik}"


def stooq_symbol(ticker: str) -> str:
    ticker = normalize_ticker(ticker).lower()
    if ticker == "spy":
        return "spy.us"
    if ticker == "^gspc":
        return "^spx"
    return f"{ticker}.us"


def normalize_history(data: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]
    data = data.reset_index() if "Date" not in data.columns and "date" not in data.columns else data.copy()
    data.columns = [str(col).lower().replace(" ", "_") for col in data.columns]
    price_col = "adj_close" if "adj_close" in data.columns else "close"
    required = {"date", price_col, "volume"}
    if not required.issubset(set(data.columns)):
        return pd.DataFrame()
    keep_cols = ["date", price_col, "volume"] + (["close"] if "close" in data.columns else [])
    keep = data[keep_cols].copy().rename(columns={price_col: "adj_close"})
    if "close" not in keep.columns:
        keep["close"] = keep["adj_close"]
    keep["date"] = pd.to_datetime(keep["date"]).dt.normalize()
    keep = keep.dropna(subset=["adj_close", "volume"]).sort_values("date")
    keep["return"] = (keep["adj_close"].astype(float) / keep["adj_close"].astype(float).shift(1)).map(
        lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan")
    )
    keep["log_volume"] = keep["volume"].astype(float).map(lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan"))
    return keep


def download_history_yfinance(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    data = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    return normalize_history(data)


def download_history_stooq(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    params = urlencode({"s": stooq_symbol(ticker), "d1": start.strftime("%Y%m%d"), "d2": end.strftime("%Y%m%d"), "i": "d"})
    data = pd.read_csv(f"https://stooq.com/q/d/l/?{params}")
    return normalize_history(data)


def download_history(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    for source in (download_history_yfinance, download_history_stooq):
        try:
            data = source(ticker, start, end)
            if not data.empty:
                return data
        except Exception:
            continue
    return pd.DataFrame()


def select_benchmark(start: pd.Timestamp, end: pd.Timestamp) -> Tuple[str, pd.DataFrame]:
    for ticker in BENCHMARK_CANDIDATES:
        data = download_history(ticker, start, end)
        if not data.empty:
            return ticker, data
    return "", pd.DataFrame()


def build_event_rows(event: Dict[str, str], firm_data: pd.DataFrame, market_data: pd.DataFrame, benchmark: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    filing_date = pd.to_datetime(event.get("event_date", ""), errors="coerce")
    base = {
        "event_id": event_id(event),
        "ticker": normalize_ticker(event.get("ticker", "")),
        "company_name": event.get("company_name", ""),
        "target_report_year": event.get("target_report_year", ""),
        "filing_date": event.get("event_date", ""),
        "market_benchmark": benchmark,
    }
    if pd.isna(filing_date):
        return [], {**base, "market_data_status": "failed", "failure_reason": "missing_or_invalid_filing_date", "event_trading_date": "", "available_event_rows": 0}

    firm = firm_data[["date", "adj_close", "close", "volume", "return", "log_volume"]].rename(
        columns={
            "adj_close": "firm_adj_close",
            "close": "firm_close",
            "volume": "firm_volume",
            "return": "firm_return",
            "log_volume": "firm_log_volume",
        }
    )
    market = market_data[["date", "adj_close", "return"]].rename(
        columns={"adj_close": "market_adj_close", "return": "market_return"}
    )
    merged = firm.merge(market, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if merged.empty:
        return [], {**base, "market_data_status": "failed", "failure_reason": "no_common_firm_market_trading_days", "event_trading_date": "", "available_event_rows": 0}

    event_candidates = merged.index[merged["date"] >= filing_date]
    if len(event_candidates) == 0:
        return [], {**base, "market_data_status": "failed", "failure_reason": "no_trading_date_on_or_after_filing_date", "event_trading_date": "", "available_event_rows": 0}
    event_pos = int(event_candidates[0])
    event_trading_date = merged.loc[event_pos, "date"]
    start_pos = max(0, event_pos + REL_START)
    end_pos = min(len(merged) - 1, event_pos + REL_END)
    window = merged.loc[start_pos:end_pos].copy()
    window["relative_trading_day"] = window.index - event_pos

    estimation_n = int(window[(window["relative_trading_day"] >= -250) & (window["relative_trading_day"] <= -30)]["firm_return"].dropna().shape[0])
    has_event_rows = all(day in set(window["relative_trading_day"]) for day in [0, 1, 3, 5])
    status = "success" if estimation_n >= MIN_ESTIMATION_DAYS and has_event_rows else "insufficient_data"
    reason = "" if status == "success" else f"estimation_n={estimation_n}; has_event_rows={has_event_rows}"

    rows: List[Dict[str, object]] = []
    for _, row in window.iterrows():
        rows.append(
            {
                **base,
                "event_trading_date": event_trading_date.strftime("%Y-%m-%d"),
                "date": row["date"].strftime("%Y-%m-%d"),
                "relative_trading_day": int(row["relative_trading_day"]),
                "firm_adj_close": row["firm_adj_close"],
                "firm_close": row["firm_close"],
                "firm_volume": row["firm_volume"],
                "firm_return": row["firm_return"],
                "firm_log_volume": row["firm_log_volume"],
                "market_adj_close": row["market_adj_close"],
                "market_return": row["market_return"],
                "market_data_status": status,
                "failure_reason": reason,
            }
        )
    diag = {**base, "market_data_status": status, "failure_reason": reason, "event_trading_date": event_trading_date.strftime("%Y-%m-%d"), "available_event_rows": len(rows), "estimation_n": estimation_n}
    return rows, diag


def report_rows(events: List[Dict[str, str]], diags: List[Dict[str, object]], benchmark: str, benchmark_rows: int) -> List[Dict[str, object]]:
    with_ticker = [row for row in events if normalize_ticker(row.get("ticker", ""))]
    success = [row for row in diags if row.get("market_data_status") == "success"]
    insufficient = [row for row in diags if row.get("market_data_status") == "insufficient_data"]
    missing_ticker = [row for row in events if not normalize_ticker(row.get("ticker", ""))]
    return [
        {"metric": "total_firm_year_events", "value": len(events), "note": "Input scaffold rows"},
        {"metric": "events_with_ticker", "value": len(with_ticker), "note": "Rows with non-empty ticker"},
        {"metric": "events_with_sufficient_price_data", "value": len(success), "note": "At least 120 estimation returns and event days through +5"},
        {"metric": "events_with_insufficient_estimation_window", "value": len(insufficient), "note": "Downloaded but did not meet sufficiency rule"},
        {"metric": "events_with_missing_ticker", "value": len(missing_ticker), "note": "Not requested from yfinance"},
        {"metric": "events_with_market_benchmark_data", "value": len(events) if benchmark_rows else 0, "note": benchmark or "no benchmark downloaded"},
        {"metric": "market_benchmark", "value": benchmark, "note": "Priority: SPY, then ^GSPC"},
    ]


def main() -> int:
    events = read_csv(INPUT)
    dated = [pd.to_datetime(row.get("event_date", ""), errors="coerce") for row in events]
    valid_dates = [date for date in dated if pd.notna(date)]
    if not valid_dates:
        raise SystemExit("No valid event dates found")
    start = min(valid_dates) - timedelta(days=430)
    end = max(valid_dates) + timedelta(days=45)

    benchmark, market_data = select_benchmark(start, end)
    ticker_rows: Dict[str, pd.DataFrame] = {}
    for ticker in sorted({normalize_ticker(row.get("ticker", "")) for row in events if normalize_ticker(row.get("ticker", ""))}):
        try:
            ticker_rows[ticker] = download_history(ticker, start, end)
        except Exception:
            ticker_rows[ticker] = pd.DataFrame()
        time.sleep(0.05)

    all_rows: List[Dict[str, object]] = []
    diags: List[Dict[str, object]] = []
    for event in events:
        ticker = normalize_ticker(event.get("ticker", ""))
        if not ticker:
            diags.append({"event_id": event_id(event), "ticker": "", "company_name": event.get("company_name", ""), "filing_date": event.get("event_date", ""), "market_data_status": "failed", "failure_reason": "missing_ticker", "event_trading_date": "", "available_event_rows": 0})
            continue
        firm_data = ticker_rows.get(ticker, pd.DataFrame())
        if firm_data.empty or market_data.empty:
            diags.append({"event_id": event_id(event), "ticker": ticker, "company_name": event.get("company_name", ""), "filing_date": event.get("event_date", ""), "market_data_status": "failed", "failure_reason": "missing_firm_or_benchmark_data", "event_trading_date": "", "available_event_rows": 0})
            continue
        rows, diag = build_event_rows(event, firm_data, market_data, benchmark)
        all_rows.extend(rows)
        diags.append(diag)

    daily_fields = [
        "event_id", "ticker", "company_name", "target_report_year", "filing_date", "market_benchmark",
        "event_trading_date", "date", "relative_trading_day", "firm_adj_close", "firm_close", "firm_volume",
        "firm_return", "firm_log_volume", "market_adj_close", "market_return", "market_data_status", "failure_reason",
    ]
    write_csv(DAILY_OUT, all_rows, daily_fields)
    write_csv(REPORT_OUT, report_rows(events, diags, benchmark, len(market_data)), ["metric", "value", "note"])
    print(f"Daily market event panel: {DAILY_OUT.relative_to(REPO_ROOT)} ({len(all_rows)} rows)")
    print(f"Market data collection report: {REPORT_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
