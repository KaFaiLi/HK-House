# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Purpose

Hong Kong property price data analysis. Fetches data from multiple online sources, cleans and standardises into a unified base format, and enables analysis.

The project now supports two related data families:
- Listing sources, such as Midland, House730, Centaline, and 28Hse.
- Bank valuation sources, starting with Hang Seng e-Valuation.

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

Listing pipelines can crawl broad result sets. Bank valuation pipelines should be request-driven unless the user explicitly asks for and approves a broader crawl, because valuation APIs often require walking a large address tree and may throttle aggressively.

### Bank Valuation Sources

Bank valuation sources live under the same source layout:

```
sources/
  <bank_name>/
    fetcher.py      # address lookup + valuation HTTP requests
    parser.py       # valuation response → BaseProperty
    pipeline.py     # request-driven valuation orchestration
models/
  <bank_name>.py    # address tree / floor / flat / valuation models
```

For bank valuation APIs:
- Keep address lookup helpers in the fetcher, for example area/district/estate/block, floor, and flat methods.
- Keep valuation fetching explicit: accept concrete address code combinations rather than crawling every unit by default.
- Treat HTTP `429` as a hard signal to slow down or stop.
- Preserve the original valuation payload in `BaseProperty.raw`.
- Map sale valuation price to `BaseProperty.price`, area fields to `gross_area_ft` / `net_area_ft`, and compute price-per-foot fields when possible.
- Document endpoint paths, important query/body parameters, and source page in the bank fetcher module docstring.

Current Hang Seng usage:

```bash
uv run python -m hk_house.cli hangseng --area 1 --district 5 --estate 646 --block 5711 --floor 10 --flat A1
```

Hang Seng source page:

```text
https://www.hangseng.com/zh-hk/e-valuation/address-search/
```

Hang Seng API endpoints used:

```text
GET  /area2blockfulllist?timestamp={unix_ms}
GET  /floor?blockcode={blockCode}&timestamp={unix_ms}
GET  /flat?blockcode={blockCode}&floorcode={floorCode}&timestamp={unix_ms}
POST /valuation
```

### API Integration

APIs are provided by the user from browser inspection. When adding a new source:
- Inspect request headers, cookies, pagination params from browser
- Model the request exactly (user-agent, headers, query params)
- Handle pagination to get full dataset
- Document the API endpoint and key params in the source's module docstring
