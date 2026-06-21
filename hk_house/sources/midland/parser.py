"""Midland parser: raw property dict -> MidlandProperty -> BaseProperty."""

from __future__ import annotations

from typing import Any

from ...models.base import BaseProperty, PropertyKind, TxType
from ...models.midland import MidlandProperty


def _name(v: Any) -> str | None:
    """Midland location fields are {'id':..., 'name':...}; pull the name."""
    if isinstance(v, dict):
        return v.get("name")
    return v or None


def to_base(raw: dict[str, Any]) -> BaseProperty:
    p = MidlandProperty.model_validate(raw)
    is_rent = "R" in (p.tx_type or [])

    url = None
    if p.url_desc:
        url = p.url_desc if p.url_desc.startswith("http") else (
            f"https://www.midland.com.hk/zh-hk/list/buy/{p.url_desc}"
        )

    return BaseProperty(
        source="midland",
        source_id=p.serial_no,
        url=url,
        tx_type=TxType.RENT if is_rent else TxType.SALE,
        kind=PropertyKind.RESIDENTIAL,
        price=(p.rent_hkd if is_rent else p.price_hkd) or None,
        price_per_gross_ft=p.price_over_area or None,
        price_per_net_ft=p.price_over_net_area or None,
        gross_area_ft=p.area or None,
        net_area_ft=p.net_area or None,
        estate=_name(p.estate),
        building=_name(p.phase),
        district=_name(p.district) or _name(p.sm_district),
        region=_name(p.region),
        flat=p.flat or None,
        bedrooms=p.bedroom,
        raw=raw,
    )
