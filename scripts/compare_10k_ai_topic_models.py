#!/usr/bin/env python3
"""Compare fixed-K topic models for AI-related 10-K mention windows.

Purpose
-------
Run the same topic-model pipeline for multiple fixed K values, usually K=4,5,6,
without overwriting the canonical final topic-model outputs.

Outputs
-------
Base directory: data/processed/10k_ai_topic_model_comparison/

- k_04/ai_topic_assignments.csv
- k_04/firm_year_topic_distribution.csv
- k_04/topic_terms.csv
- k_05/...
- k_06/...
- k456_model_comparison_summary.csv
- k456_topic_terms_long.csv
- k456_firm_year_topic_distribution_long.csv

Audit:
- data/audit/10k_ai_topics/k456_model_comparison_summary.csv

Example
-------
python scripts/compare_10k_ai_topic_models.py \
  --input-csv data/processed/fortune2025_top100_10k_report_linked_text_sample.csv \
  --k-values 4,5,6 \
  --window-size 1
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from run_10k_ai_bert_topic_model import (  # type: ignore
    DEFAULT_INPUT_CSV,
    REPO_ROOT,
    SEED_FRAME_DICTIONARY,
    assign_topics,
    build_firm_year_distribution,
    compute_seed_frame_scores,
    extract_windows,
    read_csv,
    write_csv,
)

OUT_BASE = REPO_ROOT / "data" / "processed" / "10k_ai_topic_model_comparison"
AUDIT_OUT = REPO_ROOT / "data" / "audit" / "10k_ai_topics" / "k456_model_comparison_summary.csv"


def parse_k_values(raw: str) -> List[int]:
    values = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(int(part))
    if not values:
        raise ValueError("At least one K value is required")
    return values


def build_topic_term_rows(topic_terms: List[List[str]], labels: List[int], k: int) -> List[Dict[str, object]]:
    counts = Counter(labels)
    return [
        {
            "k": k,
            "topic_id": topic_id,
            "topic_terms": "; ".join(terms),
            "topic_window_count": counts.get(topic_id, 0),
            "topic_window_share": round(counts.get(topic_id, 0) / len(labels), 6) if labels else 0.0,
        }
        for topic_id, terms in enumerate(topic_terms)
    ]


def run_for_k(
    k: int,
    window_dicts: List[Dict[str, object]],
    random_state: int,
    model_name: str,
    tfidf_fallback_only: bool,
) -> Dict[str, object]:
    texts = [str(row["window_text"]) for row in window_dicts]
    labels, topic_terms, model_used = assign_topics(texts, k, random_state, model_name, tfidf_fallback_only)
    effective_topics = len(topic_terms)

    assignments: List[Dict[str, object]] = []
    for row, label in zip(window_dicts, labels):
        assigned = dict(row)
        assigned["k"] = k
        assigned["topic_id"] = int(label)
        assigned["topic_terms"] = "; ".join(topic_terms[int(label)]) if int(label) < len(topic_terms) else ""
        assignments.append(assigned)

    topic_term_rows = build_topic_term_rows(topic_terms, labels, k)
    distribution = build_firm_year_distribution(assignments, effective_topics)
    for row in distribution:
        row["k"] = k

    out_dir = OUT_BASE / f"k_{k:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    window_fields = list(window_dicts[0].keys())
    seed_fields = [f"seed_{frame}_count" for frame in SEED_FRAME_DICTIONARY]
    write_csv(out_dir / "ai_topic_assignments.csv", assignments, ["k"] + window_fields + seed_fields + ["topic_id", "topic_terms"])
    write_csv(out_dir / "topic_terms.csv", topic_term_rows, ["k", "topic_id", "topic_terms", "topic_window_count", "topic_window_share"])
    dist_fields = list(distribution[0].keys()) if distribution else []
    write_csv(out_dir / "firm_year_topic_distribution.csv", distribution, dist_fields)

    topic_counts = Counter(labels)
    min_size = min(topic_counts.values()) if topic_counts else 0
    max_size = max(topic_counts.values()) if topic_counts else 0
    return {
        "k": k,
        "effective_topics": effective_topics,
        "n_windows": len(labels),
        "firm_years_with_ai_windows": len(distribution),
        "model_used": model_used,
        "min_topic_size": min_size,
        "max_topic_size": max_size,
        "min_topic_share": round(min_size / len(labels), 6) if labels else 0.0,
        "max_topic_share": round(max_size / len(labels), 6) if labels else 0.0,
        "topic_size_distribution": "; ".join(f"{topic_id}:{count}" for topic_id, count in sorted(topic_counts.items())),
        "topic_terms_preview": " | ".join(f"T{row['topic_id']}:" + str(row["topic_terms"]) for row in topic_term_rows),
        "assignments_path": str((out_dir / "ai_topic_assignments.csv").relative_to(REPO_ROOT)),
        "topic_terms_path": str((out_dir / "topic_terms.csv").relative_to(REPO_ROOT)),
        "firm_year_distribution_path": str((out_dir / "firm_year_topic_distribution.csv").relative_to(REPO_ROOT)),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare fixed-K AI topic models for 10-K mention windows.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--k-values", default="4,5,6")
    parser.add_argument("--window-size", type=int, default=1)
    parser.add_argument("--max-windows-per-doc", type=int, default=0, help="0 means no cap")
    parser.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--tfidf-fallback-only", action="store_true")
    args = parser.parse_args(argv)

    k_values = parse_k_values(args.k_values)
    rows = read_csv(args.input_csv)
    windows = extract_windows(rows, args.window_size, args.max_windows_per_doc)
    if not windows:
        raise SystemExit("No AI mention windows extracted. Check input CSV and local_text_path files.")

    window_dicts = [asdict(window) for window in windows]
    for row in window_dicts:
        row.update(compute_seed_frame_scores(str(row["window_text"])))

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "data" / "audit" / "10k_ai_topics").mkdir(parents=True, exist_ok=True)

    comparison_rows: List[Dict[str, object]] = []
    all_topic_terms: List[Dict[str, object]] = []
    all_distribution_rows: List[Dict[str, object]] = []

    for k in k_values:
        print(f"Running fixed-K topic model: K={k}")
        summary = run_for_k(k, window_dicts, args.random_state, args.model_name, args.tfidf_fallback_only)
        comparison_rows.append(summary)

        topic_terms_path = REPO_ROOT / str(summary["topic_terms_path"])
        all_topic_terms.extend(read_csv(topic_terms_path))
        dist_path = REPO_ROOT / str(summary["firm_year_distribution_path"])
        all_distribution_rows.extend(read_csv(dist_path))

    summary_fields = [
        "k",
        "effective_topics",
        "n_windows",
        "firm_years_with_ai_windows",
        "model_used",
        "min_topic_size",
        "max_topic_size",
        "min_topic_share",
        "max_topic_share",
        "topic_size_distribution",
        "topic_terms_preview",
        "assignments_path",
        "topic_terms_path",
        "firm_year_distribution_path",
    ]
    write_csv(OUT_BASE / "k456_model_comparison_summary.csv", comparison_rows, summary_fields)
    write_csv(AUDIT_OUT, comparison_rows, summary_fields)

    if all_topic_terms:
        write_csv(OUT_BASE / "k456_topic_terms_long.csv", all_topic_terms, list(all_topic_terms[0].keys()))
    if all_distribution_rows:
        write_csv(OUT_BASE / "k456_firm_year_topic_distribution_long.csv", all_distribution_rows, list(all_distribution_rows[0].keys()))

    print(f"Compared K values: {k_values}")
    print(f"AI mention windows: {len(window_dicts)}")
    print(f"Comparison summary: {(OUT_BASE / 'k456_model_comparison_summary.csv').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
