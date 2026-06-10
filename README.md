# Korea University Research Project Repository

This repository records Korea University research-project materials, implementation notes, and project-local data-pipeline status.

## Project Boundary

This repository is an independent project repository.

```text
Repository: https://github.com/Vulter3653/korea_uni
Default project scope: Korea University research project materials and related documentation
```

Important distinction:

```text
Vulter3653/korea_uni and Vulter3653/x_scrapper are separate projects.
The 10-K status recorded here must be managed as korea_uni project documentation, not as an x_scrapper submodule, mirror, or dependent workflow.
```

## Internal Project Links

| Item | korea_uni path | Status |
| --- | --- | --- |
| Main repository | `https://github.com/Vulter3653/korea_uni` | Active |
| README | `README.md` | Updated with project-local status summary |
| 10-K pipeline status note | `docs/fortune2025_10k_pipeline_status.md` | Active documentation |
| Original IDX environment note | `.idx/dev.nix` | Environment customization reference |

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
