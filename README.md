# Korea University Research Project Repository

This repository records Korea University research-project materials, dashboard files, documentation, and project-local data-pipeline status.

## 1. Project Boundary

This repository is an independent project repository.

```text
Repository: https://github.com/Vulter3653/korea_uni
Default project scope: Korea University research project materials, dashboard pages, documentation, and project-local data files
```

Important distinction:

```text
Vulter3653/korea_uni and Vulter3653/x_scrapper are separate projects.
The 10-K status recorded here must be managed as korea_uni project documentation, not as an x_scrapper submodule, mirror, or dependent workflow.
```

## 2. Current Research Direction

The repository focus is now Fortune 2025 Top 100 firms AI communication in 10-K reports.

Current working direction:

```text
Measure AI disclosure intensity and AI communication patterns in 10-K reports, then use those text measures as a basis for later empirical analysis.
```

The project is no longer merely at the preliminary Top 10 smoke-test stage before Top 100 scaling. The current repository contains the final Fortune 2025 Top 100 x 2023-2025 manifest and sample decision files.

## 3. Current 10-K Dataset Status

The current repository is at the final dataset stage for the Fortune 2025 Top 100 10-K collection track.

| Item | Current status |
| --- | --- |
| Target frame | Fortune 2025 Top 100 x report years 2023-2025 |
| Master frame | 300 firm-year rows |
| Primary observed 10-K text sample | 273 successful 10-K text rows |
| Balanced observed text panel | 270 firm-year rows |
| Final audit / non-success rows | 27 firm-year rows |
| Missingness treatment | Non-success rows are retained in audit documentation, not silently dropped |

Recommended wording:

```text
The current repository contains the final Fortune 2025 Top 100 x 2023-2025 manifest and sample decision files. The master frame contains 300 firm-year rows, the observed primary text sample contains 273 successful 10-K text rows, the balanced text panel contains 270 rows, and 27 non-success rows are retained in the final audit classification.
```

Do not describe the dataset as if every Fortune 2025 Top 100 firm-year has successful observed 10-K text. The audit frame still contains 27 non-success firm-year rows.

## 4. Deployed Dashboard Status

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

The dashboard content is currently mixed with legacy news-organization AI adoption material and a newer 10-K sample update. Dashboard alignment with the current 10-K AI communication research direction should be handled in a later task. This document update does not modify the dashboard.

## 5. Internal Project Links

| Item | korea_uni path | Status |
| --- | --- | --- |
| Main repository | `https://github.com/Vulter3653/korea_uni` | Active |
| Public dashboard | `https://korea-uni.pages.dev/` | Canonical Pages link |
| Pages entry point | `index.html` | Redirects to dashboard HTML |
| Dashboard file | `ai_adoption_news_dashboard.html` | Active, mixed/legacy content |
| README | `README.md` | Current repository status summary |
| 10-K pipeline status note | `docs/fortune2025_10k_pipeline_status.md` | Current final dataset status report |
| Final manifest | `data/processed/fortune2025_top100_10k_final_manifest.csv` | Present |
| Final sample decision | `data/processed/fortune2025_top100_10k_final_sample_decision.csv` | Present |
| Final audit classification | `data/audit/fortune2025_top100_10k_final_audit_classification.csv` | Present |
| Final analysis master | `data/processed/fortune2025_top100_final_ai_analysis_master.csv` | Present |
| Final analysis text sample | `data/processed/fortune2025_top100_final_ai_analysis_text_sample.csv` | Present |
| Final K=5 topic sample | `data/processed/fortune2025_top100_final_ai_analysis_k5_topic_sample.csv` | Present |
| Original IDX environment note | `.idx/dev.nix` | Environment customization reference |

## 6. Final Sample Structure

| Sample | Definition | Firm count | Firm-year count | Primary use |
| --- | --- | ---: | ---: | --- |
| `MASTER_FRAME` | All Fortune 2025 Top 100 firms x report years 2023-2025 | 100 | 300 | Coverage and audit denominator |
| `PRIMARY_TEXT_SAMPLE` | `download_status = success` in the final manifest | 92 | 273 | Main 10-K AI disclosure text analysis |
| `BALANCED_TEXT_PANEL` | Firms with successful observed 10-K text for all three years | 90 | 270 | Robustness panel |
| `FINAL_AUDIT` | `download_status != success` in the final manifest | 10 | 27 | Missingness documentation and sensitivity checks |

Downstream AI-window/topic-analysis sample:

```text
246 firm-year rows have at least one AI mention window under the selected K=5 topic solution.
```

This 246-row sample is a downstream topic-analysis subset. It is not the same as the 300-row master frame or the 273-row observed text sample.

## 7. Data and Audit Files

Core 10-K collection status files:

```text
data/processed/fortune2025_top100_10k_final_manifest.csv
data/processed/fortune2025_top100_10k_final_sample_decision.csv
data/audit/fortune2025_top100_10k_final_audit_classification.csv
```

Downstream analysis files:

```text
data/processed/fortune2025_top100_final_ai_analysis_master.csv
data/processed/fortune2025_top100_final_ai_analysis_text_sample.csv
data/processed/fortune2025_top100_final_ai_analysis_k5_topic_sample.csv
data/audit/fortune2025_top100_final_ai_analysis_dataset_summary.csv
data/processed/fortune2025_top100_k5_ai_topic_analysis_dataset.csv
data/audit/10k_ai_topics/k5_ai_topic_analysis_dataset_summary.csv
```

The final audit classification retains non-success firm-year rows. Missing rows are part of the documented sample frame and should not be treated as if they were silently excluded.

## 8. Current Limitations

The dataset is suitable for 10-K AI disclosure / AI communication text analysis.

Current limitations:

| Limitation | Status |
| --- | --- |
| External reactions | Media response, analyst response, SNS response, and market reaction are not yet measured in the current repository |
| Industry codes in final manifest | SIC/NAICS industry codes are not yet joined to the final manifest file itself |
| Dashboard alignment | Dashboard content is not yet fully aligned with the current 10-K AI communication research direction |
| Workflow hardening | Some workflows may still directly push generated outputs; workflow hardening is a later task |
| Missing 10-K text rows | 27 non-success firm-year rows remain in the audit frame |

## 9. Next Work Plan

Recommended next work:

1. Align the dashboard content with the current 10-K AI communication research direction.
2. Add or document external reaction variables only after measurable data sources are selected.
3. Decide whether industry-code enrichment should be joined directly into the final manifest or kept in downstream analysis files.
4. Harden GitHub Actions workflows that commit generated outputs directly.
5. Keep the final audit classification attached to any analysis that uses the observed text sample.
