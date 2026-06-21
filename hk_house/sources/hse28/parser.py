"""28Hse parser: scraped card dict -> BaseProperty.

The fetcher extracts structured sub-fields per card:
  district   <- .district_area first link        (e.g. 荔枝角)
  estate     <- .district_area last link          (e.g. 泓景臺)
  unit_desc  <- .district_area .unit_desc          (e.g. "2座 高層 E室")
  area_price <- .areaUnitPrice                     ("實用面積: 471 呎 @19,915 元")
  price_text <- .extra red label                   ("售 $938 萬元")
  tags       <- .tagLabels labels                  (["2 房 , 1 浴室", "向西", ...])

Older raw records (pre-structured) only have a flattened ``text`` blob, so each
field falls back to regexing ``text`` when the structured value is absent.
"""

from __future__ import annotations

import re
from typing import Any

from ...models.base import BaseProperty, PropertyKind, TxType

_AREA = re.compile(r"實用面積[:：]\s*([\d,]+)\s*呎")
_NET_FT_PRICE = re.compile(r"@\s*([\d,]+)\s*元")
_BEDROOMS = re.compile(r"(\d+)\s*房")
_BATHROOMS = re.compile(r"(\d+)\s*浴室")
_DIRECTION = re.compile(r"向([東南西北]+)")
_FLOOR = re.compile(r"(低層|中層|高層|地下|頂層)")
_FLAT = re.compile(r"([A-Za-z0-9]+)\s*室")
# price: "售 $938 萬元" / "$2.3 億元"; unit 萬/億 required (avoids title noise).
_PRICE = re.compile(r"(售|租)?\s*\$\s*([\d,.]+)\s*(萬|億)\s*元")
# fallback location from text blob: between 刊登 and 實用面積
_LOC = re.compile(r"刊登\s*(.+?)\s*實用面積")


def _f(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _search(rx: re.Pattern[str], *texts: str | None) -> str | None:
    for t in texts:
        if t:
            m = rx.search(t)
            if m:
                return m.group(1)
    return None


def _price(price_text: str | None, text: str | None) -> tuple[float | None, TxType]:
    for src in (price_text, text):
        if not src:
            continue
        m = _PRICE.search(src)
        if not m:
            continue
        tx = TxType.RENT if m.group(1) == "租" else TxType.SALE
        val = _f(m.group(2))
        if val is None:
            return None, tx
        val *= 100_000_000 if m.group(3) == "億" else 10_000
        return val, tx
    return None, TxType.SALE


def _unit_desc(raw: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """unit_desc 'building floor flat' -> (building, floor, flat)."""
    seg = raw.get("unit_desc")
    if not seg:
        # fall back to the text-blob location segment
        m = _LOC.search(raw.get("text", "") or "")
        seg = m.group(1).rsplit("|", 1)[-1] if m and "|" in (m.group(1)) else None
    if not seg:
        return None, None, None
    floor = _search(_FLOOR, seg)
    flat = _search(_FLAT, seg)
    building = seg
    for token in (floor, flat):
        if token:
            building = re.sub(re.escape(token) + r"\s*室?", "", building)
    building = _FLOOR.sub("", building).strip(" |") or None
    return building, floor, flat


def _loc_fallback(text: str | None) -> tuple[str | None, str | None]:
    """district, estate from the text blob (old raw without structured fields)."""
    m = _LOC.search(text or "")
    if not m:
        return None, None
    left = m.group(1).split("|", 1)[0].split()
    district = left[0] if left else None
    estate = " ".join(left[1:]) or None
    return district, estate


def to_base(raw: dict[str, Any]) -> BaseProperty:
    text = raw.get("text", "") or ""
    area_price = raw.get("area_price")
    tags = " ".join(raw.get("tags") or [])

    price, tx = _price(raw.get("price_text"), text)
    building, floor, flat = _unit_desc(raw)

    district = raw.get("district")
    estate = raw.get("estate")
    if not district and not estate:
        district, estate = _loc_fallback(text)

    net_area = _search(_AREA, area_price, text)
    net_ft_price = _search(_NET_FT_PRICE, area_price, text)
    bedrooms = _search(_BEDROOMS, tags, text)
    bathrooms = _search(_BATHROOMS, tags, text)
    direction = _search(_DIRECTION, tags, text)

    return BaseProperty(
        source="hse28",
        source_id=str(raw["id"]),
        url=raw.get("url"),
        tx_type=tx,
        kind=PropertyKind.RESIDENTIAL,
        price=price,
        price_per_net_ft=_f(net_ft_price),
        net_area_ft=_f(net_area),
        estate=estate,
        building=building,
        district=district,
        floor=floor,
        flat=flat,
        bedrooms=int(bedrooms) if bedrooms else None,
        bathrooms=int(bathrooms) if bathrooms else None,
        direction=direction,
        raw=raw,
    )
