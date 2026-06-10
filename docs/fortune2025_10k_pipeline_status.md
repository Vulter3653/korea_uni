# Fortune 2025 Top 100 10-K Pipeline Status

## 1. Project Boundary

This document records the current Fortune 2025 Top 100 SEC 10-K collection and sample status for the `korea_uni` repository.

```text
Repository: https://github.com/Vulter3653/korea_uni
Project boundary: independent Korea University research-project repository
```

Important distinction:

```text
Vulter3653/korea_uni and Vulter3653/x_scrapper are separate projects.
This document should not describe korea_uni as a mirror, submodule, or dependent copy of x_scrapper.
```

## 2. Current Final Dataset Status

The current repository contains the final Fortune 2025 Top 100 x 2023-2025 manifest and sample decision files.

| Item | Current status |
| --- | --- |
| Target universe | Fortune 2025 Top 100 firms |
| Target report years | 2023, 2024, 2025 |
| Master frame | 300 firm-year rows |
| Primary observed 10-K text sample | 273 successful 10-K text rows |
| Balanced observed text panel | 270 firm-year rows |
| Final audit / non-success rows | 27 firm-year rows |
| Missingness treatment | Non-success rows are retained in the final audit classification |

This is a final dataset stage for the current collection track, with documented missingness. It should not be described as complete text coverage for all 300 firm-year rows.

## 3. Sample Definitions

| Sample | Definition | Firm-year count | Use |
| --- | --- | ---: | --- |
| `MASTER_FRAME` | 100 firms x 3 report years | 300 | Full denominator and collection coverage frame |
| `PRIMARY_TEXT_SAMPLE` | Successful 10-K text rows | 273 | Main 10-K AI disclosure / AI communication text analysis |
| `BALANCED_TEXT_PANEL` | Firms with successful observed text for all three years | 270 | Within-firm robustness panel |
| `FINAL_AUDIT` | Non-success rows | 27 | Missingness documentation and sensitivity checks |

Additional downstream topic-analysis subset:

```text
246 firm-year rows have at least one AI mention window under the selected K=5 topic solution.
```

The 246-row K=5 topic sample is a downstream AI-window/topic-model analysis sample, not the collection master frame.

## 4. File Inventory

Core final sample and audit files:

| File | Role |
| --- | --- |
| `data/processed/fortune2025_top100_10k_final_manifest.csv` | 300-row final collection manifest |
| `data/processed/fortune2025_top100_10k_final_sample_decision.csv` | Sample definitions and inclusion rules |
| `data/audit/fortune2025_top100_10k_final_audit_classification.csv` | 27-row non-success audit classification |

Downstream analysis and topic-model files:

| File | Role |
| --- | --- |
| `data/processed/fortune2025_top100_final_ai_analysis_master.csv` | Final 300-row analysis master |
| `data/processed/fortune2025_top100_final_ai_analysis_text_sample.csv` | 273-row observed text analysis sample |
| `data/processed/fortune2025_top100_final_ai_analysis_k5_topic_sample.csv` | 246-row K=5 AI-window topic sample |
| `data/audit/fortune2025_top100_final_ai_analysis_dataset_summary.csv` | Final analysis dataset summary |
| `data/processed/fortune2025_top100_k5_ai_topic_analysis_dataset.csv` | K=5 topic-analysis dataset |
| `data/audit/10k_ai_topics/k5_ai_topic_analysis_dataset_summary.csv` | K=5 topic-analysis summary |

## 5. Audit and Missingness Treatment

The final manifest keeps the full 300 firm-year sampling frame. The observed primary text sample includes 273 successful 10-K text rows. The final audit classification retains 27 non-success rows.

The non-success rows are not silently dropped. They are retained as documented missingness and should be considered when reporting sample construction, coverage, and robustness.

Current audit structure:

| Audit category | Treatment |
| --- | --- |
| Firms with no collected 10-K text across all three years | Retain in the master frame and classify as missing across all three years |
| Firms with partial 10-K missingness | Retain observed years in text analysis and retain missing years in audit documentation |
| Non-success firm-year rows | Treat as missing values with row-level audit classification |

## 6. Remaining Limitations

The dataset is suitable for 10-K AI disclosure / AI communication text analysis.

Remaining limitations:

| Limitation | Current status |
| --- | --- |
| External reactions | Media response, analyst response, SNS response, and market reaction are not yet measured in the current repository |
| SIC/NAICS in final manifest | Industry codes such as SIC/NAICS are not yet joined to the final manifest file itself |
| Dashboard alignment | Dashboard content is not yet fully aligned with the current 10-K AI communication research direction |
| Workflow hardening | Some workflows may still directly push generated outputs; workflow hardening is a later task |
| Incomplete text coverage | 27 non-success firm-year rows remain in the audit frame |

## 7. Recommended Next Steps

Recommended next steps:

1. Keep the 300-row master frame and 27-row audit classification attached to any reported analysis.
2. Use the 273-row primary text sample for main 10-K AI disclosure / AI communication text analysis.
3. Use the 270-row balanced text panel for within-firm robustness checks.
4. Use the 246-row K=5 AI-window/topic-model sample only when the analysis requires observed AI mention windows.
5. Decide whether SIC/NAICS enrichment should be joined directly into the final manifest or remain in downstream analysis files.
6. Align the public dashboard with the current 10-K AI communication research direction in a later task.
7. Harden workflows that directly commit and push generated outputs.

## 8. Defensive Research Statement

Use the following statement when reporting the current status:

```text
The current repository contains the final Fortune 2025 Top 100 x 2023-2025 manifest and sample decision files. The master frame contains 300 firm-year rows, the observed primary text sample contains 273 successful 10-K text rows, the balanced text panel contains 270 rows, and 27 non-success rows are retained in the final audit classification. The dataset is suitable for 10-K AI disclosure / AI communication text analysis, but it should not be described as complete observed 10-K text coverage for all 300 firm-year rows.
```
