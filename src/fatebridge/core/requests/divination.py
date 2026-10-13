"""Request contracts for divination."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from fatebridge.core.requests.base import _DeferredModel


class MeihuaAnalysisRequest(_DeferredModel):
    """Request model for time-seeded Mei Hua Yi Shu analysis."""

    analysis_year: int = Field(description="Analysis year, e.g., 2028")
    analysis_month: int = Field(ge=1, le=12, description="Analysis month (1-12)")
    analysis_day: int = Field(ge=1, le=31, description="Analysis day (1-31)")
    analysis_hour: int = Field(ge=0, le=23, description="Analysis hour (0-23)")
    analysis_minute: int = Field(
        default=0, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_timezone: Optional[str] = Field(
        default=None, description="Analysis timezone (IANA name or UTC offset)"
    )
    question: Optional[str] = Field(
        default=None, description="Question or topic for the divination context"
    )


class GuaLookupRequest(_DeferredModel):
    """Request model for trigram/hexagram lookup."""

    query: str = Field(description="Hexagram/trigram name or binary code")
    lookup_mode: str = Field(
        default="auto",
        description="Lookup mode: auto, hexagram, or trigram",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class GuaMeiyiRequest(_DeferredModel):
    """Request model for batch Meiyi hexagram meanings."""

    name: List[str] = Field(description="Trigram or hexagram names/codes")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class TongSheFaRequest(_DeferredModel):
    """Request model for tongshefa."""

    taiyin: Optional[str] = Field(default="巽", description="Taiyin trigram")
    taiyang: Optional[str] = Field(default="坤", description="Taiyang trigram")
    shaoyang: Optional[str] = Field(default="震", description="Shaoyang trigram")
    shaoyin: Optional[str] = Field(default="震", description="Shaoyin trigram")


class SixYaoLineRequest(_DeferredModel):
    """One six-yao line item."""

    value: int = Field(ge=0, le=1, description="0 for yin, 1 for yang")
    change: bool = Field(default=False, description="Whether the line is moving")
    god: Optional[str] = Field(default=None, description="Optional six-god label")
    name: Optional[str] = Field(default=None, description="Optional line label")


class SixYaoRequest(_DeferredModel):
    """Request model for sixyao."""

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(default=None, description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, description="GPS longitude")
    question: Optional[str] = Field(default=None, description="Question or topic")
    gua_code: Optional[str] = Field(default=None, description="Current hexagram code")
    changed_code: Optional[str] = Field(
        default=None, description="Changed hexagram code"
    )
    lines: List[SixYaoLineRequest] = Field(
        default_factory=list, description="Optional six lines"
    )
    method: str = Field(
        default="auto",
        description=(
            "起卦方式：auto（默认，缺卦则按时刻时间起卦）/ coin（真·摇钱起卦，"
            "系统随机六掷）/ time（强制时间起卦）。提供 coins/lines/gua_code 时自动按其起卦。"
        ),
    )
    coins: Optional[List[int]] = Field(
        default=None,
        description=(
            "摇钱起卦六掷之和（初爻→上爻），每掷为三枚铜钱之和 6/7/8/9"
            "（字面=2、背面=3）。提供则按真实摇出的铜钱结果装卦。"
        ),
    )
    seed: Optional[int] = Field(
        default=None,
        description="随机摇钱起卦的随机种子（method=coin 且未提供 coins 时），用于复现同一卦。",
    )


class SuZhanRequest(_DeferredModel):
    """Request model for suzhan."""

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(default=None, description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, description="GPS longitude")
    szchart: int = Field(
        default=0, description="宿占盘模式开关（透传至宿曜引擎；默认 0）"
    )
    szshape: int = Field(
        default=0, description="宿占盘形态开关（透传至宿曜引擎；默认 0）"
    )
    house_start_mode: int = Field(
        default=1,
        description="宫位起始模式（透传至宿曜引擎；默认 1）",
    )
    doubing_su28: bool = Field(
        default=True,
        description="是否按斗柄(doubing)标注二十八宿(su28)；默认开启",
    )
    hsys: int = Field(
        default=8,
        description="Offline house system selector; standard suzhan supports 0..8 with the same FateBridge local house semantics as core chart",
    )
    zodiacal: int = Field(
        default=0,
        description="Offline zodiac selector; standard suzhan supports 0=tropical and 1=sidereal(Lahiri-like)",
    )


class CanpingRequest(_DeferredModel):
    """Request model for canping (邵子参评数 / 金锁银匙)."""

    date: str = Field(description="Birth date string, e.g. 1990-06-15")
    time: str = Field(description="Birth time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(
        default=None, description="Latitude text or decimal (optional)"
    )
    lon: Optional[str] = Field(
        default=None,
        description="Longitude text or decimal; required when true solar time is on",
    )
    gps_lat: Optional[float] = Field(default=None, description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, description="GPS longitude")
    gender: Optional[str] = Field(
        default="男",
        description=(
            "性别 男/女 — 选择本命男/女断语。接受 男/女、male/female 等写法；"
            "省略默认按男命（男）起盘。"
        ),
    )
    method: str = Field(
        default="ming",
        description="取法: ming 明法(月支反向取日宫支) or gu 古法(八字日支)",
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Apply true solar time correction (needs lon); default on — 数算 derives from the BaZi pillars",
    )


class HeluoRequest(_DeferredModel):
    """Request model for heluo (河洛理数)."""

    date: str = Field(description="Birth date string, e.g. 1990-06-15")
    time: str = Field(description="Birth time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(
        default=None, description="Latitude text or decimal (optional)"
    )
    lon: Optional[str] = Field(
        default=None,
        description="Longitude text or decimal; required when true solar time is on",
    )
    gps_lat: Optional[float] = Field(default=None, description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, description="GPS longitude")
    gender: Optional[str] = Field(
        default="男",
        description=(
            "性别 男/女 — 影响起命相盪与元堂推导。接受 男/女、male/female 等写法；"
            "省略默认按男命（男）起盘。"
        ),
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Apply true solar time correction (needs lon); default on — 数算 derives from the BaZi pillars",
    )


class OtherBuRequest(_DeferredModel):
    """Request model for otherbu."""

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(default=None, description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, description="GPS longitude")
    tradition: bool = Field(
        default=False, description="Traditional mode without outer planets"
    )
    sign: Optional[str] = Field(default="Aries", description="Dice sign")
    house: int = Field(default=0, ge=0, le=11, description="Dice house index (0-11)")
    planet: Optional[str] = Field(default="Sun", description="Dice planet")
    hsys: int = Field(
        default=8,
        description="Offline house system selector; supports 0..8 via local Swiss house cusps",
    )
    zodiacal: int = Field(
        default=0,
        description="Offline zodiac selector; supports 0=tropical and 1=sidereal(Lahiri-like)",
    )
    question: Optional[str] = Field(default=None, description="Question or topic")


class SanShiUnitedRequest(_DeferredModel):
    """Request model for sanshiunited."""

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(default=None, description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, description="GPS longitude")
    qimen_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional qimen settings",
    )
    taiyi_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional taiyi settings",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    liureng_yue: Optional[str] = Field(
        default=None,
        description="Optional liureng month-general override",
    )
    liureng_is_diurnal: Optional[bool] = Field(
        default=None,
        description="Optional liureng day/night override",
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Enable local true solar time correction before sanshi aggregation (default on — 式占 keys off the apparent-solar 时辰)",
    )
