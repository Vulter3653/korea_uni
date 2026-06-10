# Fortune 2025 Top 100 10-K Pipeline Status

## 1. Project Boundary

This document records the Fortune 2025 top 100 SEC 10-K collection status for the `korea_uni` repository.

```text
Repository: https://github.com/Vulter3653/korea_uni
Project boundary: independent Korea University research-project repository
```

Important distinction:

```text
Vulter3653/korea_uni and Vulter3653/x_scrapper are separate projects.
This document should not describe korea_uni as a mirror, submodule, or dependent copy of x_scrapper.
```

The current goal is not to claim that the full 10-K HTML corpus has already been collected. The verified status is that the project has documented the intended collection scope, SEC source flow, manifest/audit logic, current access limitation, and required next execution step.

## 2. korea_uni Internal Links

| Item | korea_uni path | Status |
| --- | --- | --- |
| Main repository | `https://github.com/Vulter3653/korea_uni` | Active |
| README | `README.md` | Updated |
| 10-K status note | `docs/fortune2025_10k_pipeline_status.md` | Active |
| Future manifest location | `config/fortune2025_top100_10k_report_index.csv` | To be added when generated inside korea_uni |
| Future audit location | `data/audit/fortune2025_top100_10k_report_audit.csv` | To be added when generated inside korea_uni |
| Future SEC cache location | `data/sec_cache/` | Optional rerun support |

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
1. SEC company tickers source
2. SEC company submissions metadata by CIK
3. SEC Archives primary 10-K filing document URL
```

## 4. Current Verified Status in korea_uni

Current status summary:

| Item | Status |
| --- | --- |
| Fortune 2025 top 100 target definition | Documented |
| 2025/2024/2023 target year definition | Documented |
| SEC source flow | Documented |
| Manifest/index CSV inside korea_uni | Not yet generated in this repository |
| Failure audit CSV inside korea_uni | Not yet generated in this repository |
| GitHub Actions workflow inside korea_uni | Not yet added in this repository |
| Actual 10-K HTML report download | Not completed in this repository |

Important wording:

```text
The current korea_uni state should be described as "10-K collection scope and status documented," not as "10-K corpus collection completed."
```

## 5. Current Limitation

Actual SEC 10-K HTML report files are not yet present in this repository. The next implementation step must either:

```text
1. Add and run a korea_uni-local collector script and workflow in an SEC-accessible environment; or
2. Provide SEC source/cache files and generate the manifest/audit locally within korea_uni.
```

Recommended future cache structure:

```text
data/sec_cache/company_tickers.json
data/sec_cache/submissions/CIK##########.json
```

Recommended future output structure:

```text
config/fortune2025_top100_10k_report_index.csv
data/audit/fortune2025_top100_10k_report_audit.csv
data/sec_10k_reports/{rank}_{company_slug}_{year}_10k.html
```

## 6. Required Next Step

The next step for `korea_uni` is implementation within this repository, not reliance on another repository.

Recommended execution route:

```text
1. Add a korea_uni-local SEC 10-K collector script.
2. Generate the 300-row Fortune 2025 top 100 x 3-year manifest in korea_uni.
3. Generate a failure/status audit file in korea_uni.
4. If SEC access is blocked, record the failure stage and HTTP status.
5. Rerun in an SEC-accessible environment or inject SEC cache files.
```

## 7. Defensive Research Statement

Use the following statement when reporting the current status:

```text
At this stage, korea_uni has documented the Fortune 2025 top 100 10-K collection scope, expected manifest structure, SEC source flow, and current corpus limitation. The full 10-K HTML corpus is not yet completed inside this repository. Completion requires a korea_uni-local rerun in an SEC-accessible environment or SEC cache injection followed by manifest and audit generation.
```
