# Korea University Research Project Repository

This repository records research-project materials and implementation notes for Korea University coursework and related data-pipeline work.

## Fortune 2025 Top 100 10-K Pipeline Status

The Fortune 2025 top 100 SEC 10-K collection work should be reflected in this repository as project documentation.

Current verified status:

- Target universe: Fortune 2025 top 100 firms.
- Target report years: 2025, 2024, 2023.
- Expected manifest size: 100 firms x 3 years = 300 rows.
- Current output status: manifest/index and failure audit files have been generated in the source implementation repository.
- Current limitation: actual 10-K HTML report files have not yet been downloaded because the current execution environment returned SEC access failures.

Accurate project wording:

```text
Fortune 2025 top 100 10-K collection pipeline and audit structure completed; actual 10-K HTML corpus requires rerun in an SEC-accessible environment or SEC cache injection.
```

Detailed status note:

```text
docs/fortune2025_10k_pipeline_status.md
```

## Original IDX Note

Get started by customizing your environment, defined in the `.idx/dev.nix` file, with the tools and IDE extensions needed for the project.

Learn more from the Google IDX guide.
