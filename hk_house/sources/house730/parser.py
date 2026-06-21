"""House730 parser: raw result dict -> House730Property -> BaseProperty."""

from __future__ import annotations

from typing import Any

from ...models.base import BaseProperty, PropertyKind, TxType
from ...models.house730 import House730Property

_KIND = {
    "住宅": PropertyKind.RESIDENTIAL,
    "村屋": PropertyKind.VILLAGE_HOUSE,
    "車位": PropertyKind.CARPARK,
    "商舖": PropertyKind.SHOP,
    "寫字樓": PropertyKind.COMMERCIAL,
    "工商": PropertyKind.INDUSTRIAL,
}


def to_base(raw: dict[str, Any]) -> BaseProperty:
    p = House730Property.model_validate(raw)
    is_rent = p.rentalType == 2

    return BaseProperty(
        source="house730",
        source_id=str(p.propertyID),
        url=f"https://www.house730.com/en/property-{p.propertyID}/",
        tx_type=TxType.RENT if is_rent else TxType.SALE,
        kind=_KIND.get(p.propertyCategoryWithCulture or "", PropertyKind.RESIDENTIAL),
        price=(p.rentPrice if is_rent else p.salePrice) or None,
        price_per_gross_ft=p.buildingAvgPrice or None,
        price_per_net_ft=p.saleableAvgPrice or None,
        gross_area_ft=p.buildingArea or None,
        net_area_ft=p.saleableArea or None,
        estate=p.estateName or None,
        address=p.estateAddressWithCulture or None,
        district=p.zoneName or None,
        region=p.regionName or None,
        floor=p.unitFloorWithCulture or None,
        flat=p.propertyNo or None,
        bedrooms=p.roomNumber,
        bathrooms=p.toiletNumber,
        building_age=p.buildingAge,
        raw=raw,
    )
