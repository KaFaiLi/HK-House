"""Centanet pipeline: fetch -> parse -> base."""

from __future__ import annotations

from typing import Any, Iterator

from ...models.base import BaseProperty
from ..base_pipeline import Pipeline
from .fetcher import CentanetFetcher
from .parser import to_base


class CentanetPipeline(Pipeline):
    source = "centanet"

    def __init__(self, page_size: int = 100, filters: dict[str, Any] | None = None) -> None:
        self.fetcher = CentanetFetcher(page_size=page_size, filters=filters)

    def iter_raw(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        yield from self.fetcher.iter_posts(max_records=max_records)

    def parse(self, raw: dict[str, Any]) -> BaseProperty:
        return to_base(raw)
