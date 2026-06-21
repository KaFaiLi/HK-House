"""House730 pipeline: fetch detail by id -> parse -> base.

IDs come from (in priority order): explicit ``property_ids``, else the
browser-captured HOUSE730_LIST_API discovery endpoint.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator

from ...models.base import BaseProperty
from ..base_pipeline import Pipeline
from .fetcher import House730Fetcher
from .parser import to_base


class House730Pipeline(Pipeline):
    source = "house730"

    def __init__(self, property_ids: Iterable[int | str] | None = None) -> None:
        self.property_ids = list(property_ids) if property_ids is not None else None
        self.fetcher = House730Fetcher()

    def _ids(self, max_records: int | None) -> Iterator[int | str]:
        if self.property_ids is not None:
            ids: Iterable[int | str] = self.property_ids
        else:
            ids = self.fetcher.iter_ids_from_list_api()
        for i, pid in enumerate(ids):
            if max_records and i >= max_records:
                return
            yield pid

    def iter_raw(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        try:
            yield from self.fetcher.iter_details(self._ids(max_records))
        finally:
            self.fetcher.close()

    def parse(self, raw: dict[str, Any]) -> BaseProperty:
        return to_base(raw)
