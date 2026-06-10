#!/usr/bin/env python3
"""Merge Fortune 2025 Top 100 10-K chunk artifacts.

This script merges chunk-level manifest/audit CSV files produced by
`collect-fortune-top100-10k.yml` into combined run-level CSV files.

Expected input layout after `actions/download-artifact`:

    artifacts/
      fortune2025-top100-10k-chunk-1/
        data/processed/fortune2025_top100_10k_chunk_01_manifest.csv
        data/audit/fortune2025_top100_10k_chunk_01_audit.csv
      fortune2025-top100-10k-chunk-2/
        ...

Outputs:

    data/processed/fortune2025_top100_10k_run_<RUN_ID>_combined_manifest.csv
    data/audit/fortune2025_top100_10k_run_<RUN_ID>_combined_audit.csv
    data/audit/fortune2025_top100_10k_run_<RUN_ID>_merge_summary.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "artifacts"
DEFAULT_RUN_ID = "unknown_run"

MANIFEST_GLOB = "**/data/processed/fortune2025_top100_10k_chunk_*_manifest.csv"
AUDIT_GLOB = "**/data/audit/fortune2025_top100_10k_chunk_*_audit.csv"
EXPECTED_CHUNKS = {"1", "2", "3", "4"}
EXPECTED_ROWS_PER_CHUNK = 75
EXPECTED_TOTAL_ROWS = 300


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


def chunk_id_from_rows(rows: List[Dict[str, str]], fallback: str) -> str:
    if rows and rows[0].get("collection_chunk_id"):
        return rows[0]["collection_chunk_id"]
    return fallback


def infer_chunk_from_path(path: Path) -> str:
    text = str(path)
    for chunk in EXPECTED_CHUNKS:
        if f"chunk_0{chunk}" in text or f"chunk-{chunk}" in text or f"chunk_{chunk}" in text:
            return chunk
    return "unknown"


def collect_chunk_files(artifact_root: Path) -> Tuple[List[Path], List[Path]]:
    manifests = sorted(artifact_root.glob(MANIFEST_GLOB))
    audits = sorted(artifact_root.glob(AUDIT_GLOB))
    if not manifests:
        raise FileNotFoundError(f"No chunk manifest files found under {artifact_root}")
    return manifests, audits


def sort_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    def key(row: Dict[str, str]) -> Tuple[int, int, int]:
        def to_int(value: str, default: int = 0) -> int:
            try:
                return int(value)
            except Exception:
                return default

        return (
            to_int(row.get("collection_chunk_id", "0")),
            to_int(row.get("fortune_rank_2025", "0")),
            to_int(row.get("target_report_year", "0")),
        )

    return sorted(rows, key=key)


def validate_manifest_rows(rows: List[Dict[str, str]]) -> None:
    if len(rows) != EXPECTED_TOTAL_ROWS:
        raise ValueError(f"Expected {EXPECTED_TOTAL_ROWS} combined manifest rows, found {len(rows)}")
    chunk_counts = Counter(row.get("collection_chunk_id", "") for row in rows)
    for chunk in EXPECTED_CHUNKS:
        actual = chunk_counts.get(chunk, 0)
        if actual != EXPECTED_ROWS_PER_CHUNK:
            raise ValueError(f"Chunk {chunk} expected {EXPECTED_ROWS_PER_CHUNK} rows, found {actual}")


def make_summary_rows(
    manifest_files: List[Path],
    audit_files: List[Path],
    manifest_rows: List[Dict[str, str]],
    audit_rows: List[Dict[str, str]],
    combined_manifest_path: Path,
    combined_audit_path: Path,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    status_counts = Counter(row.get("download_status", "") for row in manifest_rows)
    chunk_status: Dict[str, Counter] = {}
    chunk_rows: Dict[str, int] = Counter()
    chunk_audit_rows: Dict[str, int] = Counter()

    for row in manifest_rows:
        chunk = row.get("collection_chunk_id", "unknown")
        chunk_status.setdefault(chunk, Counter())[row.get("download_status", "")] += 1
        chunk_rows[chunk] += 1
    for row in audit_rows:
        chunk_audit_rows[row.get("collection_chunk_id", "unknown")] += 1

    for chunk in sorted(chunk_rows.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        counts = chunk_status.get(chunk, Counter())
        rows.append({
            "scope": f"chunk_{int(chunk):02d}" if chunk.isdigit() else chunk,
            "manifest_rows": str(chunk_rows[chunk]),
            "audit_rows": str(chunk_audit_rows.get(chunk, 0)),
            "success_rows": str(counts.get("success", 0)),
            "missing_rows": str(counts.get("missing", 0)),
            "failed_rows": str(counts.get("failed", 0)),
            "unavailable_rows": str(counts.get("unavailable", 0)),
            "status_counts": "; ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        })

    rows.append({
        "scope": "ALL_CHUNKS",
        "manifest_rows": str(len(manifest_rows)),
        "audit_rows": str(len(audit_rows)),
        "success_rows": str(status_counts.get("success", 0)),
        "missing_rows": str(status_counts.get("missing", 0)),
        "failed_rows": str(status_counts.get("failed", 0)),
        "unavailable_rows": str(status_counts.get("unavailable", 0)),
        "status_counts": "; ".join(f"{k}={v}" for k, v in sorted(status_counts.items())),
    })

    rows.append({
        "scope": "OUTPUT_SHA256",
        "manifest_rows": sha256_file(combined_manifest_path),
        "audit_rows": sha256_file(combined_audit_path),
        "success_rows": "",
        "missing_rows": "",
        "failed_rows": "",
        "unavailable_rows": "",
        "status_counts": "manifest_sha256 in manifest_rows; audit_sha256 in audit_rows",
    })
    return rows


def merge_artifacts(artifact_root: Path, run_id: str) -> Tuple[Path, Path, Path]:
    manifest_files, audit_files = collect_chunk_files(artifact_root)
    all_manifest_rows: List[Dict[str, str]] = []
    all_audit_rows: List[Dict[str, str]] = []
    manifest_fieldnames: List[str] = []
    audit_fieldnames: List[str] = []

    print(f"Artifact root: {artifact_root}")
    print(f"Manifest files found: {len(manifest_files)}")
    print(f"Audit files found: {len(audit_files)}")

    for path in manifest_files:
        rows = read_csv(path)
        fallback_chunk = infer_chunk_from_path(path)
        chunk = chunk_id_from_rows(rows, fallback_chunk)
        print(f"manifest chunk {chunk}: {len(rows)} rows | {path}")
        if not manifest_fieldnames and rows:
            manifest_fieldnames = list(rows[0].keys())
        all_manifest_rows.extend(rows)

    for path in audit_files:
        rows = read_csv(path)
        fallback_chunk = infer_chunk_from_path(path)
        chunk = chunk_id_from_rows(rows, fallback_chunk)
        print(f"audit chunk {chunk}: {len(rows)} rows | {path}")
        if not audit_fieldnames and rows:
            audit_fieldnames = list(rows[0].keys())
        all_audit_rows.extend(rows)

    all_manifest_rows = sort_rows(all_manifest_rows)
    all_audit_rows = sort_rows(all_audit_rows)
    validate_manifest_rows(all_manifest_rows)

    if not manifest_fieldnames:
        raise ValueError("Could not infer manifest CSV fieldnames")
    if not audit_fieldnames:
        audit_fieldnames = manifest_fieldnames

    safe_run_id = str(run_id).strip() or DEFAULT_RUN_ID
    combined_manifest_path = REPO_ROOT / "data" / "processed" / f"fortune2025_top100_10k_run_{safe_run_id}_combined_manifest.csv"
    combined_audit_path = REPO_ROOT / "data" / "audit" / f"fortune2025_top100_10k_run_{safe_run_id}_combined_audit.csv"
    merge_summary_path = REPO_ROOT / "data" / "audit" / f"fortune2025_top100_10k_run_{safe_run_id}_merge_summary.csv"

    write_csv(combined_manifest_path, all_manifest_rows, manifest_fieldnames)
    write_csv(combined_audit_path, all_audit_rows, audit_fieldnames)

    summary_fieldnames = [
        "scope",
        "manifest_rows",
        "audit_rows",
        "success_rows",
        "missing_rows",
        "failed_rows",
        "unavailable_rows",
        "status_counts",
    ]
    summary_rows = make_summary_rows(
        manifest_files,
        audit_files,
        all_manifest_rows,
        all_audit_rows,
        combined_manifest_path,
        combined_audit_path,
    )
    write_csv(merge_summary_path, summary_rows, summary_fieldnames)

    print(f"Combined manifest: {combined_manifest_path.relative_to(REPO_ROOT)}")
    print(f"Combined audit: {combined_audit_path.relative_to(REPO_ROOT)}")
    print(f"Merge summary: {merge_summary_path.relative_to(REPO_ROOT)}")
    print(f"Combined manifest rows: {len(all_manifest_rows)}")
    print(f"Combined audit rows: {len(all_audit_rows)}")
    return combined_manifest_path, combined_audit_path, merge_summary_path


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge Fortune 2025 Top 100 10-K chunk artifacts.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    merge_artifacts(args.artifact_root, args.run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
