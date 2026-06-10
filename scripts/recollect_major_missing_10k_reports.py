#!/usr/bin/env python3
"""Recollect major missing Fortune 2025 Top 100 10-K filings.

Scope
-----
Only the major listed/SEC-registered missing cases from the first Top 100 run:
9 firms, 15 firm-year rows.

Purpose
-------
The first full collection used only `filings.recent` from SEC submissions JSON.
For high-frequency filers, older 10-K filings may be outside that recent window.
This script searches both:

1. submissions.filings.recent
2. submissions.filings.files older filing JSON files

Outputs
-------
- data/processed/fortune2025_top100_major_missing_recollection_manifest.csv
- data/audit/fortune2025_top100_major_missing_recollection_audit.csv
- data/raw/sec_10k_html/major_missing/<TICKER>/<YEAR>_<TICKER>_10k.html
- data/processed/sec_10k_text/major_missing/<TICKER>/<YEAR>_<TICKER>_10k.txt
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "config" / "fortune2025_top100_missing_major_10k_seed.csv"
MANIFEST_PATH = REPO_ROOT / "data" / "processed" / "fortune2025_top100_major_missing_recollection_manifest.csv"
AUDIT_PATH = REPO_ROOT / "data" / "audit" / "fortune2025_top100_major_missing_recollection_audit.csv"
HTML_ROOT = REPO_ROOT / "data" / "raw" / "sec_10k_html" / "major_missing"
TEXT_ROOT = REPO_ROOT / "data" / "processed" / "sec_10k_text" / "major_missing"
SEC_BASE = "https://data.sec.gov/submissions"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
REQUEST_SLEEP_SECONDS = float(os.getenv("SEC_REQUEST_SLEEP_SECONDS", "0.50"))
USER_AGENT = os.getenv("SEC_USER_AGENT", "Seung Hyun Choi korea_uni research shch3653@g.skku.edu")

STRICT_AI_PATTERNS = [
    r"\bartificial intelligence\b",
    r"\bgenerative ai\b",
    r"\bgenai\b",
    r"\bmachine learning\b",
    r"\bdeep learning\b",
    r"\bnatural language processing\b",
    r"\bcomputer vision\b",
    r"\bneural network(?:s)?\b",
    r"\blarge language model(?:s)?\b",
    r"\bllm(?:s)?\b",
]
BROAD_AI_RELATED_PATTERNS = [
    r"\balgorithmic\b",
    r"\bautomation\b",
]
# Backward-compatible broad AI-related disclosure proxy. Strict terms should be
# preferred for main measurement when the pipeline is rerun with validation.
AI_PATTERNS = STRICT_AI_PATTERNS + BROAD_AI_RELATED_PATTERNS
STRICT_AI_REGEX = re.compile("|".join(STRICT_AI_PATTERNS), flags=re.IGNORECASE)
BROAD_AI_RELATED_REGEX = re.compile("|".join(BROAD_AI_RELATED_PATTERNS), flags=re.IGNORECASE)
AI_REGEX = re.compile("|".join(AI_PATTERNS), flags=re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[\s\S]*?</\1>", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9\-']*\b")


@dataclass
class MissingTarget:
    fortune_rank_2025: str
    company_name: str
    ticker: str
    cik: str
    cik_padded: str
    target_report_year: str
    original_status: str
    original_failure_reason: str
    notes: str


@dataclass
class RecollectionRow:
    fortune_rank_2025: str
    company_name: str
    ticker: str
    cik: str
    cik_padded: str
    target_report_year: int
    form_type: str
    filing_date: str
    report_date: str
    accession_number: str
    primary_document: str
    filing_source: str
    sec_filing_url: str
    sec_document_url: str
    local_html_path: str
    local_text_path: str
    recollection_status: str
    failure_reason: str
    total_words: int
    ai_keyword_count: int
    ai_keyword_per_10k_words: float


def ensure_dirs() -> None:
    for path in [MANIFEST_PATH.parent, AUDIT_PATH.parent, HTML_ROOT, TEXT_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def read_seed() -> List[MissingTarget]:
    with SEED_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [MissingTarget(**row) for row in csv.DictReader(f)]


def sec_get_json(url: str) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sec_get_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def filings_from_columns(payload: Dict[str, Any], source: str) -> List[Dict[str, str]]:
    forms = payload.get("form", [])
    filings: List[Dict[str, str]] = []
    for idx, form in enumerate(forms):
        filings.append({
            "form": str(form),
            "filingDate": str(payload.get("filingDate", [""])[idx]),
            "reportDate": str(payload.get("reportDate", [""])[idx]),
            "accessionNumber": str(payload.get("accessionNumber", [""])[idx]),
            "primaryDocument": str(payload.get("primaryDocument", [""])[idx]),
            "source": source,
        })
    return filings


def collect_all_filings(cik_padded: str) -> List[Dict[str, str]]:
    submissions_url = f"{SEC_BASE}/CIK{cik_padded}.json"
    submissions = sec_get_json(submissions_url)
    time.sleep(REQUEST_SLEEP_SECONDS)

    filings: List[Dict[str, str]] = []
    recent = submissions.get("filings", {}).get("recent", {})
    filings.extend(filings_from_columns(recent, "recent"))

    for file_item in submissions.get("filings", {}).get("files", []):
        name = file_item.get("name")
        if not name:
            continue
        file_url = f"{SEC_BASE}/{name}"
        try:
            older = sec_get_json(file_url)
            time.sleep(REQUEST_SLEEP_SECONDS)
            filings.extend(filings_from_columns(older, name))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"WARN older filings fetch failed for {file_url}: {type(exc).__name__}: {exc}")
            continue
    return filings


def select_10k_for_report_year(filings: Iterable[Dict[str, str]], target_year: int) -> Optional[Dict[str, str]]:
    candidates = []
    for filing in filings:
        if filing.get("form") != "10-K":
            continue
        report_date = filing.get("reportDate") or ""
        if report_date[:4] == str(target_year):
            candidates.append(filing)
    if not candidates:
        return None
    return sorted(candidates, key=lambda x: x.get("filingDate", ""), reverse=True)[0]


def archives_urls(cik: str, accession: str, primary_document: str) -> Tuple[str, str]:
    cik_no_zero = str(int(cik))
    accession_no_dash = accession.replace("-", "")
    filing_url = f"{SEC_ARCHIVES_BASE}/{cik_no_zero}/{accession_no_dash}/"
    document_url = f"{filing_url}{primary_document}"
    return filing_url, document_url


def clean_html_to_text(raw_html: str) -> str:
    no_script = SCRIPT_STYLE_RE.sub(" ", raw_html)
    no_tags = TAG_RE.sub(" ", no_script)
    unescaped = html.unescape(no_tags)
    return SPACE_RE.sub(" ", unescaped).strip()


def compute_text_metrics(text: str) -> Tuple[int, int, float]:
    total_words = len(WORD_RE.findall(text))
    ai_count = len(AI_REGEX.findall(text))
    per_10k = (ai_count / total_words * 10000) if total_words else 0.0
    return total_words, ai_count, round(per_10k, 6)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def recollect() -> int:
    ensure_dirs()
    targets = read_seed()
    filings_cache: Dict[str, List[Dict[str, str]]] = {}
    rows: List[RecollectionRow] = []

    for target in targets:
        target_year = int(target.target_report_year)
        try:
            if target.cik_padded not in filings_cache:
                filings_cache[target.cik_padded] = collect_all_filings(target.cik_padded)
            selected = select_10k_for_report_year(filings_cache[target.cik_padded], target_year)
        except Exception as exc:
            selected = None
            fetch_failure = f"filings_fetch_failed: {type(exc).__name__}: {exc}"
        else:
            fetch_failure = ""

        if not selected:
            rows.append(RecollectionRow(
                fortune_rank_2025=target.fortune_rank_2025,
                company_name=target.company_name,
                ticker=target.ticker,
                cik=target.cik,
                cik_padded=target.cik_padded,
                target_report_year=target_year,
                form_type="10-K",
                filing_date="",
                report_date="",
                accession_number="",
                primary_document="",
                filing_source="",
                sec_filing_url="",
                sec_document_url="",
                local_html_path="",
                local_text_path="",
                recollection_status="missing",
                failure_reason=fetch_failure or "no_10k_for_target_report_year_after_recent_and_files_lookup",
                total_words=0,
                ai_keyword_count=0,
                ai_keyword_per_10k_words=0.0,
            ))
            continue

        filing_url, document_url = archives_urls(target.cik, selected["accessionNumber"], selected["primaryDocument"])
        html_dir = HTML_ROOT / target.ticker
        text_dir = TEXT_ROOT / target.ticker
        html_dir.mkdir(parents=True, exist_ok=True)
        text_dir.mkdir(parents=True, exist_ok=True)
        html_path = html_dir / f"{target_year}_{target.ticker}_10k.html"
        text_path = text_dir / f"{target_year}_{target.ticker}_10k.txt"

        try:
            raw = sec_get_bytes(document_url)
            time.sleep(REQUEST_SLEEP_SECONDS)
            raw_html = raw.decode("utf-8", errors="replace")
            html_path.write_text(raw_html, encoding="utf-8")
            clean_text = clean_html_to_text(raw_html)
            text_path.write_text(clean_text, encoding="utf-8")
            total_words, ai_count, per_10k = compute_text_metrics(clean_text)
            status = "success"
            failure = ""
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            total_words, ai_count, per_10k = 0, 0, 0.0
            status = "failed"
            failure = f"document_download_or_parse_failed: {type(exc).__name__}: {exc}"

        rows.append(RecollectionRow(
            fortune_rank_2025=target.fortune_rank_2025,
            company_name=target.company_name,
            ticker=target.ticker,
            cik=target.cik,
            cik_padded=target.cik_padded,
            target_report_year=target_year,
            form_type=selected.get("form", "10-K"),
            filing_date=selected.get("filingDate", ""),
            report_date=selected.get("reportDate", ""),
            accession_number=selected.get("accessionNumber", ""),
            primary_document=selected.get("primaryDocument", ""),
            filing_source=selected.get("source", ""),
            sec_filing_url=filing_url,
            sec_document_url=document_url,
            local_html_path=str(html_path.relative_to(REPO_ROOT)) if html_path.exists() else "",
            local_text_path=str(text_path.relative_to(REPO_ROOT)) if text_path.exists() else "",
            recollection_status=status,
            failure_reason=failure,
            total_words=total_words,
            ai_keyword_count=ai_count,
            ai_keyword_per_10k_words=per_10k,
        ))

    dict_rows = [asdict(row) for row in rows]
    fields = list(asdict(rows[0]).keys()) if rows else []
    write_csv(MANIFEST_PATH, dict_rows, fields)
    audit_rows = [row for row in dict_rows if row.get("recollection_status") != "success"]
    write_csv(AUDIT_PATH, audit_rows, fields)

    print(f"Targets: {len(targets)}")
    print(f"Success: {sum(1 for row in dict_rows if row['recollection_status'] == 'success')}")
    print(f"Non-success: {len(audit_rows)}")
    print(f"Manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"Audit: {AUDIT_PATH.relative_to(REPO_ROOT)}")
    return 0 if len(dict_rows) == len(targets) else 1


if __name__ == "__main__":
    sys.exit(recollect())
