"""Midland fetcher.

API (observed from browser inspection):

    GET https://data.midland.com.hk/search/v2/properties
        ?tx_type=S&page=<n>&limit=<n>&lang=zh-hk&unit=feet&currency=HKD
    header: Authorization: Bearer <JWT>

Auth: the JWT is NOT a login token -- it is a build-time token (``BUILD_TOKEN``)
embedded in the homepage HTML at https://www.midland.com.hk/. We scrape it
automatically (and cache it), so no manual capture is needed. If Midland rotates
the token you may override it via the MIDLAND_TOKEN env var.

Pagination: ``page`` (1-based) + ``limit``. ``limit`` accepts large values
(>=500 observed). Response: {"count": <total>, "result": [ ...properties ]}.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Iterator

from ...config import DATA_DIR, SECRETS
from ...http_client import BlockedError, HttpClient

log = logging.getLogger("hkhouse.midland")

SEARCH_URL = "https://data.midland.com.hk/search/v2/properties"
HOMEPAGE = "https://www.midland.com.hk/"
PAGE_LIMIT = 500
_TOKEN_RE = re.compile(r'"BUILD_TOKEN":"([^"]+)"')

# BUILD_TOKEN is a long-lived per-deploy token, so cache it and reuse for a while
# instead of re-scraping the (Cloudflare-protected) homepage every run.
_TOKEN_CACHE = DATA_DIR / ".cache" / "midland_token.txt"
_TOKEN_TTL = 12 * 3600  # seconds

BASE_HEADERS = {
    "Origin": "https://www.midland.com.hk",
    "Referer": "https://www.midland.com.hk/",
}


def _read_cache() -> str | None:
    if _TOKEN_CACHE.exists() and (time.time() - _TOKEN_CACHE.stat().st_mtime) < _TOKEN_TTL:
        tok = _TOKEN_CACHE.read_text().strip()
        if tok:
            return tok
    return None


def _write_cache(token: str) -> None:
    _TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_CACHE.write_text(token)


def _scrape_httpx() -> str | None:
    try:
        with HttpClient(base_headers={"Referer": HOMEPAGE}) as client:
            html = client.get(HOMEPAGE).text
    except BlockedError:
        log.warning("midland: homepage blocked via httpx; trying browser")
        return None
    m = _TOKEN_RE.search(html)
    return m.group(1) if m else None


def _scrape_playwright() -> str | None:
    """Fallback: a real browser usually gets past Cloudflare on the homepage."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(locale="zh-HK").new_page()
            page.goto(HOMEPAGE, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1500)
            html = page.content()
            browser.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("midland: playwright token scrape failed: %s", exc)
        return None
    m = _TOKEN_RE.search(html)
    return m.group(1) if m else None


def get_build_token(force: bool = False) -> str:
    """Resolve the BUILD_TOKEN: env override -> cache -> httpx -> Playwright."""
    if SECRETS.midland_token:
        return SECRETS.midland_token
    if not force:
        cached = _read_cache()
        if cached:
            return cached
    token = _scrape_httpx() or _scrape_playwright()
    if not token:
        raise RuntimeError(
            "Could not obtain Midland BUILD_TOKEN (homepage blocked and no cache). "
            "Set MIDLAND_TOKEN env var from your browser as a fallback."
        )
    _write_cache(token)
    return token


class MidlandFetcher:
    def __init__(
        self,
        tx_type: str = "S",
        limit: int = PAGE_LIMIT,
        token: str | None = None,
        extra_params: dict[str, Any] | None = None,
    ) -> None:
        self.tx_type = tx_type
        self.limit = limit
        self.extra_params = extra_params or {}
        # priority: explicit arg -> env override -> cache -> scrape (httpx/browser)
        self._token = token or get_build_token()

    def iter_properties(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        headers = {**BASE_HEADERS, "Authorization": f"Bearer {self._token}"}
        with HttpClient(base_headers=headers) as client:
            page = 1
            total: int | None = None
            yielded = 0
            while True:
                params = {
                    "tx_type": self.tx_type,
                    "page": page,
                    "limit": self.limit,
                    "lang": "zh-hk",
                    "unit": "feet",
                    "currency": "HKD",
                    **self.extra_params,
                }
                resp = client.get(SEARCH_URL, params=params)
                payload = resp.json()

                if total is None:
                    total = int(payload.get("count", 0))
                    log.info("midland: %d total listings", total)

                rows = payload.get("result") or []
                if not rows:
                    break

                for row in rows:
                    yield row
                    yielded += 1
                    if max_records and yielded >= max_records:
                        return

                if yielded >= (total or 0) or len(rows) < self.limit:
                    break
                page += 1
