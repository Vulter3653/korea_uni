#!/usr/bin/env python3
"""Build the K=5 AI communication topic-analysis dataset.

This script treats K=5 as the selected descriptive topic solution because it
provides interpretable AI communication contexts while remaining close to K=4
in optimization quality. It does not estimate causal effects or measure actual
AI adoption.

K=5 topic interpretation
------------------------
T0: privacy/data/law/protection
T1: business/product/service/revenue context
T2: cybersecurity/attacks/security threats
T3: AI cloud/software/platform/infrastructure
T4: AI use/legal/regulatory/risk

Main derived variables
----------------------
AI_RiskRelated_Topic_Share = T0 + T2 + T4
AI_RiskRelated_Topic_Count = T0 + T2 + T4
Backward-compatible aliases retained in outputs:
AI_NegativeSensitive_Topic_Share = AI_RiskRelated_Topic_Share
AI_NegativeSensitive_Topic_Count = AI_RiskRelated_Topic_Count
AI_Privacy_Data_Law_Topic_Share = T0
AI_Cybersecurity_Risk_Topic_Share = T2
AI_AIUse_LegalRisk_Topic_Share = T4
AI_Infrastructure_Topic_Share = T3
AI_Business_Product_Topic_Share = T1
AI_Risk_Orientation_Proxy = (T0 + T2 + T4 - T3) / ai_window_count
AI_Negative_Orientation = AI_Risk_Orientation_Proxy

Outputs
-------
- data/processed/fortune2025_top100_k5_ai_topic_analysis_dataset.csv
- data/audit/10k_ai_topics/k5_ai_topic_analysis_dataset_summary.csv
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "data" / "processed" / "10k_ai_topic_model_comparison" / "k_05" / "firm_year_topic_distribution.csv"
OUTPUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_k5_ai_topic_analysis_dataset.csv"
SUMMARY = REPO_ROOT / "data" / "audit" / "10k_ai_topics" / "k5_ai_topic_analysis_dataset_summary.csv"

TOPIC_LABELS = {
    0: "privacy_data_law_protection",
    1: "business_product_service_revenue",
    2: "cybersecurity_attacks_security_threats",
    3: "ai_cloud_platform_infrastructure",
    4: "ai_use_legal_regulatory_risk",
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


def as_float(row: Dict[str, str], col: str) -> float:
    try:
        return float(row.get(col, "0") or 0)
    except Exception:
        return 0.0


def as_int(row: Dict[str, str], col: str) -> int:
    try:
        return int(float(row.get(col, "0") or 0))
    except Exception:
        return 0


def build_dataset(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out_rows: List[Dict[str, object]] = []
    for row in rows:
        ai_window_count = as_int(row, "ai_window_count")
        t0_count = as_int(row, "topic_0_count")
        t1_count = as_int(row, "topic_1_count")
        t2_count = as_int(row, "topic_2_count")
        t3_count = as_int(row, "topic_3_count")
        t4_count = as_int(row, "topic_4_count")
        t0_share = as_float(row, "topic_0_share")
        t1_share = as_float(row, "topic_1_share")
        t2_share = as_float(row, "topic_2_share")
        t3_share = as_float(row, "topic_3_share")
        t4_share = as_float(row, "topic_4_share")

        neg_count = t0_count + t2_count + t4_count
        neg_share = t0_share + t2_share + t4_share
        infrastructure_count = t3_count
        infrastructure_share = t3_share
        business_count = t1_count
        business_share = t1_share
        negative_orientation = ((neg_count - infrastructure_count) / ai_window_count) if ai_window_count else 0.0

        dominant_topic_id = max(
            [(0, t0_count), (1, t1_count), (2, t2_count), (3, t3_count), (4, t4_count)],
            key=lambda item: item[1],
        )[0]

        out = dict(row)
        out.update(
            {
                "k5_topic_0_label": TOPIC_LABELS[0],
                "k5_topic_1_label": TOPIC_LABELS[1],
                "k5_topic_2_label": TOPIC_LABELS[2],
                "k5_topic_3_label": TOPIC_LABELS[3],
                "k5_topic_4_label": TOPIC_LABELS[4],
                "AI_Privacy_Data_Law_Topic_Count": t0_count,
                "AI_Privacy_Data_Law_Topic_Share": round(t0_share, 6),
                "AI_Business_Product_Topic_Count": business_count,
                "AI_Business_Product_Topic_Share": round(business_share, 6),
                "AI_Cybersecurity_Risk_Topic_Count": t2_count,
                "AI_Cybersecurity_Risk_Topic_Share": round(t2_share, 6),
                "AI_Infrastructure_Topic_Count": infrastructure_count,
                "AI_Infrastructure_Topic_Share": round(infrastructure_share, 6),
                "AI_AIUse_LegalRisk_Topic_Count": t4_count,
                "AI_AIUse_LegalRisk_Topic_Share": round(t4_share, 6),
                "AI_RiskRelated_Topic_Count": neg_count,
                "AI_RiskRelated_Topic_Share": round(neg_share, 6),
                "AI_Risk_Orientation_Proxy": round(negative_orientation, 6),
                "AI_NegativeSensitive_Topic_Count": neg_count,
                "AI_NegativeSensitive_Topic_Share": round(neg_share, 6),
                "AI_Negative_Orientation": round(negative_orientation, 6),
                "AI_Dominant_Topic_ID": dominant_topic_id,
                "AI_Dominant_Topic_Label": TOPIC_LABELS[dominant_topic_id],
            }
        )
        out_rows.append(out)
    return out_rows


def build_summary(rows: List[Dict[str, object]]) -> List[Dict[str, str]]:
    dominant_counts = Counter(str(row.get("AI_Dominant_Topic_Label", "")) for row in rows)
    n_rows = len(rows)
    avg_neg = sum(float(row.get("AI_NegativeSensitive_Topic_Share", 0)) for row in rows) / n_rows if n_rows else 0
    avg_infra = sum(float(row.get("AI_Infrastructure_Topic_Share", 0)) for row in rows) / n_rows if n_rows else 0
    avg_orientation = sum(float(row.get("AI_Negative_Orientation", 0)) for row in rows) / n_rows if n_rows else 0
    return [
        {"metric": "topic_solution", "value": "K=5", "note": "Main topic solution selected for interpretability"},
        {"metric": "firm_year_rows", "value": str(n_rows), "note": "Firm-years with at least one AI mention window"},
        {"metric": "topic_labels", "value": "; ".join(f"T{k}={v}" for k, v in TOPIC_LABELS.items()), "note": "K=5 manual interpretation based on topic_terms.csv"},
        {"metric": "focal_communication_measure", "value": "AI_RiskRelated_Topic_Share", "note": "T0 + T2 + T4 share; text-based communication proxy, not actual AI adoption"},
        {"metric": "risk_related_components", "value": "T0 privacy/data/law + T2 cybersecurity/security threat + T4 AI use/legal/risk", "note": "Risk/regulation/privacy/cybersecurity/legal communication context"},
        {"metric": "mean_AI_RiskRelated_Topic_Share", "value": f"{avg_neg:.6f}", "note": "Average across firm-years with AI windows"},
        {"metric": "mean_AI_Infrastructure_Topic_Share", "value": f"{avg_infra:.6f}", "note": "Average across firm-years with AI windows"},
        {"metric": "mean_AI_Risk_Orientation_Proxy", "value": f"{avg_orientation:.6f}", "note": "Mean of (risk-related count - infrastructure count) / AI window count"},
        {"metric": "dominant_topic_counts", "value": "; ".join(f"{k}={v}" for k, v in sorted(dominant_counts.items())), "note": "Dominant K=5 topic by firm-year"},
    ]


def main() -> int:
    rows = read_csv(INPUT)
    out_rows = build_dataset(rows)
    if not out_rows:
        raise SystemExit("No rows produced")
    write_csv(OUTPUT, out_rows, list(out_rows[0].keys()))
    write_csv(SUMMARY, build_summary(out_rows), ["metric", "value", "note"])
    print(f"K=5 analysis dataset: {OUTPUT.relative_to(REPO_ROOT)} ({len(out_rows)} rows)")
    print(f"Summary: {SUMMARY.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
