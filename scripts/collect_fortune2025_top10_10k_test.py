#!/usr/bin/env python3
"""Smoke-test collector for Fortune 2025 Top 10 10-K filings.

Purpose
-------
Collect a small, auditable SEC 10-K corpus before scaling to the full
Fortune 2025 Top 100 sample.

Target sample
-------------
- Fortune 2025 Top 10 firms
- Target report years: 2023, 2024, 2025
- Expected manifest rows: 10 firms x 3 years = 30

Outputs
-------
- data/processed/fortune2025_top10_10k_test_manifest.csv
- data/audit/fortune2025_top10_10k_test_audit.csv
- data/raw/sec_10k_html/test_top10/<TICKER>/<YEAR>_<TICKER>_10k.html
- data/processed/sec_10k_text/test_top10/<TICKER>/<YEAR>_<TICKER>_10k.txt

Notes
-----
SEC guidance requires a descriptive User-Agent. Set SEC_USER_AGENT before
running, for example:

    export SEC_USER_AGENT="Seung Hyun Choi korea_uni research shch3653@g.skku.edu"

The script uses reportDate/periodOfReport as the target report-year basis.
This is intentional because a fiscal-year 2025 10-K may be filed in 2026.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = REPO_ROOT / "config" / "fortune2025_top10_10k_test_seed.csv"
MANIFEST_PATH = REPO_ROOT / "data" / "processed" / "fortune2025_top10_10k_test_manifest.csv"
AUDIT_PATH = REPO_ROOT / "data" / "audit" / "fortune2025_top10_10k_test_audit.csv"
HTML_ROOT = REPO_ROOT / "data" / "raw" / "sec_10k_html" / "test_top10"
TEXT_ROOT = REPO_ROOT / "data" / "processed" / "sec_10k_text" / "test_top10"
TARGET_YEARS = [2023, 2024, 2025]
SEC_BASE = "https://data.sec.gov/submissions"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
REQUEST_SLEEP_SECONDS = float(os.getenv("SEC_REQUEST_SLEEP_SECONDS", "0.25"))
USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "Seung Hyun Choi korea_uni research shch3653@g.skku.edu",
)

AI_PATTERNS = [
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
    r"\balgorithmic\b",
    r"\bautomation\b",
]
AI_REGEX = re.compile("|".join(AI_PATTERNS), flags=re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[\s\S]*?</\1>", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9\-']*\b")


@dataclass
class SeedCompany:
    fortune_rank_2025: str
    company_name: str
    ticker: str
    cik: str
    cik_padded: str
    sec_title: str
    notes: str


@dataclass
class ManifestRow:
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
    sec_filing_url: str
    sec_document_url: str
    local_html_path: str
    local_text_path: str
    download_status: str
    failure_reason: str
    total_words: int
    ai_keyword_count: int
    ai_keyword_per_10k_words: float


def ensure_dirs() -> None:
    for path in [MANIFEST_PATH.parent, AUDIT_PATH.parent, HTML_ROOT, TEXT_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def read_seed(path: Path) -> List[SeedCompany]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [SeedCompany(**row) for row in reader]


def sec_get_json(url: str) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sec_get_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def normalize_accession(accession: str) -> str:
    return accession.replace("-", "")


def archives_urls(cik: str, accession: str, primary_document: str) -> Tuple[str, str]:
    cik_no_zero = str(int(cik))
    accession_no_dash = normalize_accession(accession)
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


def recent_filings(submissions: Dict[str, Any]) -> List[Dict[str, str]]:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    filings: List[Dict[str, str]] = []
    for idx, form in enumerate(forms):
        filings.append({
            "form": str(form),
            "filingDate": str(recent.get("filingDate", [""])[idx]),
            "reportDate": str(recent.get("reportDate", [""])[idx]),
            "accessionNumber": str(recent.get("accessionNumber", [""])[idx]),
            "primaryDocument": str(recent.get("primaryDocument", [""])[idx]),
        })
    return filings


def select_10k_for_year(filings: Iterable[Dict[str, str]], target_year: int) -> Optional[Dict[str, str]]:
    candidates = []
    for filing in filings:
        if filing.get("form") != "10-K":
            continue
        report_date = filing.get("reportDate") or ""
        filing_date = filing.get("filingDate") or ""
        report_year = report_date[:4]
        if report_year == str(target_year):
            candidates.append(filing)
        # Fallback: if reportDate is missing, use filingDate only as a weak fallback.
        elif not report_year and filing_date[:4] == str(target_year):
            candidates.append(filing)
    if not candidates:
        return None
    # If multiple exist, prefer the latest filing date for the same report year.
    return sorted(candidates, key=lambda x: x.get("filingDate", ""), reverse=True)[0]


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def collect() -> int:
    ensure_dirs()
    seed = read_seed(SEED_PATH)
    manifest_rows: List[ManifestRow] = []

    for company in seed:
        submissions_url = f"{SEC_BASE}/CIK{company.cik_padded}.json"
        try:
            submissions = sec_get_json(submissions_url)
            time.sleep(REQUEST_SLEEP_SECONDS)
            filings = recent_filings(submissions)
            submissions_status = "success"
            submissions_failure = ""
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            filings = []
            submissions_status = "failed"
            submissions_failure = f"submissions_fetch_failed: {type(exc).__name__}: {exc}"

        for target_year in TARGET_YEARS:
            selected = select_10k_for_year(filings, target_year)
            base_kwargs = dict(
                fortune_rank_2025=company.fortune_rank_2025,
                company_name=company.company_name,
                ticker=company.ticker,
                cik=company.cik,
                cik_padded=company.cik_padded,
                target_report_year=target_year,
            )

            if submissions_status != "success":
                manifest_rows.append(ManifestRow(
                    **base_kwargs,
                    form_type="",
                    filing_date="",
                    report_date="",
                    accession_number="",
                    primary_document="",
                    sec_filing_url="",
                    sec_document_url=submissions_url,
                    local_html_path="",
                    local_text_path="",
                    download_status="failed",
                    failure_reason=submissions_failure,
                    total_words=0,
                    ai_keyword_count=0,
                    ai_keyword_per_10k_words=0.0,
                ))
                continue

            if not selected:
                manifest_rows.append(ManifestRow(
                    **base_kwargs,
                    form_type="10-K",
                    filing_date="",
                    report_date="",
                    accession_number="",
                    primary_document="",
                    sec_filing_url="",
                    sec_document_url="",
                    local_html_path="",
                    local_text_path="",
                    download_status="missing",
                    failure_reason="no_10k_for_target_report_year",
                    total_words=0,
                    ai_keyword_count=0,
                    ai_keyword_per_10k_words=0.0,
                ))
                continue

            accession = selected.get("accessionNumber", "")
            primary_document = selected.get("primaryDocument", "")
            filing_url, document_url = archives_urls(company.cik, accession, primary_document)
            html_dir = HTML_ROOT / company.ticker
            text_dir = TEXT_ROOT / company.ticker
            html_dir.mkdir(parents=True, exist_ok=True)
            text_dir.mkdir(parents=True, exist_ok=True)
            html_path = html_dir / f"{target_year}_{company.ticker}_10k.html"
            text_path = text_dir / f"{target_year}_{company.ticker}_10k.txt"

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

            manifest_rows.append(ManifestRow(
                **base_kwargs,
                form_type=selected.get("form", "10-K"),
                filing_date=selected.get("filingDate", ""),
                report_date=selected.get("reportDate", ""),
                accession_number=accession,
                primary_document=primary_document,
                sec_filing_url=filing_url,
                sec_document_url=document_url,
                local_html_path=str(html_path.relative_to(REPO_ROOT)) if html_path.exists() else "",
                local_text_path=str(text_path.relative_to(REPO_ROOT)) if text_path.exists() else "",
                download_status=status,
                failure_reason=failure,
                total_words=total_words,
                ai_keyword_count=ai_count,
                ai_keyword_per_10k_words=per_10k,
            ))

    rows = [asdict(row) for row in manifest_rows]
    fields = list(asdict(manifest_rows[0]).keys()) if manifest_rows else []
    write_csv(MANIFEST_PATH, rows, fields)
    audit_rows = [row for row in rows if row.get("download_status") != "success"]
    write_csv(AUDIT_PATH, audit_rows, fields)

    expected = len(seed) * len(TARGET_YEARS)
    success = sum(1 for row in rows if row.get("download_status") == "success")
    failed = expected - success
    print(f"Expected rows: {expected}")
    print(f"Success rows: {success}")
    print(f"Failed/missing rows: {failed}")
    print(f"Manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"Audit: {AUDIT_PATH.relative_to(REPO_ROOT)}")
    return 0 if rows and len(rows) == expected else 1


if __name__ == "__main__":
    sys.exit(collect())
