"""Midland pipeline: fetch -> parse -> base."""

from __future__ import annotations

from typing import Any, Iterator

from ...models.base import BaseProperty
from ..base_pipeline import Pipeline
from .fetcher import MidlandFetcher
from .parser import to_base


class MidlandPipeline(Pipeline):
    source = "midland"

    def __init__(self, tx_type: str = "S", limit: int = 500, token: str | None = None) -> None:
        self.fetcher = MidlandFetcher(tx_type=tx_type, limit=limit, token=token)

    def iter_raw(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        yield from self.fetcher.iter_properties(max_records=max_records)

    def parse(self, raw: dict[str, Any]) -> BaseProperty:
        return to_base(raw)
