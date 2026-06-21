"""The unified base schema -- the contract every pipeline transforms into.

Keep this source-agnostic. Each source maps its raw fields onto these. Prices
are in HKD; areas in square feet (the HK convention). ``raw`` keeps the full
original record so nothing is lost in transformation.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class TxType(str, enum.Enum):
    SALE = "sale"
    RENT = "rent"


class PropertyKind(str, enum.Enum):
    RESIDENTIAL = "residential"
    VILLAGE_HOUSE = "village_house"
    CARPARK = "carpark"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    SHOP = "shop"
    LAND = "land"
    OTHER = "other"


class BaseProperty(BaseModel):
    """One property listing in the standardised format."""

    # Identity ----------------------------------------------------------------
    source: str = Field(..., description="Source name, e.g. 'centanet'")
    source_id: str = Field(..., description="Stable id within the source")
    url: str | None = None

    # Transaction ------------------------------------------------------------
    tx_type: TxType = TxType.SALE
    kind: PropertyKind = PropertyKind.RESIDENTIAL

    # Price (HKD) ------------------------------------------------------------
    price: float | None = Field(None, description="Total price (sale) or monthly rent")
    price_per_gross_ft: float | None = None
    price_per_net_ft: float | None = None

    # Area (sq ft) -----------------------------------------------------------
    gross_area_ft: float | None = None
    net_area_ft: float | None = None

    # Location ---------------------------------------------------------------
    estate: str | None = None
    building: str | None = None
    address: str | None = None
    district: str | None = None
    region: str | None = None

    # Unit attributes --------------------------------------------------------
    floor: str | None = None
    flat: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    building_age: int | None = None
    direction: str | None = None

    # Provenance -------------------------------------------------------------
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def key(self) -> str:
        """Globally unique key across sources, for dedup / upsert."""
        return f"{self.source}:{self.source_id}"
