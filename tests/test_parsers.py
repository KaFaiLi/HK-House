"""Offline parser tests: raw record -> BaseProperty mapping."""

from hk_house.models.base import PropertyKind, TxType
from hk_house.sources.centanet.parser import to_base as centanet_base
from hk_house.sources.house730.parser import to_base as house730_base
from hk_house.sources.hangseng.parser import to_base as hangseng_base
from hk_house.sources.hse28.parser import to_base as hse28_base
from hk_house.sources.midland.parser import to_base as midland_base


def test_centanet_estate_combines_big_and_phase():
    raw = {"id": "x", "bigEstateName": "藍天海岸", "estateName": "1期",
           "priceInfo": {}, "areaInfo": {}, "unitPriceInfo": {}, "scope": {}}
    assert centanet_base(raw).estate == "藍天海岸 1期"
    raw2 = {"id": "y", "bigEstateName": "", "estateName": "綠楊新邨",
            "priceInfo": {}, "areaInfo": {}, "unitPriceInfo": {}, "scope": {}}
    assert centanet_base(raw2).estate == "綠楊新邨"


def test_district_normalization():
    from hk_house.analysis import normalize_district
    assert normalize_district("荃灣區") == "荃灣區"
    assert normalize_district("將軍澳 (西貢區)") == "西貢區"
    assert normalize_district("屯門(青山公路)") == "屯門區"      # paren + substring
    assert normalize_district("荔枝角") == "深水埗區"            # hse28 neighbourhood
    assert normalize_district("北角半山") == "東區"              # substring fallback
    assert normalize_district("珠海") is None                    # mainland -> excluded


def test_centanet_mapping():
    raw = {
        "id": "abc-123",
        "refNo": "CMI642",
        "postType": "S",
        "unitType": "分層單位",
        "estateName": "綠楊新邨",
        "buildingName": "J座",
        "address": "蕙荃路22-66號",
        "yAxis": "中層",
        "xAxis": "1室",
        "bedroomCount": 3,
        "buildingAge": 43,
        "direction": "西北",
        "propertyPriceHkd": 7500000,
        "priceInfo": {"price": 7500000},
        "areaInfo": {"size": 671, "nSize": 582},
        "unitPriceInfo": {"unitPrice": 11177, "nUnitPrice": 12886},
        "scope": {"terr": "新界西", "db": "荃灣區"},
    }
    b = centanet_base(raw)
    assert b.source == "centanet" and b.source_id == "abc-123"
    assert b.tx_type is TxType.SALE and b.kind is PropertyKind.RESIDENTIAL
    assert b.price == 7500000 and b.gross_area_ft == 671 and b.net_area_ft == 582
    assert b.estate == "綠楊新邨" and b.district == "荃灣區" and b.bedrooms == 3
    assert b.key == "centanet:abc-123"


def test_midland_nested_location():
    raw = {
        "serial_no": "M350182538",
        "tx_type": ["S"],
        "price_hkd": 4980000,
        "area": 658,
        "net_area": 493,
        "price_over_area": 7568,
        "price_over_net_area": 10101,
        "bedroom": 2,
        "flat": "C",
        "estate": {"id": "E1", "name": "栢慧豪園"},
        "phase": {"id": "P1", "name": "一期"},
        "region": {"id": "30", "name": "新界"},
        "district": {"id": "301401", "name": "天水圍"},
        "url_desc": "https://www.midland.com.hk/zh-hk/property/foo-M350182538",
    }
    b = midland_base(raw)
    assert b.source_id == "M350182538" and b.price == 4980000
    assert b.estate == "栢慧豪園" and b.district == "天水圍" and b.region == "新界"
    assert b.url.startswith("https://www.midland.com.hk/")


def test_house730_mapping():
    raw = {
        "propertyID": 9089382,
        "rentalType": 1,
        "propertyCategoryWithCulture": "住宅",
        "estateName": "福祥大廈",
        "estateAddressWithCulture": "北帝街111號",
        "buildingAge": 29,
        "buildingArea": 500.0,
        "saleableArea": 341.0,
        "salePrice": 5780000.0,
        "buildingAvgPrice": 11560.0,
        "saleableAvgPrice": 16950.15,
        "unitFloorWithCulture": "低層",
        "propertyNo": "EL05",
        "roomNumber": 2,
        "toiletNumber": 1,
        "regionName": "九龍",
        "zoneName": "土瓜灣",
    }
    b = house730_base(raw)
    assert b.source_id == "9089382" and b.tx_type is TxType.SALE
    assert b.price == 5780000 and b.bathrooms == 1 and b.building_age == 29
    assert b.district == "土瓜灣" and b.region == "九龍"


def test_hse28_text_parsing():
    raw = {
        "id": "3899923",
        "url": "https://www.28hse.com/buy/apartment/property-3899923",
        "title": "屯門站上蓋瓏門3房套",
        "text": (
            "11 黃金 屯門站上蓋瓏門3房套 7 分鐘前 刊登 屯門 瓏門 | 第二期 第6座 中層 "
            "實用面積: 663 呎 @16,290 元 美聯物業 售 $1,080 萬元 3 房 , 2 浴室 "
            "私人屋苑 望市景 向東南"
        ),
    }
    b = hse28_base(raw)
    assert b.source_id == "3899923" and b.tx_type is TxType.SALE
    assert b.price == 10_800_000          # 1,080 萬
    assert b.net_area_ft == 663 and b.price_per_net_ft == 16290
    assert b.district == "屯門" and b.estate == "瓏門" and b.building == "第二期 第6座"
    assert b.floor == "中層" and b.bedrooms == 3 and b.bathrooms == 2
    assert b.direction == "東南"


def test_hse28_yi_price_unit():
    raw = {"id": "1", "text": "刊登 山頂 某豪宅 高層 實用面積: 3000 呎 售 $2.5 億元 4 房"}
    b = hse28_base(raw)
    assert b.price == 250_000_000          # 2.5 億


def test_hse28_structured_fields():
    # mirrors the structured dict the fetcher now extracts from the card DOM
    raw = {
        "id": "3899959",
        "url": "https://www.28hse.com/buy/apartment/property-3899959",
        "title": "西南海景 特色主人房觀景窗",
        "district": "荔枝角",
        "estate": "泓景臺",
        "unit_desc": "2座 高層 E室",
        "area_price": "實用面積: 471 呎 @19,915 元",
        "price_text": "售 $938 萬元",
        "tags": ["2 房 , 1 浴室", "向西", "私人屋苑"],
        "text": "... 荔枝角 泓景臺 | 2座 高層 E室 實用面積: 471 呎 @19,915 元 售 $938 萬元 ...",
    }
    b = hse28_base(raw)
    assert b.district == "荔枝角" and b.estate == "泓景臺"
    assert b.building == "2座" and b.floor == "高層" and b.flat == "E"
    assert b.net_area_ft == 471 and b.price_per_net_ft == 19915
    assert b.price == 9_380_000
    assert b.bedrooms == 2 and b.bathrooms == 1 and b.direction == "西"


def test_hangseng_valuation_mapping():
    raw = {
        "carparkPrice": "0",
        "addressZhDispSimple": "香港, 铜锣湾, 兴发街42号, 维景花园, A座, 10楼, A1室",
        "blockCode": "5711",
        "grossArea": "620",
        "flatCode": "A1",
        "CWReference": "64077232",
        "saleableArea": "520",
        "addressZhDisp": "香港, 銅鑼灣, 興發街42號, 維景花園, A座, 10樓, A1室",
        "valuationDate": "21/06/2026",
        "coveredCarpark": "0",
        "price": "9440000",
        "addressDisp": "Flat A1, 10/F, Block/Tower A, Viking Garden, 42 Hing Fat Street, Causeway Bay, Hong Kong",
        "completionDate": "03/1977",
        "openCarpark": "0",
        "floorCode": "10",
    }
    b = hangseng_base(raw)
    assert b.source == "hangseng" and b.source_id == "64077232:5711:10:A1"
    assert b.tx_type is TxType.SALE and b.kind is PropertyKind.RESIDENTIAL
    assert b.price == 9_440_000 and b.gross_area_ft == 620 and b.net_area_ft == 520
    assert b.price_per_gross_ft == 9_440_000 / 620
    assert b.price_per_net_ft == 9_440_000 / 520
    assert b.address == "香港, 銅鑼灣, 興發街42號, 維景花園, A座, 10樓, A1室"
    assert b.building == "5711" and b.floor == "10" and b.flat == "A1"
