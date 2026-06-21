"""Hang Seng e-Valuation source models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HangSengBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    blockCode: str
    blockName: str | None = None
    blockChinesename: str | None = None
    blockChinesenameSimple: str | None = None
    coveredCarpark: str | None = None
    openCarpark: str | None = None


class HangSengEstate(BaseModel):
    model_config = ConfigDict(extra="allow")

    estateCode: str
    estateName: str | None = None
    estateChinesename: str | None = None
    estateChinesenameSimple: str | None = None
    blocks: list[HangSengBlock] = Field(default_factory=list)


class HangSengDistrict(BaseModel):
    model_config = ConfigDict(extra="allow")

    districtCode: str
    districtName: str | None = None
    districtChinesename: str | None = None
    districtChinesenameSimple: str | None = None
    estates: list[HangSengEstate] = Field(default_factory=list)


class HangSengArea(BaseModel):
    model_config = ConfigDict(extra="allow")

    areaCode: str
    areaName: str | None = None
    areaChinesename: str | None = None
    areaChinesenameSimple: str | None = None
    districts: list[HangSengDistrict] = Field(default_factory=list)


class HangSengAddressTree(BaseModel):
    model_config = ConfigDict(extra="allow")

    areas: list[HangSengArea] = Field(default_factory=list)


class HangSengFloor(BaseModel):
    model_config = ConfigDict(extra="allow")

    floorCode: str
    floorName: str | None = None


class HangSengFlat(BaseModel):
    model_config = ConfigDict(extra="allow")

    flatCode: str
    flatName: str | None = None


class HangSengValuationRequest(BaseModel):
    area: str
    district: str
    estate: str
    block: str
    floor: str
    flat: str
    carpark: str = "0"
    tcKnowledge: str = "on"
    openCarpark: str = "0"


class HangSengValuation(BaseModel):
    model_config = ConfigDict(extra="allow")

    price: str | None = None
    carparkPrice: str | None = None
    grossArea: str | None = None
    saleableArea: str | None = None
    valuationDate: str | None = None
    completionDate: str | None = None
    addressDisp: str | None = None
    addressZhDisp: str | None = None
    addressZhDispSimple: str | None = None
    CWReference: str | None = None
    blockCode: str | None = None
    floorCode: str | None = None
    flatCode: str | None = None
    coveredCarpark: str | None = None
    openCarpark: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def of(cls, raw: dict[str, Any]) -> "HangSengValuation":
        return cls(**raw, raw=raw)
