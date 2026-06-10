# Fortune 2025 Top 10 10-K Smoke Test

## Purpose

This smoke test validates the 10-K collection pipeline before scaling to the full Fortune 2025 Top 100 sample.

The immediate research direction is to measure **AI disclosure intensity in 10-K reports**. Before calculating AI-related text metrics for the full sample, the project first checks whether SEC retrieval, 10-K filing selection, document URL construction, HTML download, text extraction, and audit logging work on a small controlled sample.

## Test Scope

| Item | Scope |
| --- | --- |
| Sample | Fortune 2025 Top 10 firms |
| Target report years | 2023, 2024, 2025 |
| Expected rows | 10 firms x 3 years = 30 firm-year filings |
| Primary source | SEC EDGAR submissions and archives |
| Unit | Firm-report-year |
| Main script | `scripts/collect_fortune2025_top10_10k_test.py` |
| Seed file | `config/fortune2025_top10_10k_test_seed.csv` |
| GitHub Actions workflow | `.github/workflows/collect-fortune-top10-10k-smoke-test.yml` |

## Seed Firms

| Rank | Company | Ticker | CIK |
| ---: | --- | --- | --- |
| 1 | Walmart | WMT | 0000104169 |
| 2 | Amazon | AMZN | 0001018724 |
| 3 | UnitedHealth Group | UNH | 0000731766 |
| 4 | Apple | AAPL | 0000320193 |
| 5 | CVS Health | CVS | 0000064803 |
| 6 | Berkshire Hathaway | BRK-B | 0001067983 |
| 7 | Alphabet | GOOGL | 0001652044 |
| 8 | ExxonMobil | XOM | 0000034088 |
| 9 | McKesson | MCK | 0000927653 |
| 10 | Cencora | COR | 0001140859 |

## Collection Logic

```text
1. Read the Fortune 2025 Top 10 seed file.
2. Query SEC submissions JSON by CIK.
3. Filter recent filings to form = 10-K.
4. Select target report years 2023, 2024, and 2025 by reportDate.
5. Construct SEC Archives document URLs from CIK, accession number, and primary document.
6. Download the 10-K HTML.
7. Convert HTML to plain text.
8. Compute preliminary AI keyword metrics.
9. Write manifest and audit files.
```

The script uses `reportDate` as the target-year basis. This is intentional because a fiscal-year 2025 10-K may be filed in 2026.

## Required Environment Variable

SEC requests should use a descriptive User-Agent.

```bash
export SEC_USER_AGENT="Seung Hyun Choi korea_uni research shch3653@g.skku.edu"
```

## Run Command

From the repository root:

```bash
python scripts/collect_fortune2025_top10_10k_test.py
```

## GitHub Actions Run

The workflow can also be run manually from the GitHub Actions tab.

```text
Workflow name: Collect Fortune 2025 Top 10 10-K Smoke Test
Input sec_user_agent default: Seung Hyun Choi korea_uni research shch3653@g.skku.edu
Input request_sleep_seconds default: 0.25
```

The workflow uploads results as an artifact named:

```text
fortune2025-top10-10k-smoke-test-output
```

## Expected Outputs

```text
data/processed/fortune2025_top10_10k_test_manifest.csv
data/audit/fortune2025_top10_10k_test_audit.csv
data/raw/sec_10k_html/test_top10/<TICKER>/<YEAR>_<TICKER>_10k.html
data/processed/sec_10k_text/test_top10/<TICKER>/<YEAR>_<TICKER>_10k.txt
```

## Manifest Fields

| Field | Meaning |
| --- | --- |
| `fortune_rank_2025` | Fortune 2025 rank in the Top 10 test seed |
| `company_name` | Company name |
| `ticker` | Ticker used for SEC mapping |
| `cik` / `cik_padded` | SEC CIK identifiers |
| `target_report_year` | 2023, 2024, or 2025 |
| `form_type` | Expected to be 10-K |
| `filing_date` | Actual SEC filing date |
| `report_date` | Fiscal/report period date used for target-year assignment |
| `accession_number` | SEC accession number |
| `primary_document` | Main 10-K HTML document filename |
| `sec_filing_url` | SEC Archives filing directory |
| `sec_document_url` | Direct 10-K HTML document URL |
| `local_html_path` | Saved HTML path |
| `local_text_path` | Saved plain-text path |
| `download_status` | `success`, `missing`, or `failed` |
| `failure_reason` | Documented reason when retrieval fails |
| `total_words` | Preliminary word count after HTML-to-text conversion |
| `ai_keyword_count` | Preliminary AI keyword count |
| `ai_keyword_per_10k_words` | AI keyword count normalized per 10,000 words |

## Success Criterion

The smoke test is successful when the pipeline produces 30 manifest rows.

```text
Expected rows = 30
Success rows + documented missing/failed rows = 30
```

All failures must be represented in the audit file with a specific failure reason.

## Interpretation

This is a pipeline validation step, not the final empirical analysis. The AI keyword variables generated here are preliminary diagnostics used to verify that the corpus can support later AI disclosure intensity analysis.

The full analysis should later extend the measurement to:

- AI disclosure intensity
- AI topic concentration
- AI opportunity framing
- AI risk framing
- AI specificity score
- market reaction around 10-K filing dates
