"""Hang Seng valuation pipeline.

This pipeline is intentionally request-driven: pass one or more concrete
address-code combinations and it fetches their valuations. The address tree,
floor, and flat helper methods live on ``HangSengFetcher`` so callers can build
those requests explicitly and checkpoint broad crawls themselves.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator

from ...models.base import BaseProperty
from ...models.hangseng import HangSengValuationRequest
from ..base_pipeline import Pipeline
from .fetcher import HangSengFetcher
from .parser import to_base


class HangSengPipeline(Pipeline):
    source = "hangseng"

    def __init__(
        self,
        valuation_requests: Iterable[HangSengValuationRequest | dict[str, Any]] | None = None,
    ) -> None:
        self.valuation_requests = list(valuation_requests or [])
        self.fetcher = HangSengFetcher()

    def iter_raw(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        yielded = 0
        try:
            for raw in self.fetcher.iter_valuations(iter(self.valuation_requests)):
                yield raw
                yielded += 1
                if max_records and yielded >= max_records:
                    return
        finally:
            self.fetcher.close()

    def parse(self, raw: dict[str, Any]) -> BaseProperty:
        return to_base(raw)
