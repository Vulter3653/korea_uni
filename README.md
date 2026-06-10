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
| AI adoption dashboard | `ai_adoption_news_dashboard.html` | Active dashboard page |
| README | `README.md` | Updated with project-local status summary and Pages link |
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

Accurate project wording:

```text
The korea_uni repository contains the AI adoption news dashboard, with the public Pages root URL set as https://korea-uni.pages.dev/ and the repository root index.html redirecting to ai_adoption_news_dashboard.html.
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
| Required next step | Rerun in an SEC-accessible environment or inject SEC cache files |

Accurate project wording:

```text
Fortune 2025 top 100 10-K collection pipeline and audit structure are documented for korea_uni; actual 10-K HTML corpus completion still requires rerun in an SEC-accessible environment or SEC cache injection.
```

Detailed project-local status note:

```text
docs/fortune2025_10k_pipeline_status.md
```

## Original IDX Note

Get started by customizing your environment, defined in the `.idx/dev.nix` file, with the tools and IDE extensions needed for the project.

Learn more from the Google IDX guide.
