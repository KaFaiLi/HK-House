"""Hang Seng e-Valuation API fetcher.

Source page:
    https://www.hangseng.com/zh-hk/e-valuation/address-search/

Endpoints used by the page:
    GET  /area2blockfulllist?timestamp={unix_ms}
    GET  /floor?blockcode={blockCode}&timestamp={unix_ms}
    GET  /flat?blockcode={blockCode}&floorcode={floorCode}&timestamp={unix_ms}
    POST /valuation

This is a public web endpoint used by Hang Seng's page, not a published
developer API. Treat 429 as a clear throttle signal and use small, explicit
fetches unless you have permission to crawl broadly.
"""

from __future__ import annotations

import time
from typing import Any, Iterator

from ...http_client import HttpClient
from ...models.hangseng import (
    HangSengAddressTree,
    HangSengFlat,
    HangSengFloor,
    HangSengValuation,
    HangSengValuationRequest,
)

BASE_URL = (
    "https://rbwm-api.hsbc.com.hk/"
    "pws-hk-hase-mortgage-eapi-prod-proxy/v1/property"
)
REFERER = "https://www.hangseng.com/zh-hk/e-valuation/address-search/"


def unix_ms() -> int:
    return int(time.time() * 1000)


class HangSengAPIError(RuntimeError):
    """Raised when Hang Seng returns an API-level error payload."""


class HangSengFetcher:
    def __init__(self, client: HttpClient | None = None) -> None:
        self._own_client = client is None
        self.client = client or HttpClient(
            base_headers={
                "Origin": "https://www.hangseng.com",
                "Referer": REFERER,
            }
        )

    def close(self) -> None:
        if self._own_client:
            self.client.close()

    def __enter__(self) -> "HangSengFetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def fetch_address_tree(self) -> HangSengAddressTree:
        data = self._get_json("area2blockfulllist")
        return HangSengAddressTree.model_validate(data)

    def fetch_floors(self, block_code: str) -> list[HangSengFloor]:
        data = self._get_json("floor", params={"blockcode": block_code})
        return [HangSengFloor.model_validate(item) for item in data]

    def fetch_flats(self, block_code: str, floor_code: str) -> list[HangSengFlat]:
        data = self._get_json(
            "flat",
            params={"blockcode": block_code, "floorcode": floor_code},
        )
        return [HangSengFlat.model_validate(item) for item in data]

    def fetch_valuation(
        self,
        request: HangSengValuationRequest | dict[str, Any],
    ) -> list[HangSengValuation]:
        req = (
            request
            if isinstance(request, HangSengValuationRequest)
            else HangSengValuationRequest.model_validate(request)
        )
        resp = self.client.post_json(f"{BASE_URL}/valuation", json=req.model_dump())
        data = resp.json()
        self._raise_for_api_error(data)
        return [HangSengValuation.of(item) for item in data]

    def iter_valuations(
        self,
        requests: Iterator[HangSengValuationRequest | dict[str, Any]],
    ) -> Iterator[dict[str, Any]]:
        for request in requests:
            for valuation in self.fetch_valuation(request):
                yield valuation.raw

    def _get_json(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        query = {"timestamp": unix_ms()}
        if params:
            query.update(params)
        resp = self.client.get(f"{BASE_URL}/{endpoint}", params=query)
        data = resp.json()
        self._raise_for_api_error(data)
        return data

    @staticmethod
    def _raise_for_api_error(data: Any) -> None:
        if isinstance(data, dict) and data.get("errMsgKey"):
            raise HangSengAPIError(str(data["errMsgKey"]))
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict) and first.get("errorMsg"):
                field = first.get("fieldName") or "Unknown"
                raise HangSengAPIError(f"{field}: {first['errorMsg']}")
