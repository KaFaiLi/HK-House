"""District-level price analysis + choropleth map.

Normalises every listing's location to one of Hong Kong's 18 administrative
districts, aggregates price metrics (total price and price per net sq ft:
avg / median / min / max), and renders an interactive Folium choropleth.

    uv run python -m hk_house.cli map

Output:
    data/processed/district_stats.csv   -- the aggregated table
    data/processed/hk_price_map.html    -- interactive map
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR, ROOT

log = logging.getLogger("hkhouse.analysis")

GEOJSON = ROOT / "data" / "geo" / "hk18_official.json"
STATS_CSV = PROCESSED_DIR / "district_stats.csv"
MAP_HTML = PROCESSED_DIR / "hk_price_map.html"

# Canonical 18 districts (Chinese, consistent 區 suffix). Order = geojson order.
CANONICAL = [
    "中西區", "灣仔區", "東區", "南區", "油尖旺區", "深水埗區",
    "九龍城區", "黃大仙區", "觀塘區", "荃灣區", "屯門區", "元朗區",
    "北區", "大埔區", "西貢區", "沙田區", "葵青區", "離島區",
]
# geojson 地區 -> canonical (geojson omits 區 on some names)
_GEO_TO_CANON = {
    "中西區": "中西區", "灣仔": "灣仔區", "東區": "東區", "南區": "南區",
    "油尖旺": "油尖旺區", "深水埗": "深水埗區", "九龍城": "九龍城區",
    "黃大仙": "黃大仙區", "觀塘": "觀塘區", "荃灣": "荃灣區", "屯門": "屯門區",
    "元朗": "元朗區", "北區": "北區", "大埔": "大埔區", "西貢": "西貢區",
    "沙田": "沙田區", "葵青": "葵青區", "離島": "離島區",
}

# Neighbourhood / sub-area -> canonical district (for hse28 + centanet noise).
NEIGHBOURHOOD = {d: d for d in CANONICAL}
NEIGHBOURHOOD.update({
    # 中西區
    "中環": "中西區", "上環": "中西區", "西環": "中西區", "堅尼地城": "中西區",
    "西營盤": "中西區", "山頂": "中西區", "石塘咀": "中西區",
    "金鐘": "中西區", "中半山": "中西區", "西半山": "中西區",
    # 灣仔區
    "灣仔": "灣仔區", "銅鑼灣": "灣仔區", "跑馬地": "灣仔區", "大坑": "灣仔區",
    "天后": "灣仔區", "渣甸山": "灣仔區", "寶馬山": "灣仔區",
    # 東區
    "北角": "東區", "鰂魚涌": "東區", "筲箕灣": "東區", "西灣河": "東區",
    "太古": "東區", "柴灣": "東區", "杏花邨": "東區", "小西灣": "東區",
    "康山": "東區", "炮台山": "東區", "康怡": "東區",
    # 南區
    "香港仔": "南區", "鴨脷洲": "南區", "黃竹坑": "南區", "淺水灣": "南區",
    "赤柱": "南區", "石澳": "南區", "數碼港": "南區", "貝沙灣": "南區",
    "薄扶林": "南區", "鋼綫灣": "南區",
    # 油尖旺區
    "尖沙咀": "油尖旺區", "油麻地": "油尖旺區", "旺角": "油尖旺區",
    "大角咀": "油尖旺區", "佐敦": "油尖旺區", "太子": "油尖旺區",
    "奧運": "油尖旺區", "九龍站": "油尖旺區", "西九龍": "油尖旺區",
    # 深水埗區
    "深水埗": "深水埗區", "長沙灣": "深水埗區", "荔枝角": "深水埗區",
    "美孚": "深水埗區", "石硤尾": "深水埗區", "又一村": "深水埗區",
    "南昌": "深水埗區", "大坑東": "深水埗區",
    # 九龍城區
    "九龍城": "九龍城區", "何文田": "九龍城區", "土瓜灣": "九龍城區",
    "紅磡": "九龍城區", "啟德": "九龍城區", "九龍塘": "九龍城區",
    "馬頭角": "九龍城區", "馬頭圍": "九龍城區", "黃埔": "九龍城區",
    "九龍城寨": "九龍城區",
    # 黃大仙區
    "黃大仙": "黃大仙區", "鑽石山": "黃大仙區", "慈雲山": "黃大仙區",
    "樂富": "黃大仙區", "新蒲崗": "黃大仙區", "彩虹": "黃大仙區",
    "牛池灣": "黃大仙區", "橫頭磡": "黃大仙區", "東頭": "黃大仙區",
    "鳳德": "黃大仙區",
    # 觀塘區
    "觀塘": "觀塘區", "藍田": "觀塘區", "油塘": "觀塘區", "牛頭角": "觀塘區",
    "九龍灣": "觀塘區", "秀茂坪": "觀塘區", "茶果嶺": "觀塘區", "順利": "觀塘區",
    "佐敦谷": "觀塘區",
    # 荃灣區
    "荃灣": "荃灣區", "梨木樹": "荃灣區", "深井": "荃灣區", "汀九": "荃灣區",
    "馬灣": "荃灣區",
    # 屯門區
    "屯門": "屯門區", "藍地": "屯門區", "掃管笏": "屯門區",
    # 元朗區
    "元朗": "元朗區", "天水圍": "元朗區", "洪水橋": "元朗區", "錦田": "元朗區",
    "八鄉": "元朗區", "流浮山": "元朗區", "新田": "元朗區", "屏山": "元朗區",
    # 北區
    "粉嶺": "北區", "上水": "北區", "古洞": "北區", "沙頭角": "北區",
    "打鼓嶺": "北區",
    # 大埔區
    "大埔": "大埔區", "太和": "大埔區", "大尾篤": "大埔區", "林村": "大埔區",
    # 西貢區
    "西貢": "西貢區", "將軍澳": "西貢區", "康城": "西貢區", "日出康城": "西貢區",
    "坑口": "西貢區", "寶林": "西貢區", "調景嶺": "西貢區", "清水灣": "西貢區",
    # 沙田區
    "沙田": "沙田區", "大圍": "沙田區", "馬鞍山": "沙田區", "火炭": "沙田區",
    "白石角": "沙田區", "第一城": "沙田區", "烏溪沙": "沙田區", "水泉澳": "沙田區",
    # 葵青區
    "青衣": "葵青區", "葵涌": "葵青區", "葵芳": "葵青區", "荔景": "葵青區",
    "大窩口": "葵青區",
    # 離島區
    "東涌": "離島區", "愉景灣": "離島區", "長洲": "離島區", "坪洲": "離島區",
    "大嶼山": "離島區", "南丫島": "離島區", "梅窩": "離島區", "貝澳": "離島區",
    # extra named estates / sub-areas
    "寶琳": "西貢區", "太古城": "東區", "海怡半島": "南區", "碧瑤灣": "南區",
    "陽明山莊": "灣仔區", "大潭": "南區", "肇輝臺": "東區",
})

# Longest-first keys for the substring fallback (matches "屯門(青山公路)", "北角半山"...).
_SUBSTR_KEYS = sorted(NEIGHBOURHOOD, key=len, reverse=True)


def normalize_district(value: str | None) -> str | None:
    """Map any district/neighbourhood string to one of the 18 canonical districts."""
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    # "前綴(後綴)" -> try both the part inside the parens and the part before them
    candidates = [s]
    if "(" in s:
        inside = s[s.rfind("(") + 1: s.rfind(")")].strip()
        before = s[: s.find("(")].strip()
        candidates += [inside, before]
    candidates += [s.split()[0] if s.split() else s, s.replace("區", "") + "區"]
    for token in candidates:
        if token in NEIGHBOURHOOD:
            return NEIGHBOURHOOD[token]
    # last resort: any known neighbourhood appearing as a substring (longest first)
    for key in _SUBSTR_KEYS:
        if len(key) >= 2 and key in s:
            return NEIGHBOURHOOD[key]
    return None


def _agg(g: pd.DataFrame, col: str) -> dict:
    s = g[col].dropna()
    if s.empty:
        return {"avg": None, "median": None, "min": None, "max": None}
    return {"avg": round(s.mean()), "median": round(s.median()),
            "min": round(s.min()), "max": round(s.max())}


def build_stats(parquet: Path | None = None) -> pd.DataFrame:
    parquet = parquet or (PROCESSED_DIR / "properties.parquet")
    df = pd.read_parquet(parquet)
    df = df[df.tx_type == "sale"].copy()
    df["district"] = df["district"].map(normalize_district)

    unmapped = df["district"].isna().sum()
    log.info("dropped %d rows with unmappable district", unmapped)
    df = df.dropna(subset=["district"])

    rows = []
    for dist, g in df.groupby("district"):
        price = _agg(g, "price")
        ppf = _agg(g, "price_per_net_ft")
        rows.append({
            "district": dist,
            "count": len(g),
            "price_avg": price["avg"], "price_median": price["median"],
            "price_min": price["min"], "price_max": price["max"],
            "ppf_avg": ppf["avg"], "ppf_median": ppf["median"],
            "ppf_min": ppf["min"], "ppf_max": ppf["max"],
        })
    stats = pd.DataFrame(rows).sort_values("ppf_median", ascending=False, na_position="last")
    STATS_CSV.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(STATS_CSV, index=False)
    log.info("wrote %s (%d districts)", STATS_CSV, len(stats))
    return stats


def build_map(stats: pd.DataFrame, output: Path = MAP_HTML) -> Path:
    import branca.colormap as cm
    import folium

    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    by_dist = {r["district"]: r for r in stats.to_dict("records")}

    # Merge stats into geojson properties (canonical name + numbers for tooltip).
    for ft in geo["features"]:
        canon = _GEO_TO_CANON.get(ft["properties"].get("地區", ""), None)
        rec = by_dist.get(canon, {})
        ft["properties"]["district"] = canon
        ft["properties"]["count"] = rec.get("count", 0)
        for k in ("price_avg", "price_median", "price_min", "price_max",
                  "ppf_avg", "ppf_median", "ppf_min", "ppf_max"):
            v = rec.get(k)
            # human-readable: price in $M, ppf in $/ft
            if v is None:
                ft["properties"][k] = "—"
            elif k.startswith("price"):
                ft["properties"][k] = f"${v/1e6:.2f}M"
            else:
                ft["properties"][k] = f"${v:,.0f}"

    m = folium.Map(location=[22.36, 114.13], zoom_start=11, tiles="cartodbpositron")

    def add_layer(metric: str, label: str, fmt_div: float, caption: str, show: bool):
        vals = [r[metric] for r in stats.to_dict("records") if pd.notna(r[metric])]
        colormap = cm.linear.YlOrRd_09.scale(min(vals), max(vals))
        colormap.caption = caption
        lookup = {r["district"]: r[metric] for r in stats.to_dict("records")}

        def style(feat):
            canon = _GEO_TO_CANON.get(feat["properties"].get("地區", ""), None)
            v = lookup.get(canon)
            return {
                "fillColor": colormap(v) if pd.notna(v) else "#cccccc",
                "color": "white", "weight": 1, "fillOpacity": 0.75,
            }

        fg = folium.FeatureGroup(name=label, show=show)
        folium.GeoJson(
            geo, style_function=style,
            tooltip=folium.GeoJsonTooltip(
                fields=["地區", "count",
                        "price_avg", "price_median", "price_min", "price_max",
                        "ppf_avg", "ppf_median", "ppf_min", "ppf_max"],
                aliases=["District", "Listings",
                         "Price avg", "Price median", "Price min", "Price max",
                         "$/ft avg", "$/ft median", "$/ft min", "$/ft max"],
                localize=True, sticky=True,
            ),
        ).add_to(fg)
        fg.add_to(m)
        colormap.add_to(m)

    add_layer("ppf_median", "Median price / net sq ft", 1, "Median net $/ft", True)
    add_layer("price_median", "Median total price", 1e6, "Median total price (HKD)", False)
    folium.LayerControl(collapsed=False).add_to(m)

    output.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output))
    log.info("wrote %s", output)
    return output
