#!/usr/bin/env python3
"""Update Top 100 combined manifest with major-missing recollection results.

Inputs
------
1. data/processed/fortune2025_top100_10k_run_<SOURCE_RUN_ID>_combined_manifest.csv
2. data/audit/fortune2025_top100_10k_run_<SOURCE_RUN_ID>_combined_audit.csv
3. data/processed/fortune2025_top100_major_missing_recollection_manifest.csv
4. data/audit/fortune2025_top100_major_missing_recollection_audit.csv

Outputs
-------
1. data/processed/fortune2025_top100_10k_final_manifest.csv
2. data/audit/fortune2025_top100_10k_final_audit.csv
3. data/audit/fortune2025_top100_10k_final_update_summary.csv

Logic
-----
- Keep the original 300-row combined manifest structure.
- For recollection success rows, replace the matching original missing row.
- For recollection missing rows, keep the row as missing but update failure_reason
  to the recollection failure_reason.
- Final audit is all final manifest rows where download_status != success.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_RUN_ID = "27272856688"

FINAL_MANIFEST_PATH = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_final_manifest.csv"
FINAL_AUDIT_PATH = REPO_ROOT / "data" / "audit" / "fortune2025_top100_10k_final_audit.csv"
FINAL_SUMMARY_PATH = REPO_ROOT / "data" / "audit" / "fortune2025_top100_10k_final_update_summary.csv"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def key(row: Dict[str, str]) -> Tuple[str, str, str]:
    cik = (row.get("cik_padded") or row.get("cik") or "").strip()
    ticker = (row.get("ticker") or "").strip()
    year = str(row.get("target_report_year") or "").strip()
    return cik, ticker, year


def sort_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    def to_int(value: str, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    return sorted(
        rows,
        key=lambda row: (
            to_int(row.get("collection_chunk_id", "0")),
            to_int(row.get("fortune_rank_2025", "0")),
            to_int(row.get("target_report_year", "0")),
        ),
    )


def update_row_from_recollection(base: Dict[str, str], recollect: Dict[str, str]) -> Dict[str, str]:
    updated = dict(base)
    status = recollect.get("recollection_status", "")

    mapping = {
        "form_type": "form_type",
        "filing_date": "filing_date",
        "report_date": "report_date",
        "accession_number": "accession_number",
        "primary_document": "primary_document",
        "sec_filing_url": "sec_filing_url",
        "sec_document_url": "sec_document_url",
        "local_html_path": "local_html_path",
        "local_text_path": "local_text_path",
        "total_words": "total_words",
        "ai_keyword_count": "ai_keyword_count",
        "ai_keyword_per_10k_words": "ai_keyword_per_10k_words",
    }

    for base_col, recollect_col in mapping.items():
        if base_col in updated and recollect_col in recollect:
            updated[base_col] = recollect.get(recollect_col, "")

    if status == "success":
        updated["download_status"] = "success"
        updated["failure_reason"] = ""
    else:
        updated["download_status"] = status or updated.get("download_status", "missing")
        updated["failure_reason"] = recollect.get("failure_reason", updated.get("failure_reason", ""))

    return updated


def make_summary(
    source_run_id: str,
    original_manifest: List[Dict[str, str]],
    original_audit: List[Dict[str, str]],
    recollection_manifest: List[Dict[str, str]],
    final_manifest: List[Dict[str, str]],
    final_audit: List[Dict[str, str]],
    replaced_success: int,
    updated_missing: int,
) -> List[Dict[str, str]]:
    original_status = Counter(row.get("download_status", "") for row in original_manifest)
    recollect_status = Counter(row.get("recollection_status", "") for row in recollection_manifest)
    final_status = Counter(row.get("download_status", "") for row in final_manifest)

    rows = [
        {
            "metric": "source_run_id",
            "value": source_run_id,
            "note": "Original Top 100 collection run used for combined manifest/audit",
        },
        {
            "metric": "original_manifest_rows",
            "value": str(len(original_manifest)),
            "note": "; ".join(f"{k}={v}" for k, v in sorted(original_status.items())),
        },
        {
            "metric": "original_audit_rows",
            "value": str(len(original_audit)),
            "note": "Rows where original download_status != success",
        },
        {
            "metric": "recollection_rows",
            "value": str(len(recollection_manifest)),
            "note": "; ".join(f"{k}={v}" for k, v in sorted(recollect_status.items())),
        },
        {
            "metric": "recollection_success_rows_applied",
            "value": str(replaced_success),
            "note": "Original missing rows replaced with recollection success rows",
        },
        {
            "metric": "recollection_missing_rows_retained",
            "value": str(updated_missing),
            "note": "Still missing after recent+files lookup; failure_reason updated",
        },
        {
            "metric": "final_manifest_rows",
            "value": str(len(final_manifest)),
            "note": "; ".join(f"{k}={v}" for k, v in sorted(final_status.items())),
        },
        {
            "metric": "final_audit_rows",
            "value": str(len(final_audit)),
            "note": "Rows where final download_status != success",
        },
        {
            "metric": "final_success_rows",
            "value": str(final_status.get("success", 0)),
            "note": "Final collected 10-K firm-year rows",
        },
        {
            "metric": "final_manifest_sha256",
            "value": sha256_file(FINAL_MANIFEST_PATH),
            "note": str(FINAL_MANIFEST_PATH.relative_to(REPO_ROOT)),
        },
        {
            "metric": "final_audit_sha256",
            "value": sha256_file(FINAL_AUDIT_PATH),
            "note": str(FINAL_AUDIT_PATH.relative_to(REPO_ROOT)),
        },
    ]
    return rows


def update_manifest(source_run_id: str) -> None:
    combined_manifest_path = REPO_ROOT / "data" / "processed" / f"fortune2025_top100_10k_run_{source_run_id}_combined_manifest.csv"
    combined_audit_path = REPO_ROOT / "data" / "audit" / f"fortune2025_top100_10k_run_{source_run_id}_combined_audit.csv"
    recollection_manifest_path = REPO_ROOT / "data" / "processed" / "fortune2025_top100_major_missing_recollection_manifest.csv"

    original_manifest = read_csv(combined_manifest_path)
    original_audit = read_csv(combined_audit_path)
    recollection_manifest = read_csv(recollection_manifest_path)
    recollection_by_key = {key(row): row for row in recollection_manifest}

    final_rows: List[Dict[str, str]] = []
    replaced_success = 0
    updated_missing = 0

    for row in original_manifest:
        row_key = key(row)
        recollect = recollection_by_key.get(row_key)
        if recollect:
            updated = update_row_from_recollection(row, recollect)
            if recollect.get("recollection_status") == "success":
                replaced_success += 1
            else:
                updated_missing += 1
            final_rows.append(updated)
        else:
            final_rows.append(dict(row))

    final_rows = sort_rows(final_rows)
    if len(final_rows) != 300:
        raise ValueError(f"Expected 300 final manifest rows, found {len(final_rows)}")

    fieldnames = list(original_manifest[0].keys())
    final_audit = [row for row in final_rows if row.get("download_status") != "success"]

    write_csv(FINAL_MANIFEST_PATH, final_rows, fieldnames)
    write_csv(FINAL_AUDIT_PATH, final_audit, fieldnames)

    summary_rows = make_summary(
        source_run_id=source_run_id,
        original_manifest=original_manifest,
        original_audit=original_audit,
        recollection_manifest=recollection_manifest,
        final_manifest=final_rows,
        final_audit=final_audit,
        replaced_success=replaced_success,
        updated_missing=updated_missing,
    )
    write_csv(FINAL_SUMMARY_PATH, summary_rows, ["metric", "value", "note"])

    print(f"Original manifest rows: {len(original_manifest)}")
    print(f"Original audit rows: {len(original_audit)}")
    print(f"Recollection rows: {len(recollection_manifest)}")
    print(f"Recollection success rows applied: {replaced_success}")
    print(f"Recollection missing rows retained: {updated_missing}")
    print(f"Final manifest rows: {len(final_rows)}")
    print(f"Final audit rows: {len(final_audit)}")
    print(f"Final status counts: {dict(Counter(row.get('download_status') for row in final_rows))}")
    print(f"Final manifest: {FINAL_MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"Final audit: {FINAL_AUDIT_PATH.relative_to(REPO_ROOT)}")
    print(f"Final summary: {FINAL_SUMMARY_PATH.relative_to(REPO_ROOT)}")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update Top 100 10-K combined manifest with recollection results.")
    parser.add_argument("--source-run-id", default=DEFAULT_SOURCE_RUN_ID)
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    update_manifest(args.source_run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
