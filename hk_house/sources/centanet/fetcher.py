"""Centanet fetcher.

API (no auth required), observed from browser inspection:

    POST https://hk.centanet.com/findproperty/api/Post/Search
    Content-Type: application/json
    body: {"offset": <record offset>, "size": <page size>, ...filters}

  * ``offset`` is a RECORD offset (offset=1 skips the first record), not a page
    index. Paginate by stepping offset += size.
  * ``size`` max is 100 (200 returns an empty list).
  * Response: {"count": <total>, "data": [ ...posts ]}.

``count`` (~40k) is the total matching the filter, used to know when to stop.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

from ...http_client import HttpClient

log = logging.getLogger("hkhouse.centanet")

SEARCH_URL = "https://hk.centanet.com/findproperty/api/Post/Search"
MAX_SIZE = 100
# Server caps deep pagination (Elasticsearch max_result_window): offset >= 10000
# returns HTTP 500. So plain offset paging reaches the first ~10k listings only.
# Full coverage needs partitioning the search by a filter (browser-captured
# schema); not available, so we stop cleanly at the cap.
MAX_OFFSET = 10000
BASE_HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://hk.centanet.com",
    "Referer": "https://hk.centanet.com/findproperty/list/buy",
}


class CentanetFetcher:
    def __init__(self, page_size: int = MAX_SIZE, filters: dict[str, Any] | None = None) -> None:
        self.page_size = min(page_size, MAX_SIZE)
        self.filters = filters or {}

    def iter_posts(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        """Yield raw post dicts, paginating until exhausted or max_records hit."""
        with HttpClient(base_headers=BASE_HEADERS) as client:
            offset = 0
            total: int | None = None
            yielded = 0
            while True:
                body = {**self.filters, "offset": offset, "size": self.page_size}
                resp = client.post_json(SEARCH_URL, json=body)
                payload = resp.json()

                if total is None:
                    total = int(payload.get("count", 0))
                    log.info("centanet: %d total listings", total)

                data = payload.get("data") or []
                if not data:
                    break

                for post in data:
                    yield post
                    yielded += 1
                    if max_records and yielded >= max_records:
                        return

                offset += len(data)
                if offset >= total:
                    break
                if offset >= MAX_OFFSET:
                    log.warning(
                        "centanet: reached deep-pagination cap (offset=%d of %d); "
                        "remaining listings need filter partitioning",
                        offset, total,
                    )
                    break
