#!/usr/bin/env python3
"""Build final Fortune 2025 Top 100 AI analysis datasets.

Inputs
------
1. data/processed/fortune2025_top100_10k_report_linked_with_industry.csv
   - 300-row master frame with 10-K links, collection status, SEC SIC and NAICS-sector fields.
2. data/processed/fortune2025_top100_k5_ai_topic_analysis_dataset.csv
   - 246-row K=5 topic dataset for firm-years with at least one AI mention window.

Outputs
-------
1. data/processed/fortune2025_top100_final_ai_analysis_master.csv
   - 300 firm-year rows. Keeps missing 10-K rows. Topic values are blank for non-collected 10-K rows.
2. data/processed/fortune2025_top100_final_ai_analysis_text_sample.csv
   - 273 firm-year rows with collected 10-K text. Topic values are zero for text rows with no AI windows.
3. data/processed/fortune2025_top100_final_ai_analysis_k5_topic_sample.csv
   - 246 firm-year rows with at least one AI mention window.
4. data/audit/fortune2025_top100_final_ai_analysis_dataset_summary.csv
   - dataset sizes and key mean values.

Treatment rules
---------------
- Master frame remains Fortune 2025 Top 100 x 2023-2025 = 300 firm-years.
- Non-success 10-K rows remain in the master dataset and are coded has_10k_text = FALSE.
- Successful 10-K rows with no AI mention windows remain in the text dataset and receive zero-valued topic variables.
- K=5 topic sample is a strict subset containing only firm-years with AI mention windows.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
INDUSTRY_INPUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_10k_report_linked_with_industry.csv"
K5_INPUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_k5_ai_topic_analysis_dataset.csv"
MASTER_OUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_final_ai_analysis_master.csv"
TEXT_OUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_final_ai_analysis_text_sample.csv"
K5_OUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_final_ai_analysis_k5_topic_sample.csv"
SUMMARY_OUT = REPO_ROOT / "data" / "audit" / "fortune2025_top100_final_ai_analysis_dataset_summary.csv"

TOPIC_NUMERIC_COLUMNS = [
    "ai_window_count",
    "topic_0_count",
    "topic_0_share",
    "topic_1_count",
    "topic_1_share",
    "topic_2_count",
    "topic_2_share",
    "topic_3_count",
    "topic_3_share",
    "topic_4_count",
    "topic_4_share",
    "AI_Privacy_Data_Law_Topic_Count",
    "AI_Privacy_Data_Law_Topic_Share",
    "AI_Business_Product_Topic_Count",
    "AI_Business_Product_Topic_Share",
    "AI_Cybersecurity_Risk_Topic_Count",
    "AI_Cybersecurity_Risk_Topic_Share",
    "AI_Infrastructure_Topic_Count",
    "AI_Infrastructure_Topic_Share",
    "AI_AIUse_LegalRisk_Topic_Count",
    "AI_AIUse_LegalRisk_Topic_Share",
    "AI_NegativeSensitive_Topic_Count",
    "AI_NegativeSensitive_Topic_Share",
    "AI_Negative_Orientation",
]

TOPIC_TEXT_COLUMNS = [
    "k",
    "k5_topic_0_label",
    "k5_topic_1_label",
    "k5_topic_2_label",
    "k5_topic_3_label",
    "k5_topic_4_label",
    "AI_Dominant_Topic_ID",
    "AI_Dominant_Topic_Label",
]

TOPIC_LABEL_DEFAULTS = {
    "k": "5",
    "k5_topic_0_label": "privacy_data_law_protection",
    "k5_topic_1_label": "business_product_service_revenue",
    "k5_topic_2_label": "cybersecurity_attacks_security_threats",
    "k5_topic_3_label": "ai_cloud_platform_infrastructure",
    "k5_topic_4_label": "ai_use_legal_regulatory_risk",
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def key(row: Dict[str, str]) -> Tuple[str, str, str]:
    return (
        str(row.get("cik_padded") or row.get("cik") or "").strip(),
        str(row.get("ticker") or "").strip(),
        str(row.get("target_report_year") or "").strip(),
    )


def is_true(value: object) -> bool:
    return str(value).strip().upper() == "TRUE"


def safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def sort_rows(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    def safe_int(value: object, default: int = 0) -> int:
        try:
            return int(float(str(value)))
        except Exception:
            return default

    return sorted(
        rows,
        key=lambda row: (
            safe_int(row.get("fortune_rank_2025", 0), 9999),
            safe_int(row.get("target_report_year", 0), 9999),
        ),
    )


def build_final_rows(industry_rows: List[Dict[str, str]], k5_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    k5_by_key = {key(row): row for row in k5_rows}
    final_rows: List[Dict[str, object]] = []

    for base in industry_rows:
        out: Dict[str, object] = dict(base)
        has_10k_text = is_true(base.get("has_10k_text"))
        topic = k5_by_key.get(key(base))
        has_ai_window = topic is not None

        out["final_dataset_role"] = "master_frame"
        out["has_10k_text_final"] = "TRUE" if has_10k_text else "FALSE"
        out["has_ai_window_k5"] = "TRUE" if has_ai_window else "FALSE"
        out["is_primary_text_sample"] = "TRUE" if has_10k_text else "FALSE"
        out["is_k5_topic_sample"] = "TRUE" if has_ai_window else "FALSE"

        if topic:
            for col in TOPIC_NUMERIC_COLUMNS + TOPIC_TEXT_COLUMNS:
                out[col] = topic.get(col, "")
        elif has_10k_text:
            # Collected text but no AI mention window: topic exposure is structurally zero.
            for col in TOPIC_NUMERIC_COLUMNS:
                out[col] = "0"
            for col, value in TOPIC_LABEL_DEFAULTS.items():
                out[col] = value
            out["AI_Dominant_Topic_ID"] = ""
            out["AI_Dominant_Topic_Label"] = "no_ai_mention_window"
        else:
            # Missing/unavailable 10-K text: keep topic variables blank because text was not observed.
            for col in TOPIC_NUMERIC_COLUMNS + TOPIC_TEXT_COLUMNS:
                out[col] = ""

        final_rows.append(out)
    return sort_rows(final_rows)


def mean(rows: List[Dict[str, object]], col: str) -> float:
    vals = [safe_float(row.get(col)) for row in rows if str(row.get(col, "")) != ""]
    return sum(vals) / len(vals) if vals else 0.0


def build_summary(master_rows: List[Dict[str, object]], text_rows: List[Dict[str, object]], k5_rows: List[Dict[str, object]]) -> List[Dict[str, str]]:
    status_counts = Counter(str(row.get("download_status", "")) for row in master_rows)
    dominant_counts = Counter(str(row.get("AI_Dominant_Topic_Label", "")) for row in k5_rows)
    sector_counts = Counter(str(row.get("naics_sector_code", "")) for row in master_rows if row.get("naics_sector_code"))
    return [
        {"metric": "master_rows", "value": str(len(master_rows)), "note": "Fortune 2025 Top 100 x 2023-2025 firm-year master frame"},
        {"metric": "text_sample_rows", "value": str(len(text_rows)), "note": "Rows with successfully collected 10-K text"},
        {"metric": "k5_topic_sample_rows", "value": str(len(k5_rows)), "note": "Rows with at least one AI mention window under K=5 topic solution"},
        {"metric": "text_rows_without_ai_windows", "value": str(len(text_rows) - len(k5_rows)), "note": "Text collected but no AI mention window; topic variables set to zero"},
        {"metric": "download_status_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(status_counts.items())), "note": "Final 10-K collection status in master dataset"},
        {"metric": "main_topic_solution", "value": "K=5", "note": "Selected for interpretability; K=4 retained as robustness and K=6 as sensitivity"},
        {"metric": "main_iv", "value": "AI_NegativeSensitive_Topic_Share", "note": "T0 privacy/data/law + T2 cybersecurity/security threat + T4 AI use/legal/risk"},
        {"metric": "mean_AI_NegativeSensitive_Topic_Share_text_sample", "value": f"{mean(text_rows, 'AI_NegativeSensitive_Topic_Share'):.6f}", "note": "Mean over 273 text-sample rows, including zero-AI-window rows"},
        {"metric": "mean_AI_NegativeSensitive_Topic_Share_k5_topic_sample", "value": f"{mean(k5_rows, 'AI_NegativeSensitive_Topic_Share'):.6f}", "note": "Mean over 246 K=5 topic-sample rows"},
        {"metric": "mean_AI_Infrastructure_Topic_Share_text_sample", "value": f"{mean(text_rows, 'AI_Infrastructure_Topic_Share'):.6f}", "note": "Mean over 273 text-sample rows"},
        {"metric": "mean_AI_Negative_Orientation_text_sample", "value": f"{mean(text_rows, 'AI_Negative_Orientation'):.6f}", "note": "Mean over 273 text-sample rows"},
        {"metric": "dominant_topic_counts_k5_topic_sample", "value": "; ".join(f"{k}={v}" for k, v in sorted(dominant_counts.items())), "note": "Dominant topic distribution among 246 AI-window firm-years"},
        {"metric": "naics_sector_counts_master", "value": "; ".join(f"{k}={v}" for k, v in sorted(sector_counts.items())), "note": "Master firm-year counts by approximate NAICS sector code"},
    ]


def main() -> int:
    industry_rows = read_csv(INDUSTRY_INPUT)
    k5_rows_raw = read_csv(K5_INPUT)
    final_rows = build_final_rows(industry_rows, k5_rows_raw)
    text_rows = [row for row in final_rows if row.get("is_primary_text_sample") == "TRUE"]
    k5_topic_rows = [row for row in final_rows if row.get("is_k5_topic_sample") == "TRUE"]

    if len(final_rows) != 300:
        raise SystemExit(f"Expected 300 master rows, found {len(final_rows)}")
    if len(text_rows) != 273:
        raise SystemExit(f"Expected 273 text sample rows, found {len(text_rows)}")
    if len(k5_topic_rows) != 246:
        raise SystemExit(f"Expected 246 K=5 topic sample rows, found {len(k5_topic_rows)}")

    fieldnames = list(final_rows[0].keys())
    write_csv(MASTER_OUT, final_rows, fieldnames)
    write_csv(TEXT_OUT, text_rows, fieldnames)
    write_csv(K5_OUT, k5_topic_rows, fieldnames)
    write_csv(SUMMARY_OUT, build_summary(final_rows, text_rows, k5_topic_rows), ["metric", "value", "note"])

    print(f"Master final dataset: {MASTER_OUT.relative_to(REPO_ROOT)} ({len(final_rows)} rows)")
    print(f"Text-sample final dataset: {TEXT_OUT.relative_to(REPO_ROOT)} ({len(text_rows)} rows)")
    print(f"K=5 topic-sample final dataset: {K5_OUT.relative_to(REPO_ROOT)} ({len(k5_topic_rows)} rows)")
    print(f"Summary: {SUMMARY_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
