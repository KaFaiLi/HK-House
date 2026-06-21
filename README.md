# HK-House

Hong Kong property listing pipelines. Each source fetches → parses → transforms
into one **unified base schema** (`hk_house/models/base.py`), stored as JSONL.

## Quick start

```bash
uv sync
uv run python -m hk_house.cli centanet --max 200    # quick sample
uv run python -m hk_house.cli centanet              # full crawl (~40k)
uv run python -m hk_house.cli all --max 100         # every source
```

Output:
- `data/raw/<source>/<source>_<ts>.jsonl` — raw responses (append-only audit trail)
- `data/processed/<source>.jsonl` — base records (streamed to disk during the crawl)

### Cleaned dataset (Parquet)

```bash
uv run python -m hk_house.cli export
```

Merges every source's processed JSONL into one typed, deduped (by `source:id`)
table → `data/processed/properties.parquet`. Numeric coercion, drops the bulky
`raw` payload and rows with neither price nor area. Load with
`pd.read_parquet("data/processed/properties.parquet")`.

Crawls **stream to disk** and flush every 200 records, so a mid-crawl failure
(deep-page cap, throttling) keeps everything fetched so far; `export` dedups.

Coverage caps: centanet stops at ~10k (server caps `offset` ≥ 10000); 28hse at
~15k (site page limit). Full centanet needs filter partitioning.

### District price map

```bash
uv run python -m hk_house.cli map
```

Normalises every listing to one of HK's 18 administrative districts
(`analysis.normalize_district`: handles `荃灣區`, `將軍澳 (西貢區)`,
`屯門(青山公路)`, hse28 neighbourhoods like `荔枝角`→`深水埗區`; mainland values
excluded), aggregates **avg / median / min / max** of total price and price per
net sq ft, and writes:
- `data/processed/district_stats.csv` — the table
- `data/processed/hk_price_map.html` — interactive Folium choropleth (toggle
  $/ft vs total price; hover for all stats). Boundaries: official
  `had.gov.hk` 18-district GeoJSON in `data/geo/`.

## Sources

| Source | Endpoint | Pagination | Auth | Status |
|--------|----------|-----------|------|--------|
| **centanet** | `POST hk.centanet.com/findproperty/api/Post/Search` | body `offset` (record offset) + `size` (**max 100**); total in `count` | none | ✅ works |
| **midland** | `GET data.midland.com.hk/search/v2/properties` | `page` + `limit` (≥500 ok); total in `count` | `Authorization: Bearer <BUILD_TOKEN>` — **scraped automatically** from the homepage | ✅ works |
| **house730** | `GET api.house730.com/Property/GetProperty?propertyId=…` | detail-by-ID; static `appsignature` reused for all IDs | none | ✅ detail works; needs IDs (see below) |
| **hse28** | `www.28hse.com/buy?page=N` (SSR HTML, Cloudflare) | `?page=N` | none — **Playwright real browser** passes Cloudflare | ✅ works |

### house730 — supplying IDs

`api.house730.com` (detail) is open, but the listing site is behind Cloudflare,
so IDs must be supplied:

```bash
uv run python -m hk_house.cli house730 --ids 9089382,9089383
```

Or set a browser-captured list endpoint (paginated via `{page}`); ids are dug out
of the JSON automatically:

```bash
export HOUSE730_LIST_API='https://<captured-list-endpoint>?page={page}'
uv run python -m hk_house.cli house730
```

### hse28 — Playwright

28Hse has no anonymous JSON API and is server-rendered behind Cloudflare, so it's
scraped with a real Chromium via Playwright (a real browser passes Cloudflare
with no challenge, even headless — no cookies needed). One-time browser install:

```bash
uv run playwright install chromium
uv run python -m hk_house.cli hse28 --max 100
```

Listing fields are parsed from each card's text blob by regex in
`sources/hse28/parser.py`. Env: `HSE28_HEADLESS=0` to run headed (debugging),
`HKHOUSE_UA` to pin the browser User-Agent.

## Anti-blocking

All fetchers share `hk_house/http_client.py`:
- rotating realistic browser User-Agents + HTTP/2 + cookie jar
- polite randomised delay between requests (jittered)
- exponential backoff w/ jitter on 429/5xx/network errors, honours `Retry-After`
- optional proxy rotation (`HKHOUSE_PROXIES="http://h1,http://h2"`)
- 403 raises `BlockedError` (WAF/Cloudflare → refresh cookies)

Tunable via env (see `hk_house/config.py`): `HKHOUSE_MIN_DELAY`,
`HKHOUSE_MAX_JITTER`, `HKHOUSE_MAX_RETRIES`, `HKHOUSE_BACKOFF_BASE`,
`HKHOUSE_BACKOFF_MAX`, `HKHOUSE_TIMEOUT`, `HKHOUSE_DATA_DIR`.

## Layout

```
hk_house/
  config.py          # paths, network tuning, secrets (env)
  http_client.py     # shared anti-blocking client
  storage.py         # raw + processed JSONL
  models/            # base.py (contract) + per-source intermediate models
  sources/<name>/    # fetcher.py, parser.py, pipeline.py
  cli.py
```

## Tests

```bash
uv run pytest
```
