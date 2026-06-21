"""Midland (美聯物業) source-specific intermediate model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class MidlandProperty(BaseModel):
    model_config = ConfigDict(extra="allow")

    serial_no: str
    tx_type: list[str] = []          # ["S"] / ["R"]
    price_hkd: float | None = None
    rent_hkd: float | None = None
    area: float | None = None        # gross sq ft
    net_area: float | None = None    # net sq ft
    price_over_area: float | None = None      # gross $/ft
    price_over_net_area: float | None = None  # net $/ft
    bedroom: int | None = None
    flat: str | None = None
    # Location fields arrive as {"id": ..., "name": ...} objects.
    estate: Any = None
    phase: Any = None
    region: Any = None
    district: Any = None
    sm_district: Any = None
    url_desc: str | None = None
