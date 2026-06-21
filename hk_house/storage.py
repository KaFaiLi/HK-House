"""Persistence for raw responses and processed base records.

Layout:
    data/raw/<source>/<source>_<timestamp>.jsonl     # one raw record per line
    data/processed/<source>.jsonl                     # base records, upserted by key

Raw is append-only (audit trail / reprocessing). Processed is keyed so re-runs
update existing listings instead of duplicating them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import PROCESSED_DIR, RAW_DIR, ensure_dirs
from .models.base import BaseProperty


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class StreamWriter:
    """Incremental writer: persists each record to disk as it arrives.

    Used by long crawls so a mid-run failure keeps everything fetched so far.
    Raw goes to a timestamped file; processed is appended (dedup is deferred to
    the Parquet export, which keeps the latest per key).
    """

    def __init__(self, source: str) -> None:
        ensure_dirs()
        raw_dir = RAW_DIR / source
        raw_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = raw_dir / f"{source}_{_ts()}.jsonl"
        self.processed_path = PROCESSED_DIR / f"{source}.jsonl"
        self._raw_fh = self.raw_path.open("w", encoding="utf-8")
        self._proc_fh = self.processed_path.open("a", encoding="utf-8")
        self.raw_count = 0
        self.processed_count = 0

    def write_raw(self, rec: dict[str, Any]) -> None:
        self._raw_fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        self.raw_count += 1

    def write_processed(self, rec: BaseProperty) -> None:
        obj = rec.model_dump(mode="json")
        obj["key"] = rec.key
        self._proc_fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.processed_count += 1

    def flush(self) -> None:
        self._raw_fh.flush()
        self._proc_fh.flush()

    def close(self) -> None:
        self._raw_fh.close()
        self._proc_fh.close()

    def __enter__(self) -> "StreamWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def save_raw(source: str, records: Iterable[dict[str, Any]]) -> Path:
    """Append raw source records to a timestamped JSONL file."""
    ensure_dirs()
    out_dir = RAW_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{source}_{_ts()}.jsonl"
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str))
            fh.write("\n")
            n += 1
    return path


def save_processed(source: str, records: Iterable[BaseProperty]) -> Path:
    """Upsert base records into the per-source processed JSONL (keyed by .key)."""
    ensure_dirs()
    path = PROCESSED_DIR / f"{source}.jsonl"

    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                existing[obj["key"]] = obj

    for rec in records:
        obj = rec.model_dump(mode="json")
        obj["key"] = rec.key
        existing[rec.key] = obj

    with path.open("w", encoding="utf-8") as fh:
        for obj in existing.values():
            fh.write(json.dumps(obj, ensure_ascii=False))
            fh.write("\n")
    return path
