#!/usr/bin/env python3
"""Build analysis-ready Fortune 2025 Top 100 10-K CSV inputs.

Priority 0
----------
Create CSV files that connect Fortune 2025 Top 100 firms to collected 10-K reports.

Priority 1
----------
Add SEC SIC industry metadata and NAICS-sector-compatible fields.

Notes on NAICS
--------------
SEC submissions metadata provides SIC, not NAICS. This script therefore:
1. fetches SEC SIC code and SIC description from submissions metadata where CIK exists;
2. maps SIC to an approximate NAICS sector using a transparent range-based mapping;
3. allows exact/manual NAICS override through config/fortune2025_top100_naics_overrides.csv.

Outputs
-------
- data/processed/fortune2025_top100_10k_report_linked_master.csv
- data/processed/fortune2025_top100_10k_report_linked_text_sample.csv
- data/processed/fortune2025_top100_10k_report_linked_with_industry.csv
- data/audit/fortune2025_top100_10k_report_linked_build_summary.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
FINAL_MANIFEST = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_final_manifest.csv"
AUDIT_CLASSIFICATION = REPO_ROOT / "data" / "audit" / "fortune2025_top100_10k_final_audit_classification.csv"
NAICS_OVERRIDE = REPO_ROOT / "config" / "fortune2025_top100_naics_overrides.csv"
MASTER_OUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_report_linked_master.csv"
TEXT_SAMPLE_OUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_report_linked_text_sample.csv"
INDUSTRY_OUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_report_linked_with_industry.csv"
SUMMARY_OUT = REPO_ROOT / "data" / "audit" / "fortune2025_top100_10k_report_linked_build_summary.csv"

SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
REQUEST_SLEEP_SECONDS = float(os.getenv("SEC_REQUEST_SLEEP_SECONDS", "0.50"))
USER_AGENT = os.getenv("SEC_USER_AGENT", "Seung Hyun Choi korea_uni research shch3653@g.skku.edu")

OUTPUT_BASE_COLUMNS = [
    "fortune_rank_2025",
    "company_name",
    "ticker",
    "cik",
    "cik_padded",
    "target_report_year",
    "download_status",
    "failure_reason",
    "form_type",
    "filing_date",
    "report_date",
    "accession_number",
    "primary_document",
    "sec_filing_url",
    "sec_document_url",
    "local_html_path",
    "local_text_path",
    "total_words",
    "ai_keyword_count",
    "ai_keyword_per_10k_words",
    "sample_role",
    "has_10k_text",
    "audit_category",
    "analysis_treatment",
]

INDUSTRY_COLUMNS = [
    "sec_sic_code",
    "sec_sic_description",
    "naics_code",
    "naics_description",
    "naics_sector_code",
    "naics_sector_name",
    "naics_source",
    "industry_enrichment_status",
    "industry_enrichment_reason",
]

# Transparent broad SIC-to-NAICS sector approximation. Exact firm-level NAICS should be added
# through overrides when needed.
SIC_TO_NAICS_SECTOR_RANGES: List[Tuple[int, int, str, str]] = [
    (100, 999, "11", "Agriculture, Forestry, Fishing and Hunting"),
    (1000, 1499, "21", "Mining, Quarrying, and Oil and Gas Extraction"),
    (1500, 1799, "23", "Construction"),
    (2000, 3999, "31-33", "Manufacturing"),
    (4000, 4999, "48-49", "Transportation and Warehousing"),
    (5000, 5199, "42", "Wholesale Trade"),
    (5200, 5999, "44-45", "Retail Trade"),
    (6000, 6799, "52", "Finance and Insurance"),
    (7000, 7999, "56", "Administrative and Support and Waste Management and Remediation Services"),
    (8000, 8099, "62", "Health Care and Social Assistance"),
    (8100, 8999, "54", "Professional, Scientific, and Technical Services"),
    (9000, 9999, "92", "Public Administration"),
]

# Better sector overrides for common SEC SICs that are ambiguous under broad SIC ranges.
SIC_EXACT_SECTOR_OVERRIDES: Dict[str, Tuple[str, str]] = {
    "4813": ("51", "Information"),  # Telephone communications
    "4822": ("51", "Information"),
    "4832": ("51", "Information"),
    "4833": ("51", "Information"),
    "4841": ("51", "Information"),
    "7370": ("51", "Information"),
    "7371": ("51", "Information"),
    "7372": ("51", "Information"),
    "7373": ("51", "Information"),
    "7374": ("51", "Information"),
    "7375": ("51", "Information"),
    "7379": ("51", "Information"),
    "7310": ("54", "Professional, Scientific, and Technical Services"),
    "7311": ("54", "Professional, Scientific, and Technical Services"),
    "8731": ("54", "Professional, Scientific, and Technical Services"),
    "8734": ("54", "Professional, Scientific, and Technical Services"),
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def sort_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            safe_int(str(row.get("fortune_rank_2025", "0"))),
            safe_int(str(row.get("target_report_year", "0"))),
        ),
    )


def row_key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (
        (row.get("cik_padded") or row.get("cik") or "").strip(),
        (row.get("ticker") or "").strip(),
        str(row.get("target_report_year") or "").strip(),
    )


def load_audit_classification() -> Dict[Tuple[str, str, str], Dict[str, str]]:
    if not AUDIT_CLASSIFICATION.exists():
        return {}
    rows = read_csv(AUDIT_CLASSIFICATION)
    out = {}
    for row in rows:
        out[row_key(row)] = row
    return out


def load_naics_overrides() -> Dict[Tuple[str, str], Dict[str, str]]:
    if not NAICS_OVERRIDE.exists():
        return {}
    rows = read_csv(NAICS_OVERRIDE)
    overrides: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in rows:
        cik = (row.get("cik_padded") or row.get("cik") or "").strip()
        ticker = (row.get("ticker") or "").strip()
        if cik or ticker:
            overrides[(cik, ticker)] = row
    return overrides


def sec_get_json(url: str) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_sec_industry(cik_padded: str) -> Tuple[str, str, str, str]:
    if not cik_padded:
        return "", "", "missing_cik", "Cannot fetch SEC submissions metadata because CIK is missing"
    try:
        url = f"{SEC_SUBMISSIONS_BASE}/CIK{cik_padded}.json"
        payload = sec_get_json(url)
        time.sleep(REQUEST_SLEEP_SECONDS)
        sic = str(payload.get("sic", "") or "").strip()
        sic_desc = str(payload.get("sicDescription", "") or "").strip()
        if sic:
            return sic, sic_desc, "success", ""
        return "", sic_desc, "missing_sic", "SEC submissions metadata exists but sic is blank"
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return "", "", "failed", f"{type(exc).__name__}: {exc}"


def sic_to_naics_sector(sic_code: str) -> Tuple[str, str, str]:
    sic = str(sic_code or "").strip()
    if not sic:
        return "", "", "none"
    if sic in SIC_EXACT_SECTOR_OVERRIDES:
        code, name = SIC_EXACT_SECTOR_OVERRIDES[sic]
        return code, name, "sic_exact_sector_override"
    sic_int = safe_int(sic, -1)
    for lo, hi, code, name in SIC_TO_NAICS_SECTOR_RANGES:
        if lo <= sic_int <= hi:
            return code, name, "sic_range_sector_crosswalk"
    return "", "", "unmapped_sic"


def apply_naics_override(row: Dict[str, Any], overrides: Dict[Tuple[str, str], Dict[str, str]]) -> bool:
    key = ((row.get("cik_padded") or row.get("cik") or "").strip(), (row.get("ticker") or "").strip())
    override = overrides.get(key)
    if not override:
        return False
    for col in ["naics_code", "naics_description", "naics_sector_code", "naics_sector_name"]:
        if override.get(col):
            row[col] = override[col]
    row["naics_source"] = override.get("naics_source") or "manual_override"
    return True


def build_linked_rows() -> List[Dict[str, Any]]:
    manifest = read_csv(FINAL_MANIFEST)
    audit_by_key = load_audit_classification()
    linked_rows: List[Dict[str, Any]] = []

    for row in manifest:
        out: Dict[str, Any] = {col: row.get(col, "") for col in OUTPUT_BASE_COLUMNS if col not in {"sample_role", "has_10k_text", "audit_category", "analysis_treatment"}}
        has_text = row.get("download_status") == "success" and bool(row.get("local_text_path"))
        out["has_10k_text"] = "TRUE" if has_text else "FALSE"
        out["sample_role"] = "primary_text_sample" if has_text else "missing_or_audit_row"
        audit = audit_by_key.get(row_key(row), {})
        out["audit_category"] = audit.get("audit_category", "")
        out["analysis_treatment"] = audit.get("analysis_treatment", "")
        linked_rows.append(out)

    return sort_rows(linked_rows)


def enrich_with_industry(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    overrides = load_naics_overrides()
    industry_cache: Dict[str, Tuple[str, str, str, str]] = {}
    enriched: List[Dict[str, Any]] = []

    for row in rows:
        cik_padded = str(row.get("cik_padded") or "").strip()
        if cik_padded not in industry_cache:
            industry_cache[cik_padded] = fetch_sec_industry(cik_padded) if cik_padded else ("", "", "missing_cik", "Cannot enrich industry because CIK is missing")
        sic_code, sic_desc, status, reason = industry_cache[cik_padded]
        naics_sector_code, naics_sector_name, naics_source = sic_to_naics_sector(sic_code)

        out = dict(row)
        out["sec_sic_code"] = sic_code
        out["sec_sic_description"] = sic_desc
        out["naics_code"] = ""
        out["naics_description"] = ""
        out["naics_sector_code"] = naics_sector_code
        out["naics_sector_name"] = naics_sector_name
        out["naics_source"] = naics_source
        overridden = apply_naics_override(out, overrides)
        if overridden:
            out["industry_enrichment_status"] = "success_manual_naics_override"
            out["industry_enrichment_reason"] = "NAICS fields provided by config/fortune2025_top100_naics_overrides.csv"
        else:
            out["industry_enrichment_status"] = status
            out["industry_enrichment_reason"] = reason
        enriched.append(out)
    return enriched


def build_summary(master_rows: List[Dict[str, Any]], text_rows: List[Dict[str, Any]], industry_rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    status_counts = Counter(str(row.get("download_status", "")) for row in master_rows)
    sample_counts = Counter(str(row.get("sample_role", "")) for row in master_rows)
    industry_status_counts = Counter(str(row.get("industry_enrichment_status", "")) for row in industry_rows)
    sector_counts = Counter(str(row.get("naics_sector_code", "")) for row in industry_rows if row.get("naics_sector_code"))
    return [
        {"metric": "master_rows", "value": str(len(master_rows)), "note": "Fortune 2025 Top 100 x 2023-2025 firm-year frame"},
        {"metric": "text_sample_rows", "value": str(len(text_rows)), "note": "Rows with successful 10-K text"},
        {"metric": "download_status_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(status_counts.items())), "note": "Final manifest download status"},
        {"metric": "sample_role_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(sample_counts.items())), "note": "Primary sample vs audit rows"},
        {"metric": "industry_enrichment_status_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(industry_status_counts.items())), "note": "SEC SIC retrieval and NAICS-sector mapping status"},
        {"metric": "naics_sector_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(sector_counts.items())), "note": "Firm-year counts by approximate NAICS sector code"},
        {"metric": "naics_warning", "value": "SEC provides SIC, not exact NAICS", "note": "Exact 6-digit NAICS requires manual override/crosswalk validation"},
    ]


def main(argv: Optional[List[str]] = None) -> int:
    linked_rows = build_linked_rows()
    text_rows = [row for row in linked_rows if row.get("has_10k_text") == "TRUE"]
    industry_rows = enrich_with_industry(linked_rows)

    write_csv(MASTER_OUT, linked_rows, OUTPUT_BASE_COLUMNS)
    write_csv(TEXT_SAMPLE_OUT, text_rows, OUTPUT_BASE_COLUMNS)
    write_csv(INDUSTRY_OUT, industry_rows, OUTPUT_BASE_COLUMNS + INDUSTRY_COLUMNS)
    write_csv(SUMMARY_OUT, build_summary(linked_rows, text_rows, industry_rows), ["metric", "value", "note"])

    print(f"Master linked CSV: {MASTER_OUT.relative_to(REPO_ROOT)} ({len(linked_rows)} rows)")
    print(f"Text sample CSV: {TEXT_SAMPLE_OUT.relative_to(REPO_ROOT)} ({len(text_rows)} rows)")
    print(f"Industry-enriched CSV: {INDUSTRY_OUT.relative_to(REPO_ROOT)} ({len(industry_rows)} rows)")
    print(f"Summary CSV: {SUMMARY_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
