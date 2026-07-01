"""Offline birth-place catalog + resolution (true-solar-time longitude hints).

Extracted verbatim from utils/helpers.py (god-file split). Pure data tables +
deterministic lookup — no numerical computation.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_BIRTH_TIMEZONE = "Asia/Shanghai"

PLACE_TEXT_SANITIZER = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")

PLACE_SPECIFICITY = {
    "province": 1,
    "special_region": 2,
    "city": 3,
    "municipality": 4,
    # County-level units (县级市/区/县) must outscore their parent prefecture-city
    # (3) so "南通海安" -> 海安, not 南通. They are pegged EQUAL to municipality (4),
    # NOT above it: a 2-char county name can appear as an accidental substring of a
    # municipality address ("上海安亭" contains "海安"; "北京通州区" contains "通州").
    # On that tie the earlier-listed entry wins, and municipalities are listed
    # first, so the municipality correctly keeps the match.
    "county": 4,
}

DEFAULT_BIRTH_PLACE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "北京": ("beijing", "peking"),
    "上海": ("shanghai",),
    "天津": ("tianjin",),
    "重庆": ("chongqing",),
    "香港": ("hong kong", "hongkong"),
    "澳门": ("macau", "macao"),
    "台北": ("taipei",),
    "河北": ("hebei",),
    "山西": ("shanxi",),
    "辽宁": ("liaoning",),
    "吉林": ("jilin",),
    "黑龙江": ("heilongjiang", "hei longjiang"),
    "江苏": ("jiangsu",),
    "浙江": ("zhejiang",),
    "安徽": ("anhui",),
    "福建": ("fujian",),
    "江西": ("jiangxi",),
    "山东": ("shandong",),
    "河南": ("henan",),
    "湖北": ("hubei",),
    "湖南": ("hunan",),
    "广东": ("guangdong",),
    "海南": ("hainan",),
    "四川": ("sichuan",),
    "贵州": ("guizhou",),
    "云南": ("yunnan",),
    "陕西": ("shaanxi",),
    "甘肃": ("gansu",),
    "青海": ("qinghai",),
    "台湾": ("taiwan",),
    "内蒙古": ("neimenggu", "inner mongolia"),
    "广西": ("guangxi",),
    "西藏": ("xizang", "tibet"),
    "宁夏": ("ningxia",),
    "新疆": ("xinjiang",),
    "广州": ("guangzhou", "canton"),
    "深圳": ("shenzhen",),
    "杭州": ("hangzhou",),
    "宁波": ("ningbo",),
    "南京": ("nanjing",),
    "苏州": ("suzhou",),
    "武汉": ("wuhan",),
    "成都": ("chengdu",),
    "西安": ("xi'an", "xi an", "xian"),
    "乌鲁木齐": ("urumqi", "wulumuqi", "urumchi"),
    "石家庄": ("shijiazhuang",),
    "济南": ("jinan",),
    "青岛": ("qingdao", "tsingtao"),
    "郑州": ("zhengzhou",),
    "长沙": ("changsha",),
    "福州": ("fuzhou",),
    "厦门": ("xiamen", "amoy"),
    "合肥": ("hefei",),
    "南昌": ("nanchang",),
    "昆明": ("kunming",),
    "贵阳": ("guiyang",),
    "南宁": ("nanning",),
    "海口": ("haikou",),
    "呼和浩特": ("huhehaote", "hohhot"),
    "银川": ("yinchuan",),
    "兰州": ("lanzhou",),
    "西宁": ("xining",),
    "拉萨": ("lhasa", "lasa"),
    "喀什": ("kashi", "kashgar"),
    "纽约": ("new york", "newyork", "nyc"),
    "伦敦": ("london",),
    "东京": ("tokyo",),
    "悉尼": ("sydney",),
}


def normalize_birth_place_text(text: str) -> str:
    """Normalize Chinese/English place text for fuzzy offline matching."""
    normalized_text = unicodedata.normalize("NFKC", text).casefold()
    return PLACE_TEXT_SANITIZER.sub("", normalized_text)


# City-centre latitudes, keyed by the same canonical names used for longitudes
# below. Latitude lives here (rather than in a separate astrology-only table)
# so that one place resolves to longitude *and* latitude together: the BaZi
# true-solar path only needs longitude, but the astrology engine needs both, and
# keeping two parallel tables let them silently drift (a city had a longitude but
# no latitude, so an otherwise-resolvable place was rejected by the chart engine).
# Every entry in KNOWN_BIRTH_PLACE_ENTRIES must have a latitude here — enforced by
# an assertion after the catalog is built, so a new city can't be half-resolved.
KNOWN_BIRTH_PLACE_LATITUDES: Dict[str, float] = {
    # Municipalities and SARs
    "北京": 39.9042,
    "上海": 31.2304,
    "天津": 39.3434,
    "重庆": 29.5630,
    "香港": 22.3193,
    "澳门": 22.1987,
    "台北": 25.0330,
    # Province-level fallbacks
    "河北": 38.0428,
    "山西": 37.8706,
    "辽宁": 41.8057,
    "吉林": 43.8171,
    "黑龙江": 45.8038,
    "江苏": 32.0603,
    "浙江": 30.2741,
    "安徽": 31.8206,
    "福建": 26.0745,
    "江西": 28.6829,
    "山东": 36.6512,
    "河南": 34.7466,
    "湖北": 30.5454,
    "湖南": 28.2282,
    "广东": 23.1291,
    "海南": 20.0440,
    "四川": 30.5728,
    "贵州": 26.6470,
    "云南": 25.0389,
    "陕西": 34.3416,
    "甘肃": 36.0611,
    "青海": 36.6171,
    "台湾": 25.0330,
    "内蒙古": 40.8426,
    "广西": 22.8170,
    "西藏": 29.6525,
    "宁夏": 38.4872,
    "新疆": 43.8256,
    # Broader city coverage
    "广州": 23.1291,
    "深圳": 22.5431,
    "杭州": 30.2741,
    "宁波": 29.8683,
    "南京": 32.0603,
    "苏州": 31.2989,
    "武汉": 30.5928,
    "成都": 30.5728,
    "西安": 34.3416,
    "乌鲁木齐": 43.8256,
    "石家庄": 38.0428,
    "济南": 36.6512,
    "青岛": 36.0671,
    "郑州": 34.7473,
    "长沙": 28.2282,
    "福州": 26.0745,
    "厦门": 24.4798,
    "合肥": 31.8206,
    "南昌": 28.6829,
    "昆明": 25.0389,
    "贵阳": 26.6470,
    "南宁": 22.8170,
    "海口": 20.0440,
    "呼和浩特": 40.8426,
    "银川": 38.4872,
    "兰州": 36.0611,
    "西宁": 36.6171,
    "拉萨": 29.6525,
    "喀什": 39.4704,
    # Additional prefecture-level cities
    "咸阳": 34.3294,
    "宝鸡": 34.3614,
    "南通": 31.9802,
    "无锡": 31.4912,
    "常州": 31.7720,
    "徐州": 34.2058,
    "扬州": 32.3942,
    "盐城": 33.3496,
    "镇江": 32.1882,
    "泰州": 32.4558,
    "温州": 27.9939,
    "绍兴": 30.0023,
    "嘉兴": 30.7522,
    "台州": 28.6562,
    "金华": 29.0784,
    "湖州": 30.8927,
    "大连": 38.9140,
    "鞍山": 41.1086,
    "唐山": 39.6304,
    "保定": 38.8740,
    "邯郸": 36.6256,
    "沧州": 38.3045,
    "廊坊": 39.5375,
    "临沂": 35.1045,
    "潍坊": 36.7069,
    "淄博": 36.8131,
    "济宁": 35.4154,
    "泰安": 36.1944,
    "烟台": 37.4638,
    "威海": 37.5128,
    "洛阳": 34.6197,
    "南阳": 32.9908,
    "开封": 34.7972,
    "新乡": 35.3030,
    "许昌": 34.0357,
    "宜昌": 30.6919,
    "襄阳": 32.0090,
    "株洲": 27.8273,
    "湘潭": 27.8294,
    "衡阳": 26.8939,
    "岳阳": 29.3570,
    "泉州": 24.8741,
    "漳州": 24.5130,
    "赣州": 25.8453,
    "九江": 29.7050,
    "芜湖": 31.3526,
    "绵阳": 31.4677,
    "宜宾": 28.7513,
    "遵义": 27.7066,
    "桂林": 25.2736,
    "柳州": 24.3264,
    "佛山": 23.0218,
    "东莞": 23.0207,
    "珠海": 22.2710,
    "汕头": 23.3535,
    "惠州": 23.1117,
    # International cities
    "纽约": 40.7128,
    "伦敦": 51.5074,
    "东京": 35.6762,
    "悉尼": -33.8688,
}


def make_birth_place_entry(
    canonical_name: str,
    longitude: float,
    *,
    latitude: Optional[float] = None,
    timezone: str = DEFAULT_BIRTH_TIMEZONE,
    level: str = "city",
    aliases: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    """Build one offline address-resolution entry.

    Latitude defaults to the co-located ``KNOWN_BIRTH_PLACE_LATITUDES`` table
    keyed by ``canonical_name`` (callers may still pass an explicit ``latitude``
    to override it for a boundary case).
    """
    resolved_latitude = (
        latitude
        if latitude is not None
        else KNOWN_BIRTH_PLACE_LATITUDES.get(canonical_name)
    )
    merged_aliases = tuple(
        dict.fromkeys(
            (
                canonical_name,
                *DEFAULT_BIRTH_PLACE_ALIASES.get(canonical_name, ()),
                *aliases,
            )
        )
    )
    normalized_aliases = tuple(
        dict.fromkeys(
            normalize_birth_place_text(alias)
            for alias in merged_aliases
            if normalize_birth_place_text(alias)
        )
    )
    return {
        "canonical_name": canonical_name,
        "longitude": longitude,
        "latitude": resolved_latitude,
        "timezone": timezone,
        "level": level,
        "specificity": PLACE_SPECIFICITY[level],
        "aliases": merged_aliases,
        "normalized_aliases": normalized_aliases,
    }


# Offline location hints for true solar time correction. This is still an
# approximate parser: it matches province/city aliases in free-form text and
# falls back to province-level coordinates when no known city appears.
KNOWN_BIRTH_PLACE_ENTRIES = (
    # Municipalities and SARs
    make_birth_place_entry("北京", 116.4074, level="municipality", aliases=("北京市",)),
    make_birth_place_entry("上海", 121.4737, level="municipality", aliases=("上海市",)),
    make_birth_place_entry("天津", 117.2000, level="municipality", aliases=("天津市",)),
    make_birth_place_entry("重庆", 106.5516, level="municipality", aliases=("重庆市",)),
    # 重庆 is a province-sized municipality (~470km E-W); its remote districts sit
    # far from the 渝中 centroid, so "重庆市开州区" silently塌回 the city centre
    # (106.55°E/29.56°N) ~180km from 开州 (108.39°E/31.18°N), rotating the
    # astrology ascendant/midheaven ~1.7°. county level + the longer canonical
    # name ("开州区">"重庆") win the substring contest over the municipality.
    make_birth_place_entry(
        "开州区", 108.3930, latitude=31.1780, level="county", aliases=("开州", "开县")
    ),
    make_birth_place_entry(
        "香港",
        114.1694,
        timezone="Asia/Hong_Kong",
        level="special_region",
        aliases=("香港特别行政区",),
    ),
    make_birth_place_entry(
        "澳门",
        113.5439,
        timezone="Asia/Macau",
        level="special_region",
        aliases=("澳门特别行政区",),
    ),
    make_birth_place_entry(
        "台北",
        121.5654,
        timezone="Asia/Taipei",
        level="special_region",
        aliases=("臺北", "台北市", "臺北市"),
    ),
    # Province-level fallbacks
    make_birth_place_entry("河北", 114.5149, level="province", aliases=("河北省",)),
    make_birth_place_entry("山西", 112.5492, level="province", aliases=("山西省",)),
    make_birth_place_entry("辽宁", 123.4315, level="province", aliases=("辽宁省",)),
    make_birth_place_entry("吉林", 125.3235, level="province", aliases=("吉林省",)),
    make_birth_place_entry("黑龙江", 126.6424, level="province", aliases=("黑龙江省",)),
    make_birth_place_entry("江苏", 119.4210, level="province", aliases=("江苏省",)),
    make_birth_place_entry("浙江", 119.9572, level="province", aliases=("浙江省",)),
    make_birth_place_entry("安徽", 117.2272, level="province", aliases=("安徽省",)),
    make_birth_place_entry("福建", 119.2965, level="province", aliases=("福建省",)),
    make_birth_place_entry("江西", 115.8582, level="province", aliases=("江西省",)),
    make_birth_place_entry("山东", 117.1201, level="province", aliases=("山东省",)),
    make_birth_place_entry("河南", 113.6254, level="province", aliases=("河南省",)),
    make_birth_place_entry("湖北", 114.3419, level="province", aliases=("湖北省",)),
    make_birth_place_entry("湖南", 112.9388, level="province", aliases=("湖南省",)),
    make_birth_place_entry("广东", 113.2665, level="province", aliases=("广东省",)),
    make_birth_place_entry("海南", 110.3312, level="province", aliases=("海南省",)),
    make_birth_place_entry("四川", 104.0758, level="province", aliases=("四川省",)),
    make_birth_place_entry("贵州", 106.6302, level="province", aliases=("贵州省",)),
    make_birth_place_entry("云南", 102.8329, level="province", aliases=("云南省",)),
    make_birth_place_entry("陕西", 108.9398, level="province", aliases=("陕西省",)),
    make_birth_place_entry("甘肃", 103.8343, level="province", aliases=("甘肃省",)),
    make_birth_place_entry("青海", 101.7782, level="province", aliases=("青海省",)),
    make_birth_place_entry(
        "台湾",
        121.5654,
        timezone="Asia/Taipei",
        level="province",
        aliases=("台湾省", "臺灣", "臺灣省"),
    ),
    make_birth_place_entry(
        "内蒙古", 111.6708, level="province", aliases=("内蒙古自治区",)
    ),
    make_birth_place_entry(
        "广西", 108.3200, level="province", aliases=("广西", "广西壮族自治区")
    ),
    make_birth_place_entry("西藏", 91.1322, level="province", aliases=("西藏自治区",)),
    make_birth_place_entry(
        "宁夏", 106.2782, level="province", aliases=("宁夏回族自治区",)
    ),
    make_birth_place_entry(
        "新疆", 87.6168, level="province", aliases=("新疆", "新疆维吾尔自治区")
    ),
    # Broader city coverage
    make_birth_place_entry("广州", 113.2644, aliases=("广州市",)),
    make_birth_place_entry("深圳", 114.0579, aliases=("深圳市",)),
    make_birth_place_entry("杭州", 120.1551, aliases=("杭州市",)),
    make_birth_place_entry("宁波", 121.5503, aliases=("宁波市",)),
    make_birth_place_entry("南京", 118.7969, aliases=("南京市",)),
    make_birth_place_entry("苏州", 120.5853, aliases=("苏州市",)),
    make_birth_place_entry("武汉", 114.3054, aliases=("武汉市",)),
    make_birth_place_entry("成都", 104.0665, aliases=("成都市",)),
    make_birth_place_entry("西安", 108.9398, aliases=("西安市",)),
    make_birth_place_entry("乌鲁木齐", 87.6168, aliases=("乌鲁木齐市",)),
    make_birth_place_entry("石家庄", 114.5149, aliases=("石家庄市",)),
    make_birth_place_entry("济南", 117.1201, aliases=("济南市",)),
    make_birth_place_entry("青岛", 120.3826, aliases=("青岛市",)),
    make_birth_place_entry("郑州", 113.6254, aliases=("郑州市",)),
    make_birth_place_entry("长沙", 112.9388, aliases=("长沙市",)),
    make_birth_place_entry("福州", 119.2965, aliases=("福州市",)),
    make_birth_place_entry("厦门", 118.0894, aliases=("厦门市",)),
    make_birth_place_entry("合肥", 117.2272, aliases=("合肥市",)),
    make_birth_place_entry("南昌", 115.8582, aliases=("南昌市",)),
    make_birth_place_entry("昆明", 102.8329, aliases=("昆明市",)),
    make_birth_place_entry("贵阳", 106.6302, aliases=("贵阳市",)),
    make_birth_place_entry("南宁", 108.3200, aliases=("南宁市",)),
    make_birth_place_entry("海口", 110.3312, aliases=("海口市",)),
    make_birth_place_entry("呼和浩特", 111.6708, aliases=("呼和浩特市",)),
    make_birth_place_entry("银川", 106.2782, aliases=("银川市",)),
    make_birth_place_entry("兰州", 103.8343, aliases=("兰州市",)),
    make_birth_place_entry("西宁", 101.7782, aliases=("西宁市",)),
    make_birth_place_entry("拉萨", 91.1322, aliases=("拉萨市",)),
    make_birth_place_entry("喀什", 75.9898, aliases=("喀什地区", "喀什市")),
    # Additional prefecture-level cities (substring match also resolves the
    # "<city>市<district>区" forms, e.g. "咸阳市秦都区" -> 咸阳). Longitudes are
    # city-centre values; for boundary-time births pass birth_longitude exactly.
    make_birth_place_entry("咸阳", 108.7050, aliases=("咸阳市",)),
    make_birth_place_entry("宝鸡", 107.2380, aliases=("宝鸡市",)),
    make_birth_place_entry("南通", 120.8943, aliases=("南通市",)),
    # 南通下辖县级单位：此前缺录时「南通X」会静默塌回南通市区坐标
    # (120.89°E/31.98°N)。补齐县治坐标 + county 级(specificity 最高)，使更具体的
    # 县名在含父府的地址里胜出。坐标为县级市/区政府驻地，精度与现有市级条目同档。
    make_birth_place_entry(
        "海安", 120.4661, latitude=32.5350, level="county", aliases=("海安市", "海安县")
    ),
    make_birth_place_entry(
        "如皋", 120.5591, latitude=32.3757, level="county", aliases=("如皋市",)
    ),
    make_birth_place_entry(
        "启东", 121.6579, latitude=31.8101, level="county", aliases=("启东市",)
    ),
    make_birth_place_entry(
        "海门", 121.1760, latitude=31.8966, level="county", aliases=("海门区", "海门市")
    ),
    # 南通通州区 deliberately NOT catalogued: its "通州区" alias collides with
    # Beijing's far better-known 通州区 ("北京通州区" would mis-resolve to 江苏).
    make_birth_place_entry(
        "如东", 121.1896, latitude=32.3144, level="county", aliases=("如东县",)
    ),
    make_birth_place_entry("无锡", 120.3019, aliases=("无锡市",)),
    make_birth_place_entry("常州", 119.9740, aliases=("常州市",)),
    make_birth_place_entry("徐州", 117.1840, aliases=("徐州市",)),
    make_birth_place_entry("扬州", 119.4215, aliases=("扬州市",)),
    make_birth_place_entry("盐城", 120.1398, aliases=("盐城市",)),
    make_birth_place_entry("镇江", 119.4250, aliases=("镇江市",)),
    make_birth_place_entry("泰州", 119.9150, aliases=("泰州市",)),
    make_birth_place_entry("温州", 120.6994, aliases=("温州市",)),
    make_birth_place_entry("绍兴", 120.5820, aliases=("绍兴市",)),
    make_birth_place_entry("嘉兴", 120.7555, aliases=("嘉兴市",)),
    make_birth_place_entry("台州", 121.4287, aliases=("台州市",)),
    make_birth_place_entry("金华", 119.6494, aliases=("金华市",)),
    make_birth_place_entry("湖州", 120.0865, aliases=("湖州市",)),
    make_birth_place_entry("大连", 121.6147, aliases=("大连市",)),
    make_birth_place_entry("鞍山", 122.9950, aliases=("鞍山市",)),
    make_birth_place_entry("唐山", 118.1758, aliases=("唐山市",)),
    make_birth_place_entry("保定", 115.4646, aliases=("保定市",)),
    make_birth_place_entry("邯郸", 114.4900, aliases=("邯郸市",)),
    make_birth_place_entry("沧州", 116.8388, aliases=("沧州市",)),
    make_birth_place_entry("廊坊", 116.7038, aliases=("廊坊市",)),
    make_birth_place_entry("临沂", 118.3563, aliases=("临沂市",)),
    make_birth_place_entry("潍坊", 119.1070, aliases=("潍坊市",)),
    make_birth_place_entry("淄博", 118.0480, aliases=("淄博市",)),
    make_birth_place_entry("济宁", 116.5871, aliases=("济宁市",)),
    make_birth_place_entry("泰安", 117.0890, aliases=("泰安市",)),
    make_birth_place_entry("烟台", 121.4479, aliases=("烟台市",)),
    make_birth_place_entry("威海", 122.1201, aliases=("威海市",)),
    make_birth_place_entry("洛阳", 112.4540, aliases=("洛阳市",)),
    make_birth_place_entry("南阳", 112.5288, aliases=("南阳市",)),
    make_birth_place_entry("开封", 114.3074, aliases=("开封市",)),
    make_birth_place_entry("新乡", 113.9268, aliases=("新乡市",)),
    make_birth_place_entry("许昌", 113.8260, aliases=("许昌市",)),
    make_birth_place_entry("宜昌", 111.2865, aliases=("宜昌市",)),
    make_birth_place_entry("襄阳", 112.1220, aliases=("襄阳市", "襄樊")),
    make_birth_place_entry("株洲", 113.1340, aliases=("株洲市",)),
    make_birth_place_entry("湘潭", 112.9440, aliases=("湘潭市",)),
    make_birth_place_entry("衡阳", 112.6072, aliases=("衡阳市",)),
    make_birth_place_entry("岳阳", 113.1290, aliases=("岳阳市",)),
    make_birth_place_entry("泉州", 118.5894, aliases=("泉州市",)),
    make_birth_place_entry("漳州", 117.6471, aliases=("漳州市",)),
    make_birth_place_entry("赣州", 114.9400, aliases=("赣州市",)),
    make_birth_place_entry("九江", 115.9920, aliases=("九江市",)),
    make_birth_place_entry("芜湖", 118.4330, aliases=("芜湖市",)),
    make_birth_place_entry("绵阳", 104.6790, aliases=("绵阳市",)),
    make_birth_place_entry("宜宾", 104.6430, aliases=("宜宾市",)),
    make_birth_place_entry("遵义", 106.9270, aliases=("遵义市",)),
    make_birth_place_entry("桂林", 110.2900, aliases=("桂林市",)),
    make_birth_place_entry("柳州", 109.4280, aliases=("柳州市",)),
    make_birth_place_entry("佛山", 113.1220, aliases=("佛山市",)),
    make_birth_place_entry("东莞", 113.7460, aliases=("东莞市",)),
    make_birth_place_entry("珠海", 113.5530, aliases=("珠海市",)),
    make_birth_place_entry("汕头", 116.6820, aliases=("汕头市",)),
    make_birth_place_entry("惠州", 114.4160, aliases=("惠州市",)),
    # International cities retained from the previous version
    make_birth_place_entry(
        "纽约", -74.0060, timezone="America/New_York", aliases=("纽约市",)
    ),
    make_birth_place_entry("伦敦", -0.1278, timezone="Europe/London"),
    make_birth_place_entry(
        "东京", 139.6917, timezone="Asia/Tokyo", aliases=("东京都",)
    ),
    make_birth_place_entry(
        "悉尼", 151.2093, timezone="Australia/Sydney", aliases=("悉尼市",)
    ),
)

# Drift guard: every catalogued place must resolve to a latitude too, otherwise


_PLACES_MISSING_LATITUDE = [
    entry["canonical_name"]
    for entry in KNOWN_BIRTH_PLACE_ENTRIES
    if entry["latitude"] is None
]
assert not _PLACES_MISSING_LATITUDE, (
    "KNOWN_BIRTH_PLACE_LATITUDES is missing entries for: " f"{_PLACES_MISSING_LATITUDE}"
)


@dataclass(frozen=True)
class BirthPlaceResolution:
    """One resolved address candidate from the offline catalog."""

    canonical_name: Optional[str]
    longitude: Optional[float]
    latitude: Optional[float]
    timezone: Optional[str]
    source: Optional[str]
    level: Optional[str]


def resolve_birth_place_context(
    birth_place: Optional[str],
) -> BirthPlaceResolution:
    """Resolve longitude/timezone hints from a free-form birth place string."""
    if not birth_place or birth_place == "未提供":
        return BirthPlaceResolution(None, None, None, None, None, None)

    normalized_place = normalize_birth_place_text(birth_place)
    return _resolve_birth_place_context_cached(normalized_place)


@lru_cache(maxsize=256)
def _resolve_birth_place_context_cached(
    normalized_place: str,
) -> BirthPlaceResolution:
    """Cache offline place resolution because it is deterministic and reusable."""
    best_match: Optional[Tuple[int, int, int, int, Dict[str, Any]]] = None
    for entry in KNOWN_BIRTH_PLACE_ENTRIES:
        for alias in entry["normalized_aliases"]:
            if alias and alias in normalized_place:
                score = (
                    entry["specificity"],
                    len(alias),
                    len(entry["canonical_name"]),
                    1,
                )
                if best_match is None or score > best_match[:4]:
                    best_match = (*score, entry)

    if best_match is None:
        # Observable, not silent: an uncatalogued place skips true-solar-time
        # longitude correction, and silent fallback here is exactly the bug class
        # fixed in #142/#143. Callers still get an all-None resolution; this just
        # makes the skipped correction visible in logs.
        logger.warning(
            "出生地 %r 不在离线地名库中，已跳过真太阳时经度校正"
            "（如需精确请显式传入经度）。",
            normalized_place,
        )
        return BirthPlaceResolution(None, None, None, None, None, None)

    entry = best_match[4]
    return BirthPlaceResolution(
        canonical_name=entry["canonical_name"],
        longitude=entry["longitude"],
        latitude=entry["latitude"],
        timezone=entry["timezone"],
        source="birth_place",
        level=entry["level"],
    )
