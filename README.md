# Korea University Research Project Repository

This repository records Korea University research-project materials, implementation notes, dashboard files, and project-local data-pipeline status.

## Project Boundary

This repository is an independent project repository.

```text
Repository: https://github.com/Vulter3653/korea_uni
Default project scope: Korea University research project materials, dashboard pages, and related documentation
```

Important distinction:

```text
Vulter3653/korea_uni and Vulter3653/x_scrapper are separate projects.
The 10-K status recorded here must be managed as korea_uni project documentation, not as an x_scrapper submodule, mirror, or dependent workflow.
```

## Current Research Direction

The project is being redirected from a news-organization AI adoption dashboard prototype toward a 10-K text-analysis design.

Current working direction:

```text
Measure AI disclosure intensity in 10-K reports and examine whether stronger AI-related disclosure functions as a market signal.
```

Immediate collection target:

```text
Fortune 2025 Top 10 smoke test first, then scale to Fortune 2025 Top 100.
```

## Deployed Dashboard

The project dashboard is deployed through Cloudflare Pages.

```text
Primary Pages URL: https://korea-uni.pages.dev/
Dashboard file: ai_adoption_news_dashboard.html
Repository entry point: index.html
```

Connection structure:

```text
https://korea-uni.pages.dev/
  -> index.html
  -> ./ai_adoption_news_dashboard.html
```

The root `index.html` file redirects visitors to `./ai_adoption_news_dashboard.html`, which contains the dashboard titled **AI Adoption Types in News Organizations and Stock Market Reactions**.

Dashboard scope:

| Item | Description |
| --- | --- |
| Research topic | AI adoption types in news organizations and stock market reactions |
| Treatment types | No AI adoption, AI-assisted adoption, AI-writing adoption |
| Main methods | Event study and multi-valued DID |
| Main outcomes | Abnormal return, cumulative abnormal return, abnormal volume |
| Public URL | `https://korea-uni.pages.dev/` |
| Local dashboard file | `ai_adoption_news_dashboard.html` |

Operational note:

```text
If the root Pages URL loads correctly in a browser, the deployment should be treated as the canonical public dashboard link.
If a direct tool/browser check returns a transient Cloudflare cache miss, verify the repository entry point and Pages deployment status before changing the dashboard path.
```

## Internal Project Links

| Item | korea_uni path | Status |
| --- | --- | --- |
| Main repository | `https://github.com/Vulter3653/korea_uni` | Active |
| Public dashboard | `https://korea-uni.pages.dev/` | Canonical Pages link |
| Pages entry point | `index.html` | Redirects to dashboard HTML |
| AI adoption dashboard | `ai_adoption_news_dashboard.html` | Active prototype page |
| README | `README.md` | Updated with project-local status summary and Pages link |
| Top 10 10-K smoke-test seed | `config/fortune2025_top10_10k_test_seed.csv` | Active test input |
| Top 10 10-K smoke-test collector | `scripts/collect_fortune2025_top10_10k_test.py` | Ready to run in SEC-accessible environment |
| Top 10 10-K smoke-test workflow | `.github/workflows/collect-fortune-top10-10k-smoke-test.yml` | Manual GitHub Actions workflow |
| Top 10 10-K smoke-test note | `docs/fortune2025_top10_10k_smoke_test.md` | Active documentation |
| 10-K pipeline status note | `docs/fortune2025_10k_pipeline_status.md` | Active documentation |
| Original IDX environment note | `.idx/dev.nix` | Environment customization reference |

## AI Adoption News Dashboard Status

The current dashboard records a quasi-experimental research design for analyzing how different AI adoption types in news organizations may relate to stock market reactions.

Current verified repository status:

| Item | Status |
| --- | --- |
| Dashboard title | AI Adoption Types in News Organizations and Stock Market Reactions |
| Deployment URL | `https://korea-uni.pages.dev/` |
| Root redirect | `index.html` redirects to `./ai_adoption_news_dashboard.html` |
| Main dashboard file | `ai_adoption_news_dashboard.html` |
| Treatment structure | `AI_Type = 0` no AI, `AI_Type = 1` AI-assisted, `AI_Type = 2` AI-writing |
| Research design | Event study + multi-valued DID |
| Key outcome variables | AR, CAR, abnormal volume |
| Status | Dashboard file exists in the repository and is linked from the root entry point |

Important methodological update:

```text
The dashboard remains a prototype. The active data-collection direction is now 10-K AI disclosure intensity rather than journalist-, article-, or broadcaster-level AI adoption coding.
```

## Fortune 2025 Top 10 10-K Smoke Test

A Top 10 smoke-test collection setup has been added before scaling to the full Top 100 sample.

| Item | Status |
| --- | --- |
| Test universe | Fortune 2025 top 10 firms |
| Target report years | 2025, 2024, 2023 |
| Expected manifest size | 10 firms x 3 years = 30 rows |
| Seed file | `config/fortune2025_top10_10k_test_seed.csv` |
| Collector script | `scripts/collect_fortune2025_top10_10k_test.py` |
| GitHub Actions workflow | `.github/workflows/collect-fortune-top10-10k-smoke-test.yml` |
| Documentation | `docs/fortune2025_top10_10k_smoke_test.md` |
| Selection basis | `reportDate` / fiscal report period year, not filing-date year |
| Expected outputs | manifest CSV, audit CSV, raw HTML files, cleaned text files |
| Preliminary metric | AI keyword count and AI keywords per 10,000 words |
| Status | Ready to run in SEC-accessible environment |

Run command:

```bash
export SEC_USER_AGENT="Seung Hyun Choi korea_uni research shch3653@g.skku.edu"
python scripts/collect_fortune2025_top10_10k_test.py
```

GitHub Actions manual run:

```text
Workflow: Collect Fortune 2025 Top 10 10-K Smoke Test
Input sec_user_agent default: Seung Hyun Choi korea_uni research shch3653@g.skku.edu
Input request_sleep_seconds default: 0.25
Artifact: fortune2025-top10-10k-smoke-test-output
```

Expected output files:

```text
data/processed/fortune2025_top10_10k_test_manifest.csv
data/audit/fortune2025_top10_10k_test_audit.csv
data/raw/sec_10k_html/test_top10/<TICKER>/<YEAR>_<TICKER>_10k.html
data/processed/sec_10k_text/test_top10/<TICKER>/<YEAR>_<TICKER>_10k.txt
```

Success criterion:

```text
Expected rows = 30
Success rows + documented missing/failed rows = 30
```

Accurate project wording:

```text
The current first-stage task is a Fortune 2025 Top 10 smoke test for 2023-2025 10-K reports. The purpose is to validate SEC retrieval, 10-K filing selection, document URL construction, HTML download, text extraction, preliminary AI keyword counting, and audit logging before scaling to Fortune 2025 Top 100.
```

## Fortune 2025 Top 100 10-K Pipeline Status

The Fortune 2025 top 100 SEC 10-K collection task is recorded here as part of the `korea_uni` project documentation.

Current verified status:

| Item | Status |
| --- | --- |
| Target universe | Fortune 2025 top 100 firms |
| Target report years | 2025, 2024, 2023 |
| Expected manifest size | 100 firms x 3 years = 300 rows |
| Collection design | SEC company tickers, SEC submissions metadata, SEC Archives document URL flow |
| Manifest/index status | Prepared as pipeline target structure |
| Audit status | Failure/status audit structure prepared |
| Actual 10-K HTML corpus | Not yet completed in the current execution environment |
| Required next step | Run Top 10 smoke test first; then scale in an SEC-accessible environment or inject SEC cache files |

Accurate project wording:

```text
Fortune 2025 top 100 10-K collection pipeline and audit structure are documented for korea_uni; actual full 10-K HTML corpus completion still requires the Top 10 smoke test and then a full rerun in an SEC-accessible environment or SEC cache injection.
```

Detailed project-local status notes:

```text
docs/fortune2025_top10_10k_smoke_test.md
docs/fortune2025_10k_pipeline_status.md
```

## Original IDX Note

Get started by customizing your environment, defined in the `.idx/dev.nix` file, with the tools and IDE extensions needed for the project.

Learn more from the Google IDX guide.
