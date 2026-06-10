#!/usr/bin/env python3
"""Materialize 10-K text files referenced by a linked report CSV.

Problem
-------
The linked analysis CSV stores local_text_path values, but large 10-K TXT files
may not be committed to the repository checkout. They may exist only in prior
GitHub Actions artifacts. Topic-model workflows therefore fail when they check
local_text_path files.

Solution
--------
For every row in the linked CSV:
- if local_text_path already exists, keep it;
- otherwise download sec_document_url;
- convert HTML/XML to plain text;
- write the result to local_text_path.

This script is intended to run inside GitHub Actions before topic optimization
or topic modeling. It does not commit TXT files by default. The TXT files are
materialized only in the workflow workspace.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_CSV = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_report_linked_text_sample.csv"
SUMMARY_OUT = REPO_ROOT / "data" / "audit" / "10k_ai_topics" / "text_materialization_summary.csv"
REQUEST_SLEEP_SECONDS = float(os.getenv("SEC_REQUEST_SLEEP_SECONDS", "0.50"))
USER_AGENT = os.getenv("SEC_USER_AGENT", "Seung Hyun Choi korea_uni research shch3653@g.skku.edu")

SCRIPT_STYLE_RE = re.compile(r"<(script|style)[\s\S]*?</\1>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9\-']*\b")


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sec_get_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=90) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def clean_html_to_text(raw_html: str) -> str:
    no_script = SCRIPT_STYLE_RE.sub(" ", raw_html)
    no_tags = TAG_RE.sub(" ", no_script)
    unescaped = html.unescape(no_tags)
    return SPACE_RE.sub(" ", unescaped).strip()


def materialize(input_csv: Path, max_docs: int = 0) -> List[Dict[str, object]]:
    rows = read_csv(input_csv)
    summary_rows: List[Dict[str, object]] = []
    processed = 0

    for idx, row in enumerate(rows, start=1):
        local_text_path = row.get("local_text_path", "").strip()
        sec_document_url = row.get("sec_document_url", "").strip()
        ticker = row.get("ticker", "")
        year = row.get("target_report_year", "")

        if not local_text_path:
            summary_rows.append({
                "row_number": idx,
                "ticker": ticker,
                "target_report_year": year,
                "status": "skipped",
                "reason": "local_text_path_blank",
                "local_text_path": local_text_path,
                "sec_document_url": sec_document_url,
                "word_count": 0,
            })
            continue

        out_path = REPO_ROOT / local_text_path
        if out_path.exists() and out_path.stat().st_size > 0:
            word_count = len(WORD_RE.findall(out_path.read_text(encoding="utf-8", errors="replace")))
            summary_rows.append({
                "row_number": idx,
                "ticker": ticker,
                "target_report_year": year,
                "status": "already_exists",
                "reason": "",
                "local_text_path": local_text_path,
                "sec_document_url": sec_document_url,
                "word_count": word_count,
            })
            continue

        if not sec_document_url:
            summary_rows.append({
                "row_number": idx,
                "ticker": ticker,
                "target_report_year": year,
                "status": "failed",
                "reason": "sec_document_url_blank",
                "local_text_path": local_text_path,
                "sec_document_url": sec_document_url,
                "word_count": 0,
            })
            continue

        if max_docs and processed >= max_docs:
            summary_rows.append({
                "row_number": idx,
                "ticker": ticker,
                "target_report_year": year,
                "status": "deferred",
                "reason": f"max_docs_reached:{max_docs}",
                "local_text_path": local_text_path,
                "sec_document_url": sec_document_url,
                "word_count": 0,
            })
            continue

        try:
            raw_html = sec_get_text(sec_document_url)
            time.sleep(REQUEST_SLEEP_SECONDS)
            text = clean_html_to_text(raw_html)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")
            word_count = len(WORD_RE.findall(text))
            processed += 1
            summary_rows.append({
                "row_number": idx,
                "ticker": ticker,
                "target_report_year": year,
                "status": "materialized",
                "reason": "downloaded_from_sec_document_url",
                "local_text_path": local_text_path,
                "sec_document_url": sec_document_url,
                "word_count": word_count,
            })
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            summary_rows.append({
                "row_number": idx,
                "ticker": ticker,
                "target_report_year": year,
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
                "local_text_path": local_text_path,
                "sec_document_url": sec_document_url,
                "word_count": 0,
            })

    return summary_rows


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize missing 10-K text files from SEC document URLs.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--summary-out", type=Path, default=SUMMARY_OUT)
    parser.add_argument("--max-docs", type=int, default=0, help="0 means no cap")
    args = parser.parse_args(argv)

    rows = materialize(args.input_csv, max_docs=args.max_docs)
    write_csv(args.summary_out, rows, ["row_number", "ticker", "target_report_year", "status", "reason", "local_text_path", "sec_document_url", "word_count"])

    counts: Dict[str, int] = {}
    for row in rows:
        counts[str(row["status"])] = counts.get(str(row["status"]), 0) + 1
    failures = counts.get("failed", 0)
    print(f"Materialization status counts: {counts}")
    print(f"Summary: {args.summary_out.relative_to(REPO_ROOT) if args.summary_out.is_absolute() else args.summary_out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
