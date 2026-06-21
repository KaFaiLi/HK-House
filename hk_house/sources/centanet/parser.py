"""Centanet parser: raw post dict -> CentanetPost -> BaseProperty."""

from __future__ import annotations

from typing import Any

from ...models.base import BaseProperty, PropertyKind, TxType
from ...models.centanet import CentanetPost

# postType -> transaction
_TX = {"S": TxType.SALE, "R": TxType.RENT, "L": TxType.RENT}

# unitType (Chinese) -> kind
_KIND = {
    "分層單位": PropertyKind.RESIDENTIAL,
    "獨立屋": PropertyKind.VILLAGE_HOUSE,
    "村屋": PropertyKind.VILLAGE_HOUSE,
    "車位": PropertyKind.CARPARK,
    "商舖": PropertyKind.SHOP,
    "寫字樓": PropertyKind.COMMERCIAL,
    "工商": PropertyKind.INDUSTRIAL,
    "地皮": PropertyKind.LAND,
}


def _num(d: dict[str, Any], key: str) -> float | None:
    v = d.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _estate(post: CentanetPost) -> str | None:
    """Combine parent estate + phase, e.g. 藍天海岸 + 1期 -> '藍天海岸 1期'."""
    parts = [p.strip() for p in (post.bigEstateName, post.estateName) if p and p.strip()]
    return " ".join(parts) or None


def to_base(raw: dict[str, Any]) -> BaseProperty:
    post = CentanetPost.model_validate(raw)
    scope = post.scope or {}

    return BaseProperty(
        source="centanet",
        source_id=post.id,
        url=None,  # detail URL scheme not stable; id kept in raw
        tx_type=_TX.get((post.postType or "S").upper(), TxType.SALE),
        kind=_KIND.get(post.unitType or "", PropertyKind.OTHER),
        price=post.propertyPriceHkd or _num(post.priceInfo, "price"),
        price_per_gross_ft=_num(post.unitPriceInfo, "unitPrice"),
        price_per_net_ft=_num(post.unitPriceInfo, "nUnitPrice"),
        gross_area_ft=_num(post.areaInfo, "size"),
        net_area_ft=_num(post.areaInfo, "nSize"),
        estate=_estate(post),
        building=post.buildingName or None,
        address=post.address or None,
        district=scope.get("db"),
        region=scope.get("terr"),
        floor=post.yAxis or None,
        flat=post.xAxis or None,
        bedrooms=post.bedroomCount,
        building_age=post.buildingAge,
        direction=post.direction or None,
        raw=raw,
    )
