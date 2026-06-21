"""Centanet (中原地產) source-specific intermediate model.

Only the fields we actually use are typed; the full payload is preserved in the
base record's ``raw``. Nested objects are kept as dicts and dug into in the
parser to stay resilient to schema drift.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CentanetPost(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    refNo: str | None = None
    postType: str | None = None          # "S" sale / "R" rent
    unitType: str | None = None          # 分層單位 / 村屋 / 車位 ...
    buildingType: str | None = None

    bigEstateName: str | None = None     # parent/phase-group estate, e.g. 藍天海岸
    estateName: str | None = None        # sub-estate / phase, e.g. 1期
    buildingName: str | None = None
    address: str | None = None

    yAxis: str | None = None             # floor band, e.g. 中層
    xAxis: str | None = None             # flat, e.g. 1室
    bedroomCount: int | None = None
    buildingAge: int | None = None
    direction: str | None = None
    propertyPriceHkd: float | None = None

    priceInfo: dict[str, Any] = Field(default_factory=dict)
    areaInfo: dict[str, Any] = Field(default_factory=dict)
    unitPriceInfo: dict[str, Any] = Field(default_factory=dict)
    scope: dict[str, Any] = Field(default_factory=dict)
