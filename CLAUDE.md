# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Hong Kong property price data analysis. Fetches data from multiple online sources, cleans and standardises into a unified base format, and enables analysis.

## Package Management

Use `uv` for all Python package management.

```bash
uv add <package>          # add dependency
uv run <script>           # run script in project venv
uv sync                   # install all deps
uv run pytest             # run tests
uv run pytest tests/path/test_file.py::test_name  # single test
```

## Architecture

### Core Concept: Multi-Source Pipelines → Unified Base Format

Each data source gets its own pipeline that fetches, cleans, and transforms raw data into a shared base schema. Pipelines are independent; base format is the contract between them.

```
sources/
  <source_name>/
    fetcher.py      # HTTP requests to source API
    parser.py       # raw response → source-specific model
    pipeline.py     # orchestrates fetch → parse → transform → base
models/
  base.py           # shared property record schema (the contract)
  <source>.py       # source-specific intermediate models
data/               # raw and processed data storage
```

### Pipeline Pattern

Each pipeline should:
1. Fetch raw data (handle pagination, rate limits)
2. Parse into source-specific model
3. Transform to base format
4. Output standardised records

### API Integration

APIs are provided by the user from browser inspection. When adding a new source:
- Inspect request headers, cookies, pagination params from browser
- Model the request exactly (user-agent, headers, query params)
- Handle pagination to get full dataset
- Document the API endpoint and key params in the source's module docstring
