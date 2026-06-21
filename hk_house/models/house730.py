"""House730 source-specific intermediate model (from Property/GetProperty)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class House730Property(BaseModel):
    model_config = ConfigDict(extra="allow")

    propertyID: int
    rentalType: int | None = None            # 1 = sale, 2 = rent (observed)
    propertyCategory: int | None = None      # 1 = residential
    propertyCategoryWithCulture: str | None = None

    estateName: str | None = None
    estateAddressWithCulture: str | None = None
    buildingAge: int | None = None

    buildingArea: float | None = None        # gross sq ft
    saleableArea: float | None = None        # net sq ft
    salePrice: float | None = None
    rentPrice: float | None = None
    buildingAvgPrice: float | None = None     # gross $/ft
    saleableAvgPrice: float | None = None     # net $/ft

    unitFloorWithCulture: str | None = None   # 低層 / 中層 / 高層
    propertyNo: str | None = None
    roomNumber: int | None = None
    toiletNumber: int | None = None

    regionName: str | None = None
    zoneName: str | None = None               # district
