"""Shared pipeline scaffolding.

A pipeline orchestrates: fetch raw -> parse to base -> persist. Subclasses only
implement ``iter_raw`` (yield raw dicts) and ``parse`` (raw dict -> BaseProperty).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator

from .. import storage
from ..models.base import BaseProperty

log = logging.getLogger("hkhouse.pipeline")


@dataclass
class RunResult:
    source: str
    fetched: int
    parsed: int
    errors: int
    raw_path: str | None = None
    processed_path: str | None = None


class Pipeline(ABC):
    source: str

    @abstractmethod
    def iter_raw(self, max_records: int | None = None) -> Iterator[dict[str, Any]]:
        ...

    @abstractmethod
    def parse(self, raw: dict[str, Any]) -> BaseProperty:
        ...

    def run(self, max_records: int | None = None, save: bool = True) -> RunResult:
        """Stream records to disk as they arrive so a mid-crawl failure (deep-page
        cap, throttling, network) keeps everything fetched so far."""
        fetched = parsed = errors = 0
        writer = storage.StreamWriter(self.source) if save else None
        fetch_error: Exception | None = None

        try:
            for raw in self.iter_raw(max_records=max_records):
                fetched += 1
                if writer:
                    writer.write_raw(raw)
                try:
                    base = self.parse(raw)
                    parsed += 1
                    if writer:
                        writer.write_processed(base)
                except Exception as exc:  # noqa: BLE001 -- isolate bad records
                    errors += 1
                    log.warning("%s: parse error: %s", self.source, exc)
                if writer and fetched % 200 == 0:
                    writer.flush()
        except Exception as exc:  # noqa: BLE001 -- persist partial, then report
            fetch_error = exc
            log.warning("%s: fetch stopped early: %s", self.source, exc)
        finally:
            if writer:
                writer.close()

        result = RunResult(
            source=self.source,
            fetched=fetched,
            parsed=parsed,
            errors=errors,
            raw_path=str(writer.raw_path) if writer else None,
            processed_path=str(writer.processed_path) if writer and parsed else None,
        )
        log.info(
            "%s: fetched=%d parsed=%d errors=%d%s",
            self.source, fetched, parsed, errors,
            f" (stopped early: {fetch_error})" if fetch_error else "",
        )
        return result
