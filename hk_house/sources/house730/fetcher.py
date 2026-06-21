"""House730 fetcher.

Detail API (open, no Cloudflare):

    GET https://api.house730.com/Property/GetProperty
        ?propertyId=<id>&language=zh-hk&platform=pc&cityen=hk
        &appkey=730responsive&appsignature=<SIG>

  * ``appsignature`` is a STATIC app signature (not per-property) -- the same
    value works for every propertyId, so detail fetching needs no per-call auth.
    Override via HOUSE730_APPSIGNATURE if it ever rotates.
  * Response: {"code": 0, "result": { ...property }}.

ID discovery: the listing/search site (www.house730.com) sits behind Cloudflare,
so its list endpoint cannot be hit anonymously. Supply IDs one of two ways:
  1. pass an explicit ``property_ids`` list to the pipeline, or
  2. set HOUSE730_LIST_API to a browser-captured list endpoint that returns
     JSON containing property ids -- ``iter_ids_from_list_api`` paginates it.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Iterable, Iterator

from ...config import SECRETS
from ...http_client import HttpClient

log = logging.getLogger("hkhouse.house730")

DETAIL_URL = "https://api.house730.com/Property/GetProperty"
DEFAULT_SIG = (
    "ztH7d7Zk4YAe8GGmlVeNjx/4kxcbHmOSUGqIhiGP5Zv262jrDOosugEqJmbqjFndn2s"
    "+IpxRP2ROhz6OBlhvqw=="
)
APPSIG = os.getenv("HOUSE730_APPSIGNATURE", DEFAULT_SIG)
APPKEY = os.getenv("HOUSE730_APPKEY", "730responsive")

BASE_HEADERS = {"Referer": "https://www.house730.com/"}


class House730Fetcher:
    def __init__(self) -> None:
        self._client = HttpClient(base_headers=BASE_HEADERS)

    def close(self) -> None:
        self._client.close()

    def fetch_detail(self, property_id: int | str) -> dict[str, Any] | None:
        params = {
            "propertyId": property_id,
            "language": "zh-hk",
            "platform": "pc",
            "cityen": "hk",
            "appkey": APPKEY,
            "appsignature": APPSIG,
        }
        payload = self._client.get(DETAIL_URL, params=params).json()
        if payload.get("code") != 0:
            log.warning("house730: id=%s returned code=%s", property_id, payload.get("code"))
            return None
        return payload.get("result")

    def iter_details(self, property_ids: Iterable[int | str]) -> Iterator[dict[str, Any]]:
        for pid in property_ids:
            result = self.fetch_detail(pid)
            if result:
                yield result

    def iter_ids_from_list_api(self, max_pages: int = 1000) -> Iterator[int]:
        """Paginate a browser-captured list endpoint (HOUSE730_LIST_API).

        The endpoint URL may contain a ``{page}`` placeholder. We pull any
        ``propertyID`` values out of the JSON, whatever the nesting.
        """
        tmpl = SECRETS.house730_list_api
        if not tmpl:
            raise RuntimeError(
                "House730 ID discovery needs a list endpoint. Either pass "
                "property_ids to the pipeline, or set HOUSE730_LIST_API to a "
                "browser-captured URL (optionally with a {page} placeholder)."
            )
        for page in range(1, max_pages + 1):
            url = tmpl.format(page=page) if "{page}" in tmpl else tmpl
            payload = self._client.get(url).json()
            ids = list(_dig_ids(payload))
            if not ids:
                break
            yield from ids
            if "{page}" not in tmpl:
                break  # not paginated


def _dig_ids(obj: Any) -> Iterator[int]:
    """Recursively yield any propertyID/propertyId values found in a structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == "propertyid" and isinstance(v, (int, str)) and str(v).isdigit():
                yield int(v)
            else:
                yield from _dig_ids(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _dig_ids(item)
