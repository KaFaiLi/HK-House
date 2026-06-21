"""28Hse fetcher (Playwright DOM scraper).

https://www.28hse.com/buy is server-rendered HTML behind Cloudflare. A real
browser loads it without a Turnstile challenge (even headless), so instead of
reverse-engineering a JSON API we drive Chromium and scrape the rendered listing
cards. No cookies or captured endpoints needed.

  * Pagination: ``/buy?page=N``.
  * Each card (``.item.property_item``) carries id, detail url, title and a text
    blob with price / area / rooms etc. -- parsed in ``parser.py``.

Requires the Chromium browser:  uv run playwright install chromium

Env:
  HSE28_HEADLESS=0   run headed (debug / if a challenge ever appears)
  HKHOUSE_UA         pin the browser User-Agent
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterator

log = logging.getLogger("hkhouse.hse28")

BUY_URL = "https://www.28hse.com/buy?page={page}"
CARD_SELECTOR = ".item.property_item"

# Runs in the page: returns one dict per listing card, pulling the structured
# sub-elements (district_area / areaUnitPrice / price label / tagLabels) rather
# than relying on the flattened text blob. ``text``/``html`` kept for reparsing.
_EXTRACT_JS = """
() => Array.from(document.querySelectorAll('.item.property_item')).map(it => {
  const a = it.querySelector('a.detail_page[attr1]');
  const t = s => { const e = it.querySelector(s); return e ? e.innerText.trim() : null; };
  const da = it.querySelector('.district_area');
  const daLinks = da ? Array.from(da.querySelectorAll('a')).map(x => x.innerText.trim()) : [];
  const tags = Array.from(it.querySelectorAll('.tagLabels .label')).map(x => x.innerText.trim());
  return {
    id: a ? a.getAttribute('attr1') : null,
    url: a ? a.href : null,
    title: t('.header'),
    district: daLinks.length ? daLinks[0] : null,
    estate: daLinks.length > 1 ? daLinks[daLinks.length - 1] : null,
    unit_desc: t('.district_area .unit_desc'),
    area_price: t('.areaUnitPrice'),
    price_text: t('.extra .label'),
    agent: t('.companyName'),
    tags: tags,
    text: it.innerText.replace(/\\s+/g, ' ').trim(),
    html: it.outerHTML,
  };
}).filter(o => o.id)
"""


class Hse28Fetcher:
    def __init__(self, headless: bool | None = None, max_pages: int = 1000) -> None:
        if headless is None:
            headless = os.getenv("HSE28_HEADLESS", "1") != "0"
        self.headless = headless
        self.max_pages = max_pages

    def iter_listings(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        # Imported lazily so the rest of the package works without playwright.
        from playwright.sync_api import sync_playwright

        ua = os.getenv("HKHOUSE_UA")
        yielded = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            ctx = browser.new_context(locale="zh-HK", **({"user_agent": ua} if ua else {}))
            page = ctx.new_page()
            try:
                for page_no in range(1, self.max_pages + 1):
                    page.goto(
                        BUY_URL.format(page=page_no),
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                    try:
                        page.wait_for_selector(CARD_SELECTOR, timeout=20000)
                    except Exception:
                        log.info("hse28: no cards on page %d; stopping", page_no)
                        break

                    cards = page.evaluate(_EXTRACT_JS)
                    if not cards:
                        break

                    for card in cards:
                        yield card
                        yielded += 1
                        if max_records and yielded >= max_records:
                            return
            finally:
                browser.close()
