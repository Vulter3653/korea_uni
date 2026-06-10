# Fortune 2025 Top 100 10-K Collection Pipeline Status

## 1. Purpose

This document records the current status of the Fortune 2025 top 100 SEC 10-K collection work that was first implemented in `Vulter3653/x_scrapper` and should also be reflected in this repository for Korea University project continuity.

The goal is not to claim that the full 10-K HTML corpus has already been collected. The current verified status is that a reproducible collection pipeline, manifest structure, and audit trail have been prepared. Actual 10-K HTML report files still require execution in an SEC-accessible environment or the provision of SEC source/cache files.

## 2. Source Repository

Primary implementation repository:

```text
https://github.com/Vulter3653/x_scrapper
```

Related implemented files in the source repository:

```text
scripts/collect_fortune2025_10k_reports.py
.github/workflows/collect-fortune-10k.yml
config/fortune2025_top100_10k_report_index.csv
data/audit/fortune2025_top100_10k_report_audit.csv
README.md
PROJECT_HISTORY.md
TROUBLESHOOTING_AND_DEBUGGING_LOG.md
```

## 3. Collection Scope

Target company universe:

```text
Fortune 2025 top 100 firms
```

Target report years:

```text
2025, 2024, 2023
```

Expected manifest rows:

```text
100 firms x 3 years = 300 rows
```

SEC source flow:

```text
1. https://www.sec.gov/files/company_tickers.json
2. https://data.sec.gov/submissions/CIK##########.json
3. https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primaryDocument}
```

## 4. Current Verified Status

The pipeline has been created and the GitHub Actions workflow has been added in the source repository. The latest workflow produced manifest and audit artifacts, but the current execution environment returned SEC access failures. Therefore, the artifact currently contains the manifest/audit outputs, not the downloaded 10-K HTML report files.

Current status summary:

| Item | Status |
| --- | --- |
| Fortune 2025 top 100 target definition | Completed |
| 2025/2024/2023 target year definition | Completed |
| SEC CIK/submissions/archive URL flow | Implemented |
| Manifest/index CSV generation | Implemented |
| Failure audit CSV generation | Implemented |
| GitHub Actions workflow | Implemented |
| Actual 10-K HTML report download | Not completed in current environment |

Important wording:

```text
The current repository state should be described as "10-K collection pipeline and audit structure completed," not as "10-K corpus collection completed."
```

## 5. GitHub Actions Record from Source Repository

Recorded workflow runs:

```text
Failed run: 27269441863
Successful reinforced run: 27269654293
Artifact: fortune-2025-top100-10k-reports
```

Current artifact status:

```text
Contains manifest/audit files only. It does not yet contain the actual 10-K HTML reports.
```

Recorded source commits:

```text
33c899e Add Fortune top 100 10-K collection workflow
24351b1 Record SEC 10-K source access failures
ad66490 Update Fortune 2025 top 100 10-K report index
df5cd43 Document SEC 10-K access status
```

## 6. Required Next Step

The next step is to rerun the same pipeline in an SEC-accessible environment or provide SEC source/cache files.

Recommended execution route:

```text
1. Run the collector locally, on a school/research network, in Colab, or in another cloud environment.
2. If direct SEC access still fails, provide cached SEC files:
   - data/sec_cache/company_tickers.json
   - data/sec_cache/submissions/CIK##########.json
3. Reuse the existing manifest/audit format.
4. Confirm whether each failure is caused by 403, 404, 429, URL-generation error, or file-save error.
```

## 7. Defensive Research Statement

Use the following statement when reporting the current status:

```text
At this stage, the project has not completed the full 10-K HTML corpus. Instead, it has completed a reproducible Fortune 2025 top 100 10-K collection pipeline, manifest generation process, and audit logging structure. Due to SEC access restrictions in the current execution environment, actual 10-K HTML files must be downloaded by rerunning the same script in an SEC-accessible environment or by injecting SEC company ticker/submissions cache files.
```
