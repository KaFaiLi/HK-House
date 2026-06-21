"""Hang Seng valuation parser: API valuation payload -> BaseProperty."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...models.base import BaseProperty, PropertyKind, TxType


def _f(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _year_month(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%m/%Y")
    except ValueError:
        return None


def _building_age(completion_date: str | None) -> int | None:
    completed = _year_month(completion_date)
    if not completed:
        return None
    now = datetime.now()
    return max(0, now.year - completed.year - ((now.month, now.day) < (completed.month, 1)))


def _source_id(raw: dict[str, Any]) -> str:
    parts = [
        raw.get("CWReference"),
        raw.get("blockCode"),
        raw.get("floorCode"),
        raw.get("flatCode"),
    ]
    return ":".join(str(p) for p in parts if p not in (None, "")) or str(hash(str(raw)))


def to_base(raw: dict[str, Any]) -> BaseProperty:
    gross_area = _f(raw.get("grossArea"))
    net_area = _f(raw.get("saleableArea"))
    price = _f(raw.get("price"))

    return BaseProperty(
        source="hangseng",
        source_id=_source_id(raw),
        tx_type=TxType.SALE,
        kind=PropertyKind.RESIDENTIAL,
        price=price,
        price_per_gross_ft=price / gross_area if price and gross_area else None,
        price_per_net_ft=price / net_area if price and net_area else None,
        gross_area_ft=gross_area,
        net_area_ft=net_area,
        address=raw.get("addressZhDisp") or raw.get("addressDisp"),
        building=raw.get("blockCode"),
        floor=raw.get("floorCode"),
        flat=raw.get("flatCode"),
        building_age=_building_age(raw.get("completionDate")),
        raw=raw,
    )
