# Korea University Research Project Repository

This repository contains the Fortune 2025 Top 100 10-K AI disclosure research pipeline and dashboard.

## Research Question

This project analyzes whether AI-related communication in Fortune 2025 Top 100 firms' 10-K reports is linked to abnormal market reactions around the 10-K filing date.

Current title:

```text
Corporate AI Communication and Capital Market Response:
A 10-K Filing Event Study of Fortune 2025 Top 100 Firms
```

The empirical design uses 10-K `filing_date` as the event date. AI disclosure variables are text-based communication proxies; they are not direct observations of actual AI adoption.

## Event-Study Design

| Component | Design |
| --- | --- |
| Event date | 10-K `filing_date` |
| Estimation window | [-250, -30] trading days |
| CAR windows | `CAR_m1_p1`, `CAR_0_p1`, `CAR_0_p3`, `CAR_0_p5` |
| Abnormal volume windows | `AbnormalVolume_0_p1`, `AbnormalVolume_0_p3`, `AbnormalVolume_0_p5` |
| Benchmark priority | `SPY`, then `^GSPC` |
| Placebo windows | `CAR_m10_m6`, `CAR_m5_m2`, `AbnormalVolume_m5_m2` |

Market-model expected returns are estimated as:

```text
R_i,d = alpha_i + beta_i R_m,d + epsilon_i,d
```

Abnormal returns are summed over event windows. Abnormal volume is computed as a log-volume z-score relative to the estimation window.

## Data Sources

| Source | Repository path / source |
| --- | --- |
| 10-K AI communication panel | `data/processed/fortune2025_top100_final_ai_analysis_text_sample.csv` |
| Event-study scaffold | `data/derived/market_extension/post_filing_market_reaction_scaffold.csv` |
| Market data collector | `scripts/collect_market_data_for_10k_event_study.py` |
| External market source | yfinance, with FinanceDataReader and Stooq CSV fallback in the collector |

## Local Market Data Fallback

If network access to `yfinance` or `Stooq` is blocked in your environment, you can use the local CSV fallback mechanism by placing data in the raw directories:

**Directory Structure:**
```text
data/raw/market_data/prices/<TICKER>.csv
data/raw/market_data/benchmarks/<BENCHMARK>.csv
```

**Required Schema (case-insensitive column names):**
- **Firm price file:** `date, close, adj_close, volume` (plus open, high, low if available)
- **Benchmark file:** `date, close, adj_close, volume`

**Processing Rules:**
- The script automatically checks these directories before attempting to download.
- `TICKER` must match the yfinance ticker (e.g., `BRK-B.csv` instead of `BRK.B.csv`).
- If `adj_close` is missing, `close` will be used as a fallback.
- If `volume` is missing, abnormal volume calculation will fail, but CARs will still be calculated.

The current run successfully collected market data using the `FinanceDataReader` fallback since `yfinance` network fetching was blocked. CAR and abnormal volume outputs are successfully generated. However, regression models failed to estimate (`insufficient_regression_rows=0`) due to a CIK padding mismatch preventing the merge of AI text features with market outcomes.

## Sample Construction

| Sample | Firm-year rows | Use |
| --- | ---: | --- |
| Master 10-K frame | 300 | Fortune 2025 Top 100 x 2023-2025 coverage frame |
| Observed 10-K text sample | 273 | Event-study candidate events |
| K=5 AI-window topic sample | 246 | Downstream topic-derived communication measures |
| Final audit / non-success rows | 27 | Missingness documentation |

The 246-row K=5 sample is a downstream topic-analysis subset. It is not the full observed text sample.

## AI Disclosure Measures

Main explanatory variables:

```text
AI_Related_Disclosure_Intensity
AI_RiskRelated_Topic_Share
AI_Risk_Orientation_Proxy
```

Aliases are created safely from existing columns when needed:

| Alias | Source fallback |
| --- | --- |
| `AI_Related_Disclosure_Intensity` | `ai_keyword_per_10k_words` |
| `AI_RiskRelated_Topic_Share` | `AI_NegativeSensitive_Topic_Share` |
| `AI_Risk_Orientation_Proxy` | `AI_Negative_Orientation` |

These are communication measures based on 10-K text. Topic labels are machine/topic-derived labels and should not be described as human-validated coding unless manual validation is completed.

## Market Reaction Outcomes

Main dependent variables:

```text
CAR_m1_p1
CAR_0_p1
CAR_0_p3
CAR_0_p5
AbnormalVolume_0_p1
AbnormalVolume_0_p3
AbnormalVolume_0_p5
```

The current generated event-study estimate file has headers but zero estimated rows because market data collection failed in this environment.

## Regression Specification

The intended regression family is:

```text
Y_i,t,w = alpha
  + beta_1 AI_Related_Disclosure_Intensity_i,t
  + beta_2 AI_RiskRelated_Topic_Share_i,t
  + beta_3 AI_Risk_Orientation_Proxy_i,t
  + gamma Controls_i,t
  + Firm FE
  + Year FE
  + epsilon_i,t
```

Implemented fallback order:

```text
1. Firm FE + Year FE
2. Year FE only
3. Sector FE + Year FE
4. No-FE baseline with controls
```

Standard errors use firm-level clustering when feasible and HC1 robust standard errors otherwise. In the current run, regression models failed to estimate due to the identifier mismatch.

## Placebo Checks

Pre-filing placebo outcomes:

```text
CAR_m10_m6
CAR_m5_m2
AbnormalVolume_m5_m2
```

If AI-related disclosure measures predict post-filing reactions but not pre-filing placebo windows, the evidence is more consistent with a filing-window market response interpretation. The current placebo models failed to estimate due to the CIK padding mismatch.

## Reproduction Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the event-study pipeline:

```bash
python scripts/prepare_market_reaction_extension_scaffold.py
python scripts/collect_market_data_for_10k_event_study.py
python scripts/estimate_10k_event_study_market_reactions.py
python scripts/run_10k_ai_causal_event_study_regressions.py
```

Validate scripts:

```bash
python -m py_compile \
  scripts/collect_market_data_for_10k_event_study.py \
  scripts/estimate_10k_event_study_market_reactions.py \
  scripts/run_10k_ai_causal_event_study_regressions.py

git diff --check
```

## Generated Outputs

| File | Current status |
| --- | --- |
| `data/derived/market_extension/daily_market_data_10k_events.csv` | Generated, ~73k rows in current run |
| `data/derived/market_extension/market_data_collection_report.csv` | Generated, documents market-data collection sources |
| `data/derived/market_extension/post_filing_market_reaction_estimates.csv` | Generated, event estimates with CAR outputs |
| `data/derived/market_extension/event_study_estimation_diagnostics.csv` | Generated, diagnostic estimates |
| `data/derived/causal/ai_10k_event_study_analysis_dataset.csv` | Generated, 273 rows |
| `data/derived/causal/causal_event_study_regression_summary.csv` | Generated, failed model rows |
| `data/derived/causal/causal_event_study_model_diagnostics.csv` | Generated, failed model diagnostics |
| `data/derived/causal/placebo_pre_filing_checks.csv` | Generated, failed placebo rows |

## Limitations

- While market data collection succeeded, regression outputs and placebo checks failed to estimate due to a CIK padding mismatch that prevented joining the market outcomes with the AI text measures. No causal inference is currently possible.
- AI disclosure measures are text-based communication proxies, not direct AI adoption measures.
- Topic labels are machine-generated/topic-derived labels, not human-validated coding.
- Sector categories are approximate SEC SIC-derived NAICS enrichment, not fully verified firm-level NAICS classifications.
- A causal interpretation requires successful market data collection, event-study diagnostics, placebo checks, and transparent identification limitations.
