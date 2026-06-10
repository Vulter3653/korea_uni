#!/usr/bin/env python3
"""Build non-destructive validation summaries for 10-K AI communication measures.

This script does not collect new data. It reads existing generated CSV files and,
when available, writes compact validation outputs under data/derived/validation/.
The outputs are intended to support measurement validation, not causal claims.

Prepared checks
---------------
1. Strict vs broad keyword classification in existing AI mention windows.
2. Standalone AI-only window audit sample for manual false-positive review.
3. Missing 10-K rows audit by year and approximate sector.

The script does not claim that manual validation is complete. It only prepares
reviewable files when source rows are present.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_IN = REPO_ROOT / "data" / "processed" / "10k_ai_topics" / "ai_mention_windows.csv"
MASTER_IN = REPO_ROOT / "data" / "processed" / "fortune2025_top100_final_ai_analysis_master.csv"
OUT_DIR = REPO_ROOT / "data" / "derived" / "validation"
SUMMARY_OUT = OUT_DIR / "measurement_validation_summary.csv"
STANDALONE_SAMPLE_OUT = OUT_DIR / "standalone_ai_window_audit_sample.csv"
MISSING_AUDIT_OUT = OUT_DIR / "missing_10k_rows_by_year_sector.csv"

STRICT_AI_TERMS = [
    r"artificial intelligence",
    r"generative ai",
    r"genai",
    r"machine learning",
    r"deep learning",
    r"natural language processing",
    r"nlp",
    r"computer vision",
    r"neural network(?:s)?",
    r"large language model(?:s)?",
    r"llm(?:s)?",
    r"ai",
]
BROAD_AI_RELATED_TERMS = [r"predictive analytics", r"algorithmic", r"automation", r"automated decision"]
STRICT_RE = re.compile(r"\b(" + "|".join(STRICT_AI_TERMS) + r")\b", re.IGNORECASE)
BROAD_RE = re.compile(r"\b(" + "|".join(BROAD_AI_RELATED_TERMS) + r")\b", re.IGNORECASE)


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def classify_window(row: Dict[str, str]) -> str:
    text = row.get("window_text", "")
    strict = bool(STRICT_RE.search(text))
    broad = bool(BROAD_RE.search(text))
    if strict and broad:
        return "strict_and_broad"
    if strict:
        return "strict_only"
    if broad:
        return "broad_only"
    return "no_keyword_detected"


def is_standalone_ai_only(row: Dict[str, str]) -> bool:
    text = row.get("window_text", "")
    strict_terms = [m.group(0).lower() for m in STRICT_RE.finditer(text)]
    return bool(strict_terms) and all(term == "ai" for term in strict_terms) and not BROAD_RE.search(text)


def build_window_validation(windows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    counts = Counter(classify_window(row) for row in windows)
    standalone_count = sum(1 for row in windows if is_standalone_ai_only(row))
    return [
        {"metric": "source_windows", "value": len(windows), "note": str(WINDOWS_IN.relative_to(REPO_ROOT))},
        {"metric": "strict_only_windows", "value": counts.get("strict_only", 0), "note": "Contains strict AI terms only"},
        {"metric": "strict_and_broad_windows", "value": counts.get("strict_and_broad", 0), "note": "Contains both strict and broad AI-related terms"},
        {"metric": "broad_only_windows", "value": counts.get("broad_only", 0), "note": "Broad AI-related terms only; use for sensitivity checks"},
        {"metric": "standalone_ai_only_windows", "value": standalone_count, "note": "Prepared for manual false-positive review; validation not completed by this script"},
    ]


def build_standalone_sample(windows: List[Dict[str, str]], limit: int = 50) -> List[Dict[str, str]]:
    sample = [row for row in windows if is_standalone_ai_only(row)][:limit]
    for row in sample:
        row["manual_review_status"] = "not_reviewed"
        row["manual_review_note"] = ""
    return sample


def build_missing_audit(master_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    grouped: Counter = Counter()
    for row in master_rows:
        if row.get("download_status") == "success":
            continue
        key = (
            row.get("target_report_year", ""),
            row.get("naics_sector_code") or "Unclassified",
            row.get("naics_sector_name") or "Unclassified",
            row.get("download_status", ""),
        )
        grouped[key] += 1
    return [
        {
            "target_report_year": year,
            "naics_sector_code": code,
            "naics_sector_name": name,
            "download_status": status,
            "non_success_rows": count,
            "note": "Approximate sector from downstream enrichment; not fully verified firm-level NAICS",
        }
        for (year, code, name, status), count in sorted(grouped.items())
    ]


def main() -> int:
    windows = read_csv(WINDOWS_IN)
    master_rows = read_csv(MASTER_IN)
    if not windows and not master_rows:
        raise SystemExit("No validation source files found")

    summary_rows = []
    if windows:
        summary_rows.extend(build_window_validation(windows))
        standalone_sample = build_standalone_sample(windows)
        if standalone_sample:
            write_csv(STANDALONE_SAMPLE_OUT, standalone_sample, list(standalone_sample[0].keys()))
    else:
        summary_rows.append({"metric": "source_windows", "value": 0, "note": f"Missing {WINDOWS_IN.relative_to(REPO_ROOT)}"})

    if master_rows:
        missing_rows = build_missing_audit(master_rows)
        if missing_rows:
            write_csv(MISSING_AUDIT_OUT, missing_rows, missing_rows[0].keys())
        summary_rows.append({"metric": "master_rows_checked", "value": len(master_rows), "note": str(MASTER_IN.relative_to(REPO_ROOT))})
    else:
        summary_rows.append({"metric": "master_rows_checked", "value": 0, "note": f"Missing {MASTER_IN.relative_to(REPO_ROOT)}"})

    write_csv(SUMMARY_OUT, summary_rows, ["metric", "value", "note"])
    print(f"Validation summary: {SUMMARY_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
