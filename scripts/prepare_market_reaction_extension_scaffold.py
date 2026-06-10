#!/usr/bin/env python3
"""Prepare a conservative post-filing market-reaction extension scaffold.

This script does not estimate market reactions. It creates a schema-ready panel
from existing 10-K communication measures and leaves market outcomes blank with
status = not_estimated. Use this only after audited stock/volume data are added.

Empirical extension design
--------------------------
- Event date: 10-K filing_date, not report_date
- Estimation window: [-250, -30] trading days
- Planned event windows: CAR[0,+1], CAR[-1,+1], CAR[0,+3], Abnormal Volume[0,+3]
- Focal communication proxy: AI_RiskRelated_Topic_Share
- Controls: AI_Related_Disclosure_Intensity, total_words, sector FE, year FE,
  and firm size if later added

No causal identification is claimed by this scaffold.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT = REPO_ROOT / "data" / "processed" / "fortune2025_top100_final_ai_analysis_text_sample.csv"
OUT = REPO_ROOT / "data" / "derived" / "market_extension" / "post_filing_market_reaction_scaffold.csv"

EVENT_WINDOWS = ["CAR_0_1", "CAR_m1_1", "CAR_0_3", "AbnormalVolume_0_3"]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_rows(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        built: Dict[str, object] = {
            "fortune_rank_2025": row.get("fortune_rank_2025", ""),
            "company_name": row.get("company_name", ""),
            "ticker": row.get("ticker", ""),
            "cik_padded": row.get("cik_padded", ""),
            "target_report_year": row.get("target_report_year", ""),
            "event_date": row.get("filing_date", ""),
            "event_date_source": "10-K filing_date",
            "estimation_window": "[-250,-30] trading days",
            "AI_Related_Disclosure_Intensity": row.get("ai_keyword_per_10k_words", ""),
            "AI_RiskRelated_Topic_Share": row.get("AI_RiskRelated_Topic_Share") or row.get("AI_NegativeSensitive_Topic_Share", ""),
            "AI_Risk_Orientation_Proxy": row.get("AI_Risk_Orientation_Proxy") or row.get("AI_Negative_Orientation", ""),
            "total_words": row.get("total_words", ""),
            "naics_sector_code": row.get("naics_sector_code", ""),
            "naics_sector_name": row.get("naics_sector_name", ""),
            "market_data_status": "not_estimated",
            "interpretation": "schema scaffold only; no market data joined and no causal identification claimed",
        }
        for col in EVENT_WINDOWS:
            built[col] = ""
        out.append(built)
    return out


def main() -> int:
    rows = read_csv(INPUT)
    out = build_rows(rows)
    fields = list(out[0].keys()) if out else []
    write_csv(OUT, out, fields)
    print(f"Market extension scaffold: {OUT.relative_to(REPO_ROOT)} ({len(out)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
