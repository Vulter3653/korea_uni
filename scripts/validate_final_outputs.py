#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_ROW_COUNTS = {
    "data/derived/market_extension/daily_market_data_10k_events.csv": 73746,
    "data/derived/market_extension/market_data_collection_report.csv": 273,
    "data/derived/market_extension/post_filing_market_reaction_estimates.csv": 273,
    "data/derived/market_extension/event_study_estimation_diagnostics.csv": 273,
    "data/derived/causal/ai_10k_event_study_analysis_dataset.csv": 273,
    "data/derived/causal/causal_event_study_regression_summary.csv": 21,
    "data/derived/causal/causal_event_study_model_diagnostics.csv": 10,
    "data/derived/causal/placebo_pre_filing_checks.csv": 9,
    "data/derived/causal/event_study_merge_diagnostics.csv": 1,
}

REQUIRED_FILES = [
    "README.md",
    "results_interpretation.md",
    "ai_adoption_news_dashboard.html",
    ".gitignore",
]

MERGE_DIAGNOSTICS_PATH = "data/derived/causal/event_study_merge_diagnostics.csv"
EXPECTED_MERGED_ROWS = 273


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def read_first_csv_row(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return {str(k).strip(): str(v).strip() for k, v in row.items()}
    return {}


def pass_line(message: str) -> None:
    print(f"[PASS] {message}")


def fail_line(message: str) -> None:
    print(f"[FAIL] {message}")


def main() -> int:
    failures: List[str] = []

    print("FINAL OUTPUT VALIDATION")
    print(f"Repo root: {REPO_ROOT}")

    for rel_path in REQUIRED_FILES:
        path = REPO_ROOT / rel_path
        if path.exists():
            pass_line(f"{rel_path} exists")
        else:
            fail_line(f"{rel_path} missing")
            failures.append(rel_path)

    for rel_path, expected_rows in EXPECTED_ROW_COUNTS.items():
        path = REPO_ROOT / rel_path
        if not path.exists():
            fail_line(f"{rel_path} missing")
            failures.append(rel_path)
            continue

        try:
            actual_rows = count_csv_rows(path)
        except Exception as exc:
            fail_line(f"{rel_path} could not be read: {exc}")
            failures.append(rel_path)
            continue

        if actual_rows == expected_rows:
            pass_line(f"{rel_path} rows = {actual_rows}")
        else:
            fail_line(f"{rel_path} rows = {actual_rows}; expected {expected_rows}")
            failures.append(rel_path)

    merge_path = REPO_ROOT / MERGE_DIAGNOSTICS_PATH
    if merge_path.exists():
        try:
            row = read_first_csv_row(merge_path)
            raw_value = row.get("merged_rows")
            if raw_value is None:
                fail_line(f"{MERGE_DIAGNOSTICS_PATH} missing merged_rows column")
                failures.append("merged_rows")
            else:
                actual = int(float(raw_value.strip()))
                if actual == EXPECTED_MERGED_ROWS:
                    pass_line(f"{MERGE_DIAGNOSTICS_PATH} merged_rows = {EXPECTED_MERGED_ROWS}")
                else:
                    fail_line(
                        f"{MERGE_DIAGNOSTICS_PATH} merged_rows = {actual}; expected {EXPECTED_MERGED_ROWS}"
                    )
                    failures.append("merged_rows")
        except Exception as exc:
            fail_line(f"{MERGE_DIAGNOSTICS_PATH} merged_rows check failed: {exc}")
            failures.append("merged_rows")
    else:
        fail_line(f"{MERGE_DIAGNOSTICS_PATH} missing")
        failures.append(MERGE_DIAGNOSTICS_PATH)

    if failures:
        print("")
        print("FINAL VERDICT: FAIL")
        print("Failed checks:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("")
    print("FINAL VERDICT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
