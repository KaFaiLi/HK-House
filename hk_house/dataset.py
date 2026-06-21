"""Build one cleaned, typed Parquet dataset from all per-source processed JSONL.

Reads ``data/processed/<source>.jsonl`` for every source, concatenates them on
the shared base schema, cleans/coerces types, dedups by ``key`` and writes
``data/processed/properties.parquet``.

    uv run python -m hk_house.cli export
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR
from .models.base import BaseProperty

log = logging.getLogger("hkhouse.dataset")

OUTPUT = PROCESSED_DIR / "properties.parquet"

# Typed base columns (raw is dropped from the cleaned dataset).
NUMERIC = [
    "price", "price_per_gross_ft", "price_per_net_ft",
    "gross_area_ft", "net_area_ft", "building_age",
    "bedrooms", "bathrooms",
]
STRING = [
    "source", "source_id", "key", "url", "tx_type", "kind",
    "estate", "building", "address", "district", "region",
    "floor", "flat", "direction",
]
COLUMNS = STRING + NUMERIC + ["fetched_at"]


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                obj = json.loads(line)
                obj.pop("raw", None)  # exclude bulky source payload
                rows.append(obj)
    return rows


def build_dataset(output: Path = OUTPUT) -> pd.DataFrame:
    sources = sorted(PROCESSED_DIR.glob("*.jsonl"))
    frames = []
    for path in sources:
        rows = _load_jsonl(path)
        if rows:
            frames.append(pd.DataFrame(rows))
            log.info("loaded %d rows from %s", len(rows), path.name)
    if not frames:
        raise RuntimeError(f"No processed JSONL found in {PROCESSED_DIR}. Run a fetch first.")

    df = pd.concat(frames, ignore_index=True)

    # Ensure all expected columns exist.
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # Type coercion.
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("bedrooms", "bathrooms", "building_age"):
        df[col] = df[col].astype("Int64")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce", utc=True)
    for col in STRING:
        df[col] = df[col].astype("string")

    # Clean: dedup by key (keep latest fetch), drop rows with neither price nor area.
    df = df.sort_values("fetched_at").drop_duplicates("key", keep="last")
    df = df.dropna(subset=["price", "net_area_ft", "gross_area_ft"], how="all")

    df = df[COLUMNS].reset_index(drop=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, engine="pyarrow", compression="snappy", index=False)
    log.info("wrote %d rows -> %s", len(df), output)
    return df


def summary(df: pd.DataFrame) -> str:
    by_src = df.groupby("source", observed=True).size().to_dict()
    return (
        f"rows={len(df)} sources={by_src} "
        f"price[min/median/max]="
        f"{df.price.min():.0f}/{df.price.median():.0f}/{df.price.max():.0f}"
    )


# Re-export so static checks know the base schema is the contract.
__all__ = ["build_dataset", "summary", "BaseProperty", "OUTPUT"]
