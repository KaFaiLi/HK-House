"""28Hse pipeline: scrape (Playwright) -> parse -> base."""

from __future__ import annotations

from typing import Any, Iterator

from ...models.base import BaseProperty
from ..base_pipeline import Pipeline
from .fetcher import Hse28Fetcher
from .parser import to_base


class Hse28Pipeline(Pipeline):
    source = "hse28"

    def __init__(self, headless: bool | None = None) -> None:
        self.fetcher = Hse28Fetcher(headless=headless)

    def iter_raw(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        yield from self.fetcher.iter_listings(max_records=max_records)

    def parse(self, raw: dict[str, Any]) -> BaseProperty:
        return to_base(raw)
