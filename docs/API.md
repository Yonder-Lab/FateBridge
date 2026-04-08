# FateBridge API 文档

完整的 FateBridge API 参考，包括所有端点、参数和响应格式。

## 目录

- [REST API](#rest-api)
- [FastMCP API](#fastmcp-api)
- [数据类型](#数据类型)
- [错误处理](#错误处理)
- [代码示例](#代码示例)

---

## REST API

### 基础信息

- **基础 URL**: `http://localhost:8000`
- **默认端口**: `8000`
- **内容类型**: `application/json`

### 可用端点

#### 1. 个人命理分析

**端点**: `POST /api/calculate`

计算单个人的完整命理分析，包括四柱、五行、十神和格局信息。

**请求**:

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": true,
    "birth_place": "北京"
  }'
```

**请求体**:

| 字段 | 类型 | 必需 | 说明 | 范围/示例 |
|------|------|------|------|----------|
| `name` | string | 否 | 姓名 | 默认："未提供" |
| `gender` | string | 否 | 性别 | "男", "女", 默认："未知" |
| `birth_year` | integer | **是** | 出生年份 | 1900-2100 |
| `birth_month` | integer | **是** | 出生月份 | 1-12 |
| `birth_day` | integer | **是** | 出生日期 | 1-31（需要符合月份）|
| `birth_hour` | integer | **是** | 出生时辰 | 0-23（24小时制）|
| `birth_minute` | integer | 否 | 出生分钟 | 0-59，默认：0 |
| `birth_place` | string | 否 | 出生地点 | 支持中文、英文和拼音地址文本，默认："未提供" |
| `birth_timezone` | string | 否 | 出生时区 | IANA 名称或 `UTC+08:00` |
| `birth_longitude` | number | 否 | 出生地经度 | -180 到 180 |
| `use_true_solar_time` | boolean | 否 | 是否启用真太阳时修正 | 默认：false |

**响应 (200 OK)**:

```json
{
  "person_info": {
    "name": "张三",
    "birth_datetime": "1990年05月15日 10时30分",
    "normalized_birth_datetime": "1990年05月15日 10时19分",
    "gender": "男",
    "birth_place": "北京",
    "birth_timezone": "Asia/Shanghai",
    "birth_longitude": 116.4074,
    "time_adjustment": {
      "applied": true,
      "timezone": "Asia/Shanghai",
      "longitude": 116.4074,
      "longitude_source": "birth_place",
      "resolved_place": "北京",
      "resolution_level": "municipality",
      "longitude_correction_minutes": -14.37,
      "equation_of_time_minutes": 3.75,
      "total_correction_minutes": -10.62
    }
  },
  "four_pillars": {
    "year": {
      "stem": "庚",
      "branch": "午"
    },
    "month": {
      "stem": "辛",
      "branch": "巳"
    },
    "day": {
      "stem": "庚",
      "branch": "辰"
    },
    "hour": {
      "stem": "辛",
      "branch": "巳"
    }
  },
  "day_master": {
    "stem": "庚",
    "element": "金",
    "polarity": "阳",
    "strength": "中强"
  },
  "element_distribution": {
    "木": 0,
    "火": 20,
    "土": 20,
    "金": 40,
    "水": 20
  },
  "favorable_elements": ["火", "木"],
  "ten_gods": {
    "year": [...],
    "month": [...],
    "day": [...],
    "hour": [...]
  },
  "patterns": {
    "harmony": {...},
    "clash": {...},
    "special": {...}
  },
  "calendar_context": {
    "timezone": "Asia/Shanghai",
    "solar_datetime": "1990-05-15 10:19:00",
    "current_solar_term": {
      "name": "立夏",
      "datetime": "1990-05-06 03:27:00",
      "date_key": "19900506",
      "day_ganzhi": "丙寅"
    },
    "next_solar_term": {
      "name": "小满",
      "datetime": "1990-05-21 16:37:00",
      "date_key": "19900521",
      "day_ganzhi": "辛巳"
    },
    "bazi_month_boundary": {
      "branch": "巳",
      "month_index": 3
    },
    "lunar_calendar": {
      "display": "四月廿一",
      "jieqi": "立夏",
      "jiedelta": "立夏后第9天",
      "meihua": {
        "base_hexagram": {
          "name": "地水师"
        },
        "changed_hexagram": {
          "name": "山水蒙"
        },
        "summary": "梅花时卦得地水师，动6爻，之山水蒙；上卦坤、下卦坎，五行关系为上制下。"
      }
    }
  }
}
```

**响应字段说明**:

- **person_info**: 个人基本信息
- **normalized_birth_datetime**: 真太阳时修正后的出生时间（未启用时与原时间一致）
- **time_adjustment**: 时间修正元数据，包括时区、经度来源、离线解析出的地点与修正分钟数
  - `resolved_place`: 当系统根据 `birth_place` 命中内置地点库时，返回实际采用的地点名
  - `resolution_level`: 地点命中层级，例如 `city`、`province`、`municipality`
- **four_pillars**: 四柱（年、月、日、时）
  - `stem`: 天干（10个）
  - `branch`: 地支（12个）
- **day_master**: 日主信息
  - `element`: 五行属性（木、火、土、金、水）
  - `polarity`: 阴阳属性
  - `strength`: 强弱程度（弱、一般、中强、强、极强）
- **element_distribution**: 五行分布百分比
- **favorable_elements**: 喜用神列表
- **ten_gods**: 十神分析
- **patterns**: 格局分析
- **calendar_context**: 历法辅助上下文
  - `current_solar_term` / `next_solar_term`: 当前与下一节气
  - `bazi_month_boundary`: 当前所处月令边界、月支与距下一节的天数
  - `lunar_calendar`: 农历日期、节气标记，以及基于农历月日和时支生成的梅花时卦辅助信息

**错误响应**:

```json
{
  "detail": "Invalid birth date: 1990-02-30"
}
```

状态码: `400 Bad Request` - 输入参数无效

---

#### 2. 健康检查

**端点**: `GET /health`

健康检查端点，用于监控 API 可用性。

**请求**:

```bash
curl http://localhost:8000/health
```

**响应 (200 OK)**:

```json
{
  "status": "healthy"
}
```

---

#### 2.1 核心星盘与派生星盘

**端点族**:

- `POST /api/astro/chart`
- `POST /api/astro/chart13`
- `POST /api/astro/hellen`
- `POST /api/astro/guolao`
- `POST /api/astro/india`
- `POST /api/astro/germany`

用于生成 FateBridge 离线近似的核心星盘、派生盘与中点盘。各端点共用同一套出生信息请求体，`germany` 在此基础上再派生中点层。

**公共请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 否 | 姓名，默认 `"未提供"` |
| `birth_year` | integer | **是** | 出生年份 |
| `birth_month` | integer | **是** | 出生月份，1-12 |
| `birth_day` | integer | **是** | 出生日期，1-31 |
| `birth_hour` | integer | **是** | 出生小时，0-23 |
| `birth_minute` | integer | 否 | 出生分钟，0-59，默认 `0` |
| `birth_timezone` | string | 否 | IANA 时区名或 UTC offset，默认 `UTC` |
| `birth_longitude` | number | **是** | 出生经度，-180 到 180 |
| `birth_latitude` | number | **是** | 出生纬度，-90 到 90 |
| `birth_place` | string | 否 | 出生地点，默认 `"未提供"` |
| `hsys` | integer | 否 | 可选离线宫制覆盖；当前支持 `0=整宫制`、`1=Alcabitus`、`2=Regiomontanus`、`3=Placidus`、`4=Koch`、`5=Vehlow Equal`、`6=Polich Page`、`7=Sripati`、`8=天顶为10宫中点等宫制`。省略时保留各盘型默认值 |
| `zodiacal` | integer | 否 | 可选离线黄道覆盖；当前支持 `0=回归黄道`、`1=恒星黄道(Lahiri-like)`。省略时保留各盘型默认值 |

**盘型默认语义**:

- `chart / chart13`: `equal + tropical`
- `hellen / guolao`: `whole_sign + tropical`
- `india`: `whole_sign + sidereal`
- `germany`: 继承其底层基准 `chart` 的 `hsys / zodiacal` 结果

**返回重点**:

- `chart_profile.house_system / house_system_code / house_system_source`: 当前实际采用的离线宫制，以及是否来自盘型默认值还是显式覆盖
- `chart_profile.zodiac / zodiacal / zodiac_label_zh / ayanamsha`: 当前实际采用的黄道模式；`zodiacal=1` 时返回 sidereal 标签与 ayanamsha
- `angles.ascendant / angles.midheaven`: 实际起盘角点
- `houses`: 当前宫制下的 12 宫数据；整宫制时一宫宫头会锚定在上升所在星座的 0 度
- `planets`: 星体列表；`chart13` 会额外附带 `sector13`，`guolao` 会附带 `su28`，`india` 会附带 `nakshatra`
- `germany.base_chart`: 中点盘的底层基准 chart；`midpoints / midpoint_aspects` 为进一步派生层

---

#### 3. 梅花时卦分析

**端点**: `POST /api/divination/meihua`

根据指定时刻生成梅花易数时卦，返回本卦、变卦、互卦、综卦与体用关系。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `analysis_year` | integer | **是** | 起卦年份 |
| `analysis_month` | integer | **是** | 起卦月份，1-12 |
| `analysis_day` | integer | **是** | 起卦日期，1-31 |
| `analysis_hour` | integer | **是** | 起卦时辰，0-23 |
| `analysis_minute` | integer | 否 | 起卦分钟，默认：0 |
| `analysis_timezone` | string | 否 | 起卦时区，默认：`Asia/Shanghai` |
| `question` | string | 否 | 占问主题 |

**返回重点**:

- `analysis_context`: 起卦时刻、时区、农历日期与节气上下文
- `four_pillars`: 起卦时刻对应四柱
- `meihua.base_hexagram`: 本卦
- `meihua.changed_hexagram`: 变卦
- `meihua.mutual_hexagram`: 互卦
- `meihua.opposite_hexagram`: 综卦
- `meihua.*.judgement / image / favorable / caution`: 各卦的离线断辞、卦象、宜为与所忌
- `meihua.body_use_relation`: 体用五行关系
- `interpretation.question_domain`: 自动识别的问事领域
- `interpretation.moving_line_phase`: 动爻所对应的事情阶段
- `interpretation.line_oracles`: 本卦 1-6 爻的逐条推演表，含各自变卦、体用与摘要
- `interpretation.moving_line_oracle`: 动爻所在爻位的细断、时机、宜忌与问事修正
- `interpretation.base_oracle / changed_oracle / mutual_oracle / opposite_oracle`: 提炼后的四层卦义断辞
- `interpretation.action_hint / risk_hint`: 面向问事的可为提示与风险提示
- `interpretation.judgement_outline`: 按本卦、变卦、体用、互卦、综卦组织的占断骨架
- `interpretation.comprehensive_judgement`: 可直接使用的综合摘要

---

#### 3.1 Phase 2 本地技法接口

以下 5 个接口均直接调用 FateBridge 离线内核，不依赖外部 runtime；当前仓库也已用黄金样例回归测试锁定主要输出合同。

##### 3.1.1 统摄法

**端点**: `POST /api/divination/tongshefa`

**关键参数**:

- `taiyin` / `taiyang` / `shaoyang` / `shaoyin`: 四象对应八卦，默认 `巽 / 坤 / 震 / 震`

**返回重点**:

- `tongshefa.baseLeft / baseRight`: 左右本卦
- `tongshefa.hiddenLeft / hiddenRight`: 潜藏卦
- `tongshefa.harmonyLeft / harmonyRight`: 亲和卦
- `tongshefa.main_relation`: 主关系，如 `思同实`、`思克实`
- `snapshot_text`: 统摄法快照文本
- `summary`: 汇总摘要

##### 3.1.2 六爻 / 易卦

**端点**: `POST /api/divination/sixyao`

**关键参数**:

- `date` / `time` / `zone`: 起卦时刻
- `lat` / `lon` / `gpsLat` / `gpsLon`: 可选地理输入
- `gua_code` / `changed_code`: 显式指定本卦 / 之卦编码
- `lines`: 六爻明细数组，元素包含 `value`、`change`、可选 `god` / `name`
- `question`: 可选问事主题

**返回重点**:

- `current_code` / `changed_code`: 本卦 / 之卦编码
- `moving_lines`: 动爻序号
- `current_hexagram` / `changed_hexagram`: 六十四卦信息
- `lines`: 归一化后的六爻明细
- `descriptions`: 六爻摘要说明
- `snapshot_text`: 六爻快照文本

##### 3.1.3 宿占 / 宿盘

**端点**: `POST /api/divination/suzhan`

**关键参数**:

- `date` / `time` / `zone`: 起盘时刻
- `lat` / `lon` / `gpsLat` / `gpsLon`: 地理位置
- `szchart`: 本地盘型开关；`0` 为标准本地盘，`1` 为 `guolao_chart`
- `szshape`: 宫位方向开关；`0` 顺布，`1` 逆布
- `houseStartMode`: 宫位起点模式；`1` 沿用本地宫头，`2` 以整宫起点重建 house ring
- `doubingSu28`: 是否把二十八宿标签写入星体对象
- `hsys`: 标准宿盘当前离线支持 `0=整宫制`、`1=Alcabitus`、`2=Regiomontanus`、`3=Placidus`、`4=Koch`、`5=Vehlow Equal`、`6=Polich Page`、`7=Sripati`、`8=天顶为10宫中点等宫制`；默认 `8`
- `zodiacal`: 标准宿盘当前离线支持 `0=回归黄道`、`1=恒星黄道(Lahiri-like)`；默认 `0`
  `szchart=1` 的果老盘模式保持 FateBridge 固定离线语义，不支持额外切换

**返回重点**:

- `params.chartVariant`: 实际采用的本地盘型
- `params.houseOrientation`: `forward` 或 `reverse`
- `params.houseSystemResolved`: 标准宿盘实际采用的宫制
- `params.zodiacMode`: 标准宿盘实际采用的黄道模式
- `params.zodiacLabelZh / ayanamsha`: `zodiacal=1` 时返回的黄道中文标签与 ayanamsha
- `chart.houses`: 重建后的宿盘宫位；`hsys=1..8` 且 `houseStartMode=1` 时会保留对应离线 cusp 结构，不再统一退化成等宽 30° ring
- `chart.objects`: 星体 / 点位列表；启用时会带 `su28`
- `snapshot_text`: 宿盘宫位与星曜摘要

##### 3.1.4 占星骰子 / OtherBu

**端点**: `POST /api/divination/otherbu`

**关键参数**:

- `date` / `time` / `zone`: 起盘时刻
- `lat` / `lon` / `gpsLat` / `gpsLon`: 地理位置
- `tradition`: 是否关闭三王星
- `sign` / `house` / `planet`: 骰面指定的星座、宫位与行星
- `hsys`: 当前离线支持 `0=整宫制`、`1=Alcabitus`、`2=Regiomontanus`、`3=Placidus`、`4=Koch`、`5=Vehlow Equal`、`6=Polich Page`、`7=Sripati`、`8=天顶为10宫中点等宫制`；默认 `8`
- `zodiacal`: 当前离线支持 `0=回归黄道`、`1=恒星黄道(Lahiri-like)`；默认 `0`
- `question`: 可选问事主题

**返回重点**:

- `planet` / `sign` / `house`: 当前骰面
- `chart.params.houseSystemResolved`: 本地天象盘实际采用的宫制
- `chart.params.zodiacMode`: 本地天象盘实际采用的黄道模式
- `chart.params.zodiacLabelZh`: `zodiacal=1` 时返回黄道中文标签
- `chart.params.ayanamsha`: `zodiacal=1` 时返回当前离线 ayanamsha
- `chart.chart.houses`: 当前离线宫制真实转换后的 house cusps；`1..7` 不再退化成等宽 30° house ring
- `diceChart.params.diceHouse1Longitude`: 本地重建后的骰子盘一宫起点
- `diceChart.chart.houses`: 与骰面一致的 house ring
- `diceChart.chart.objects`: 按新 house ring 重新归宫后的星体列表
- `chart`: 对应时刻的本地天象盘
- `snapshot_text`: 骰子盘 + 天象盘快照

##### 3.1.5 三式合一

**端点**: `POST /api/divination/sanshiunited`

**关键参数**:

- `date` / `time` / `zone`: 起盘时刻
- `lat` / `lon` / `gpsLat` / `gpsLon`: 地理位置
- `qimen_options.layout`: 当前支持 `direct` / `fly` / `mirror` / `reverse`
- `qimen_options.palaceShift` / `qimen_options.palace_shift`: 奇门宫位内容位移
- `taiyi_options.accNum` / `taiyi_options.acc_num`: 太乙积数偏移
- `taiyi_options.rotation`: 太乙布盘方向，可用 `reverse` / `逆布`
- `use_true_solar_time`: 是否启用 FateBridge 本地真太阳时修正；使用解析后的经度进行离线校正
- `selected_sections`: 可选导出 section；支持主分段，也兼容旧式方向宫名如 `正南离宫`
- `liureng_yue`: 六壬月将 override
- `liureng_isDiurnal`: 六壬昼夜盘 override

**返回重点**:

- `analysis_context.input_datetime / corrected_datetime`: 原始输入时刻与真太阳时修正后的实际起盘时刻
- `analysis_context.time_algorithm / total_correction_minutes`: 当前时间算法与修正分钟数
- `qimen.palaces[].name / trigram`: 当前槽位宫名与宫卦
- `qimen.palaces[].content_palace / content_trigram`: 当前槽位中实际承载内容的来源宫位
- `qimen.palaces[].door_hexagram`: 按当前槽位宫卦与八门重算的门卦
- `qimen.zhifu / zhishi`: 变体盘下重新定位后的值符 / 值使，并直接附带 `content_palace / content_trigram`
- `taiyi.core_board.main_calculation`: 带本地积数偏移的主算描述
- `taiyi.big_pattern / small_pattern`: 本地太乙大格 / 小局
- `liureng.month_general`: 六壬月将
- `liureng.meta.is_diurnal`: 六壬昼夜标记
- `subresults`: 三式子结果原文聚合
- `snapshot_text`: 在 `[八宫详解]` 中直接显示 `内容来源：...`
- `snapshot_export.section_titles_detected`: 本次三式快照中实际可导出的 section 列表
- `snapshot_export.selected_sections`: 实际应用后的导出 section；旧式方向宫名会归一到 `离九宫` 这类本地标题
- `snapshot_export.export_text`: 按 `selected_sections` 过滤后的导出文本；未传时默认保留完整三式快照

##### 3.1.6 独立紫微 / ZiWei

**端点**:

- `POST /api/cn/ziwei/birth`
- `POST /api/cn/ziwei/rules`

**关键参数**:

- `birth` 端点复用标准出生信息输入，并支持 `use_true_solar_time`
- `birth.selected_sections`: 可选导出 section，如 `起盘信息`、`宫位总览`
- `rules.year_stem`: 可选天干过滤，例如 `甲`

**返回重点**:

- `ziwei_birth.ming_gong / shen_gong`: 命宫、身宫信息
- `ziwei_birth.sihua`: 生年四化
- `ziwei_birth.palaces`: 十二宫位、大限与主辅星分布
- `snapshot_text`: 按 `[起盘信息] / [宫位总览]` 输出离线紫微快照
- `snapshot_export.section_titles_detected`: 本次离线快照中实际可导出的 section 列表
- `snapshot_export.selected_sections`: 实际应用后的 section 选择结果
- `snapshot_export.export_text`: 按 `selected_sections` 过滤后的导出文本；未传时默认保留完整紫微快照
- `rules` 端点继续返回宫位顺序、命身宫法与四化规则目录，不附加快照导出

##### 3.1.7 独立奇门 / QiMen

**端点**: `POST /api/cn/qimen`

**关键参数**:

- `analysis_year` / `analysis_month` / `analysis_day` / `analysis_hour` / `analysis_minute`: 起盘时刻
- `analysis_timezone`: 时区；支持 IANA 名称或 UTC offset
- `analysis_longitude`: 经度；启用真太阳时时用于修正时刻
- `use_true_solar_time`: 是否使用本地真太阳时
- `qimen_options.layout`: 当前支持 `direct` / `fly` / `mirror` / `reverse`
- `qimen_options.palaceShift`: 奇门宫位内容位移
- `selected_sections`: 可选导出 section；支持主分段，也支持单宫标题如 `离九宫`

**返回重点**:

- `qimen.palaces[].content_palace / content_trigram`: 当前槽位承载内容的来源宫位
- `qimen.zhifu / zhishi`: 独立奇门下的值符 / 值使，并直接附带 `content_palace / content_trigram`
- `qimen.layout / options_applied`: 启用变体盘后的布局信息
- `snapshot_text`: 按 `[起盘信息] / [盘型] / [盘面要素] / [奇门演卦] / [八宫详解] / [九宫方盘]` 输出离线文本快照
- `snapshot_export.section_titles_detected`: 本次离线快照中实际可导出的 section 列表
- `snapshot_export.selected_sections`: 实际应用后的 section 选择结果
- `snapshot_export.export_text`: 按 `selected_sections` 过滤后的导出文本；未传时默认保留完整奇门快照与九宫单宫分段

##### 3.1.8 独立六壬 / LiuReng

**端点**:

- `POST /api/cn/liureng/gods`
- `POST /api/cn/liureng/runyear`

**关键参数**:

- `analysis_year` / `analysis_month` / `analysis_day` / `analysis_hour` / `analysis_minute`: 起课时刻
- `analysis_timezone`: 时区；支持 IANA 名称或 UTC offset
- `analysis_longitude`: 经度；启用真太阳时时用于修正时刻
- `use_true_solar_time`: 是否使用本地真太阳时
- `selected_sections`: 可选导出 section，如 `起盘信息`、`三传`、`概览`
- `runyear` 端点额外需要出生信息，并会输出 `行年`

**返回重点**:

- `liureng.month_general`: 月将
- `liureng.four_lessons`: 四课
- `liureng.three_transmissions`: 三传与取传法
- `runyear.age / ganzhi`: 行年端点附加的年龄与行年干支
- `snapshot_text`: 按 `[起盘信息] / [十二盘式] / [四课] / [三传] / [行年] / [概览] ...` 输出离线快照
- `snapshot_export.section_titles_detected`: 本次离线快照中实际可导出的 section 列表
- `snapshot_export.selected_sections`: 实际应用后的 section 选择结果
- `snapshot_export.export_text`: 按 `selected_sections` 过滤后的导出文本；未传时默认保留完整六壬快照

##### 3.1.9 独立太乙 / TaiYi

**端点**: `POST /api/cn/taiyi`

**关键参数**:

- `analysis_year` / `analysis_month` / `analysis_day` / `analysis_hour` / `analysis_minute`: 起盘时刻
- `analysis_timezone`: 时区；支持 IANA 名称或 UTC offset
- `analysis_longitude`: 经度；启用真太阳时时用于修正时刻
- `gender`: 性别
- `use_true_solar_time`: 是否使用本地真太阳时
- `selected_sections`: 可选导出 section，如 `起盘信息`、`太乙盘`、`十六宫标记`

**返回重点**:

- `taiyi.core_board.main_calculation`: 主算结果
- `taiyi.taiyi_palace / wenchang_palace`: 太乙与文昌落宫
- `taiyi.palace_marks`: 十六宫标记
- `snapshot_text`: 按 `[起盘信息] / [太乙盘] / [十六宫标记]` 输出离线快照
- `snapshot_export.section_titles_detected`: 本次离线快照中实际可导出的 section 列表
- `snapshot_export.selected_sections`: 实际应用后的 section 选择结果
- `snapshot_export.export_text`: 按 `selected_sections` 过滤后的导出文本；未传时默认保留完整太乙快照

##### 3.1.10 独立金口诀 / JinKou

**端点**: `POST /api/cn/jinkou`

**关键参数**:

- `analysis_year` / `analysis_month` / `analysis_day` / `analysis_hour` / `analysis_minute`: 起课时刻
- `analysis_timezone`: 时区；支持 IANA 名称或 UTC offset
- `analysis_longitude`: 经度；启用真太阳时时用于修正时刻
- `gender`: 性别
- `di_fen`: 可选地分；省略时默认取当前时支
- `use_true_solar_time`: 是否使用本地真太阳时
- `selected_sections`: 可选导出 section，如 `起盘信息`、`金口诀速览`、`金口诀四位`、`四位神煞`

**返回重点**:

- `jinkou.overview`: 地分、月将、贵神、课体、取传法、用爻与空亡概览
- `jinkou.rows`: 人元 / 贵神 / 将神 / 地分四位明细，含神将、五行与旺衰
- `jinkou.shensha`: 四位神煞与课体辅助列表
- `liureng`: 当前金口诀依附的离线六壬语境，用于保持课体与取传判断一致
- `snapshot_text`: 按 `[起盘信息] / [金口诀速览] / [金口诀四位] / [四位神煞]` 输出离线快照
- `snapshot_export.section_titles_detected`: 本次离线快照中实际可导出的 section 列表
- `snapshot_export.selected_sections`: 实际应用后的 section 选择结果
- `snapshot_export.export_text`: 按 `selected_sections` 过滤后的导出文本；未传时默认保留完整金口诀快照

---

#### 4. 卦义检索

**端点**: `POST /api/divination/gua`

离线检索八卦或六十四卦义理说明，支持按卦名或二进制卦码查询。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | **是** | 卦名、八卦码或六十四卦码 |
| `lookup_mode` | string | 否 | `auto`、`hexagram`、`trigram`，默认 `auto` |

**示例**:

- `111111` -> `乾为天`
- `111` -> `乾`
- `火天大有` -> 六十四卦名称查询

**返回重点**:

- `result.lookup_type`: `hexagram` 或 `trigram`
- `result.name`: 命中的卦名
- `result.theme`: 卦义主旨
- `result.guidance`: 问事/判断摘要
- `result.judgement`: 断辞主句
- `result.image`: 卦象提示
- `result.favorable`: 当前较宜采取的方向
- `result.caution`: 当前需防的偏差
- `result.summary`: 汇总描述

---

#### 4.1 全年节气盘 Helper

**端点**: `POST /api/cn/jieqi/year`

返回指定年份的 24 节气节点，并可按节气名筛选重点节点。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `year` | integer | **是** | 目标年份 |
| `zone` | string | 否 | 时区，默认 `Asia/Shanghai` |
| `lat` | string | 否 | 纬度文本提示 |
| `lon` | string | 否 | 经度文本提示 |
| `gpsLat` | number | 否 | GPS 纬度 |
| `gpsLon` | number | 否 | GPS 经度 |
| `jieqis` | string[] | 否 | 仅返回指定节气，例如 `["春分","冬至"]` |

**返回重点**:

- `query_context`: 请求年份、时区与筛选条件
- `jieqi_year`: 全年 24 节气表
- `selected_jieqi`: 按请求筛出的重点节气
- `summary`: 年度节气摘要

---

#### 4.2 农历换算 Helper

**端点**: `POST /api/cn/nongli/time`

把公历时刻转换成农历、节气与四柱上下文，便于其他派生技法复用。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `date` | string | **是** | 公历日期，如 `2028-04-01` |
| `time` | string | **是** | 时间，如 `09:00:00` |
| `zone` | string | 否 | 时区，默认 `Asia/Shanghai` |
| `lat` | string | 否 | 纬度文本提示 |
| `lon` | string | 否 | 经度文本提示 |
| `gpsLat` | number | 否 | GPS 纬度 |
| `gpsLon` | number | 否 | GPS 经度 |
| `after23NewDay` | boolean | 否 | 是否把 23 点后视为次日 |
| `timeAlg` | integer | 否 | 时间算法透传位 |
| `ad` | integer | 否 | 公元标记透传位 |

**返回重点**:

- `input_context`: 输入参数与换算配置
- `calendar_context`: 节气上下文、月令边界与农历信息
- `lunar_calendar`: 农历日期、节气、节差与梅花时卦辅助字段
- `four_pillars`: 对应时刻的四柱
- `summary`: 换算摘要

---

#### 4.3 梅易卦义 Helper

**端点**: `POST /api/cn/gua/meiyi`

按卦名或卦码批量返回偏梅花易数语境的卦义摘要。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string[] | **是** | 卦名或二进制卦码列表 |

**返回重点**:

- `queries`: 原始查询列表
- `results.<query>.name`: 命中的卦名
- `results.<query>.lookup_type`: `trigram` 或 `hexagram`
- `results.<query>.desc`: 梅易取向摘要
- `summary`: 批量查询摘要

---

#### 4.3.1 导出协议 Helper

**端点**:

- `POST /api/export/registry`
- `POST /api/export/parse`

这组端点提供 FateBridge 自有的 AI 导出 contract，可用于前端快照导出、分段筛选与文本安全过滤。

`/api/export/registry` 请求体：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `technique` | string | 否 | 可选技法 key，例如 `qimen` |

`/api/export/parse` 请求体：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `technique` | string | **是** | 技法 key |
| `content` | string | **是** | 快照文本正文 |
| `selected_sections` | string[] | 否 | 目标导出分段列表 |
| `planetInfo` | object | 否 | 行星宫位/守护星输出开关 |
| `astroMeaning` | object | 否 | 注释输出开关 |

**返回重点**:

- `settings_key / settings_version`: 导出协议元信息
- `selected_technique`: 当前技法的分段预设与默认开关
- `section_titles_detected`: 从正文检测出的分段标题
- `selected_sections`: 实际参与导出的分段
- `sections`: 每个分段是否纳入导出的判定
- `export_text`: 过滤禁出栏目后的安全导出正文

---

#### 4.3.2 悬浮知识 Helper

**端点**:

- `POST /api/knowledge/registry`
- `POST /api/knowledge/read`

这组端点提供 astrology / 六壬 / 奇门的本地离线知识目录与单条读取能力，适合悬浮知识、说明抽屉与分段解释场景。

`/api/knowledge/registry` 请求体：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `domain` | string | 否 | 可选域过滤：`astro`、`liureng`、`qimen` |

`/api/knowledge/read` 请求体：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `domain` | string | **是** | 知识域 |
| `category` | string | **是** | 域内分类 |
| `key` | string | 否 | 主查询 key |
| `aspect_degree` | integer | 否 | astrology 相位角查询 |
| `object_a` | string | 否 | astrology 相位对象 A |
| `object_b` | string | 否 | astrology 相位对象 B |
| `jiang_name` | string | 否 | 六壬将神名 |
| `tian_branch` | string | 否 | 六壬天盘地支 |
| `di_branch` | string | 否 | 六壬地盘地支 |

**返回重点**:

- `domains`: 可用知识域与分类目录
- `title`: 命中的知识条目标题
- `tips / lines / blocks`: 原始知识内容
- `rendered_text`: 适合直接展示的文本版本
- `provenance`: 数据来源与 bundle 版本

---

#### 4.3.3 关系盘 / 合盘

**端点**: `POST /api/astro/relative`

离线近似关系盘接口，已支持旧版兼容的 `relative_mode`、`hsys`、`zodiacal` 输入 contract，并保留旧 `relationship_mode` 兼容字段。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `inner` | object | **是** | 星盘 A，结构同 `AstroChartRequest` |
| `outer` | object | **是** | 星盘 B，结构同 `AstroChartRequest` |
| `relative_mode` | string/integer | 否 | 现代盘型字段，例如 `0`、`Comp`、`Composite`、`Synastry`、`TimeSpace`、`Marks`；未传时默认 `0`。当前 `relative_mode=Synastry/synastry` 会按影响盘语义收敛为 `influence` |
| `relationship_mode` | string/integer | 否 | 旧兼容别名；未传 `relative_mode` 时会回填为 mode 输入；两者都不传时默认 `0`。当前 `relationship_mode=synastry` 会保留 FateBridge 旧版“比较盘”兼容语义 |
| `hsys` | integer | 否 | 旧版兼容宫制标识，默认 `0`；当前离线支持 `0=整宫制`、`1=Alcabitus`、`2=Regiomontanus`、`3=Placidus`、`4=Koch`、`5=Vehlow Equal`、`6=Polich Page`、`7=Sripati`、`8=天顶为10宫中点等宫制`，其余值会返回错误，避免静默误算 |
| `zodiacal` | integer | 否 | 旧版兼容黄道标识，默认 `0`；当前离线仅支持 `0=回归黄道`、`1=恒星黄道(Lahiri-like)`，其余值会返回错误，避免静默误算 |

**返回重点**:

- `relationship_profile.relative_mode_normalized`: 归一化盘型，当前会收敛为 `compare / composite / influence / timespace / marks`
- `relationship_profile.relative_mode_source`: 本次 mode 解析主要依据的输入来源，`default / relative_mode / relationship_mode`
- `relationship_profile.relative_mode_resolution`: 本次 mode 归一化路径，例如 `numeric`、`exact_alias`、`legacy_relationship_mode_synastry`
- `relationship_profile.relative_mode_label_zh`: 中文盘型标签
- `relationship_profile.relative_mode_note`: 当命中旧兼容路径时，会返回额外说明，提醒调用方改用现代字段
- `relationship_profile.house_system` / `relationship_profile.house_system_label_zh`: 当前关系盘实际采用的宫制标识与中文标签
- `relationship_profile.zodiac_mode` / `relationship_profile.zodiac_label_zh`: 当前关系盘实际采用的黄道模式
- `relationship_profile.primary_layer`: 当前主输出层；`compare` 为 `directional_synastry`，`composite` 为 `composite_chart`，`influence` 为 `influence_chart_pair`，`timespace` 为 `timespace_chart`，`marks` 为 `marks_chart`
- `inner_chart.chart_profile.zodiac` / `chart.chart_profile.zodiac`: 当前盘层实际采用的黄道类型；`zodiacal=1` 时会真实切到 sidereal 近似计算，而不是仅保留 metadata
- `in_to_out_aspects` / `out_to_in_aspects`: 方向化相位层
- `chart`: `compare` 模式下当前留空；`composite` 返回合成盘层，`timespace` 返回时空中点盘层，`marks` 返回马克斯盘近似层；`influence` 仍保留合成盘作为辅助层
- `in_to_out_midpoint` / `out_to_in_midpoint`: 当前返回离线近似的中点相位命中层
- `in_to_out_antiscia` / `out_to_in_antiscia`: 当前返回离线近似的映点命中层；`in_to_out_contra_antiscia` / `out_to_in_contra_antiscia` 为反映点命中层
- `inner` / `outer`: 当前返回离线近似的影响图盘包装层，`inner.chart` / `outer.chart` 为各自视角的投影盘

---

#### 4.4 西占时运分析

**端点**: `POST /api/astro/timing`

基于精确星历返回西占时运组合输出，聚合太阳返照、月返、指定年盘、次限推运、太阳弧、轴点主限近似、离线半弧主限近似、小限、法达、十年星限，以及基于 Fortune / Spirit lots 的黄道释放。

**请求体**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | integer | **是** | 出生年份 |
| `birth_month` | integer | **是** | 出生月份 |
| `birth_day` | integer | **是** | 出生日期 |
| `birth_hour` | integer | **是** | 出生时辰 |
| `birth_minute` | integer | 否 | 出生分钟，默认：0 |
| `birth_timezone` | string | **是** | 出生时区（IANA 名称或 UTC 偏移） |
| `birth_longitude` | number | **是** | 出生地经度 |
| `birth_latitude` | number | **是** | 出生地纬度 |
| `birth_place` | string | 否 | 出生地标签 |
| `analysis_year` | integer | 否 | 分析年份 |
| `analysis_month` | integer | 否 | 分析月份 |
| `analysis_day` | integer | 否 | 分析日期 |
| `return_longitude` | number | 否 | 返照盘地点经度，默认沿用出生地 |
| `return_latitude` | number | 否 | 返照盘地点纬度，默认沿用出生地 |
| `return_timezone` | string | 否 | 返照盘地点时区，默认沿用出生时区 |
| `house_system` | string | 否 | 宫制，默认 `P`（Placidus） |
| `zodiac_type` | string | 否 | 黄道类型，默认 `Tropic` |
| `pd_method` | string | 否 | 主限方法标识，默认 `astroapp_alchabitius`；`legacy_reference` / `legacy_equatorial` 使用赤经坐标；`fatebridge_mundane_semiarc` 使用 FateBridge 离线半弧 mundane 坐标 |
| `pd_time_key` | string | 否 | 主限 time key，默认 `Ptolemy`，可传 `Naibod` |
| `pd_type` | integer | 否 | 主限方向模式，`0` 为顺推，`1` 为逆推，默认 `0` |
| `pd_aspects` | integer[] | 否 | 主限事件表纳入的相位度数，默认 `[0,60,90,120,180]` |
| `show_pd_bounds` | boolean | 否 | 是否返回主限法盘的埃及界限 overlay，默认 `true` |

**返回重点**:

- `natal_reference`: 本命日月、上升、天顶、盘型（昼夜盘）与 Fortune / Spirit lots
- `returns.solar_return`: 太阳返照时刻与关键点位
- `returns.lunar_return`: 月返时刻与关键点位
- `directions.given_year`: 指定年盘关键点位、命盘相位命中，以及从生日起算的 12 段月推限时间线
- `directions.secondary_progression`: 次限推运日期、关键点位与命盘相位命中
- `directions.solar_arc`: 太阳弧度数、定向点位与命盘相位命中
- `directions.primary_directions`: 基于 static key 的轴点主限近似，返回顺推 / 逆推模式、主限坐标系（Arc / 赤经 / SemiArc）、近似类型、当前弧度、主限事件表、最近事件窗口，以及可选的坐标诊断、本命坐标环；其中 `timeline` 事件项带事件弧度下的 `coordinate_context`、`arc_applied_degrees`、`relative_years_from_current`、`relative_arc_from_current` 与 `timing_phase`，`current_window` / `past_window` / `future_window` / `exact_window` 则带当前分析弧度下的 `coordinate_context`
- `directions.primary_direction_chart`: 当前分析时刻对应的轴点主限法盘视图，返回顺推 / 逆推模式下的主限坐标系、近似类型、完整 directed points / lots、换座提示、当前事件命中、坐标诊断、本命 / directed 坐标环、带 `coordinate_context` 的 `hits` / `coordinate_hits` / `exact_hits`，以及可选的 `bounds_overlay`
- `time_lords.annual_profection`: 年小限主宫、激活星座与年主星
- `time_lords.firdaria`: 当前法达主限 / 子限与时间范围
- `time_lords.decennials`: 当前十年星限的 L1 / L2 / L3 层级与时间轴片段
- `time_lords.zodiacal_releasing.spirit`: 基于 Spirit 的黄道释放，返回当前 L1 / L2 / L3、时间片段，以及 `loosing_of_bond` 标记
- `time_lords.zodiacal_releasing.fortune`: 基于 Fortune 的黄道释放，返回当前 L1 / L2 / L3、时间片段，以及 `loosing_of_bond` 标记

---

#### 5. 流日专项分析

**端点**: `POST /api/timing/liuri`

在出生盘基础上分析指定日期的流日影响。

**返回重点**:

- `calendar_context`: 出生时刻节气/农历上下文
- `analysis_calendar.analysis_date_context`: 分析日期节气上下文
- `liuri_info`: 流日干支、五行与星期
- `summary`: 流日摘要

---

#### 6. 流月专项分析

**端点**: `POST /api/timing/liuyue`

在出生盘基础上分析指定日期所在节令月的影响，不按公历月份近似。

**返回重点**:

- `calendar_context`: 出生时刻节气/农历上下文
- `analysis_calendar.analysis_date_context`: 分析日期节气上下文
- `target_year_jieqi`: 目标年份 24 节气表
- `liuyue_info`: 流月干支、纳音与节气窗口
- `liunian_info`: 同年流年信息
- `combination_effects`: 流月与流年组合关系
- `summary`: 流月综合摘要

---

#### 7. 节气节点时间轴

**端点**: `POST /api/timing/jieqi`

输出目标年份 24 节气节点的流月/流日切换与简要影响。

**返回重点**:

- `target_year_jieqi`: 全年 24 节气表
- `jieqi_timeline`: 每个节气节点对应的流月、流日与摘要

---

## FastMCP API

FastMCP API 通过 Model Context Protocol 提供相同功能，可用于 AI 助手集成。

### 可用工具

#### 1. `analyze_destiny`

个人命理分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 (1-12) |
| `birth_day` | int | **是** | 出生日期 (1-31) |
| `birth_hour` | int | **是** | 出生时辰 (0-23) |
| `name` | str | 否 | 姓名，默认："未提供" |
| `gender` | str | 否 | 性别，默认："未知" |
| `birth_place` | str | 否 | 出生地，默认："未提供" |
| `birth_minute` | int | 否 | 出生分钟，默认：0 |
| `birth_timezone` | str | 否 | 出生时区（IANA 名称或 UTC 偏移） |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含四柱主分析以及 `calendar_context` 历法辅助信息

**示例**:

```python
from fastmcp_server import analyze_destiny

result = analyze_destiny(
    1990,
    5,
    15,
    10,
    "张三",
    "男",
    "北京",
    birth_minute=30,
    birth_timezone="Asia/Shanghai",
    use_true_solar_time=True,
)
print(result)  # JSON 字符串
```

---

#### 2. `two_person_compatibility`

双人配合度分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `person1_name` | str | **是** | 第一人姓名 |
| `person1_birth_year` | int | **是** | 第一人出生年份 |
| `person1_birth_month` | int | **是** | 第一人出生月份 |
| `person1_birth_day` | int | **是** | 第一人出生日期 |
| `person1_birth_hour` | int | **是** | 第一人出生时辰 |
| `person2_name` | str | **是** | 第二人姓名 |
| `person2_birth_year` | int | **是** | 第二人出生年份 |
| `person2_birth_month` | int | **是** | 第二人出生月份 |
| `person2_birth_day` | int | **是** | 第二人出生日期 |
| `person2_birth_hour` | int | **是** | 第二人出生时辰 |
| `person1_gender` | str | 否 | 第一人性别 |
| `person1_birth_place` | str | 否 | 第一人出生地 |
| `person2_gender` | str | 否 | 第二人性别 |
| `person2_birth_place` | str | 否 | 第二人出生地 |
| `relationship_type` | str | 否 | 关系类型 |
| `person1_birth_minute` | int | 否 | 第一人出生分钟 |
| `person2_birth_minute` | int | 否 | 第二人出生分钟 |
| `person1_birth_timezone` | str | 否 | 第一人出生时区 |
| `person2_birth_timezone` | str | 否 | 第二人出生时区 |
| `person1_birth_longitude` | float | 否 | 第一人出生地经度 |
| `person2_birth_longitude` | float | 否 | 第二人出生地经度 |
| `person1_use_true_solar_time` | bool | 否 | 第一人是否启用真太阳时修正 |
| `person2_use_true_solar_time` | bool | 否 | 第二人是否启用真太阳时修正 |

**关系类型**:

- `marriage` - 婚姻关系
- `friendship` - 友谊关系
- `business` - 商业合作
- `family` - 家庭关系
- `general` - 一般关系（默认）

**返回**: JSON 格式字符串，包含配合度分析结果

---

#### 西占时运 `western_timing_analysis`

西占推运 / 返照 / 时运系统工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `birth_minute` | int | 否 | 出生分钟，默认：0 |
| `birth_timezone` | str | **是** | 出生时区 |
| `birth_longitude` | float | **是** | 出生地经度 |
| `birth_latitude` | float | **是** | 出生地纬度 |
| `birth_place` | str | 否 | 出生地标签 |
| `analysis_year` | int | 否 | 分析年份 |
| `analysis_month` | int | 否 | 分析月份 |
| `analysis_day` | int | 否 | 分析日期 |
| `return_longitude` | float | 否 | 返照盘地点经度 |
| `return_latitude` | float | 否 | 返照盘地点纬度 |
| `return_timezone` | str | 否 | 返照盘地点时区 |
| `house_system` | str | 否 | 宫制，默认 `P` |
| `zodiac_type` | str | 否 | 黄道类型，默认 `Tropic` |

**返回**: JSON 格式字符串，包含 `natal_reference.lots`、`returns`、`directions`、`time_lords.zodiacal_releasing` 等西占时运数据

---

#### 3. `timing_analysis`

综合时运分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `name` | str | 否 | 姓名 |
| `gender` | str | 否 | 性别 |
| `birth_place` | str | 否 | 出生地 |
| `analysis_year` | int | 否 | 分析年份（默认当前年） |
| `analysis_month` | int | 否 | 分析月份（默认当前月） |
| `analysis_age` | int | 否 | 分析年龄（用于大运分析） |
| `birth_minute` | int | 否 | 出生分钟 |
| `birth_timezone` | str | 否 | 出生时区 |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含大运、流年、流月分析，以及：

- `calendar_context`: 出生时刻的节气/农历上下文
- `analysis_calendar.analysis_date_context`: 目标分析日期的节气上下文
- `analysis_calendar.analysis_year_jieqi`: 目标年份 24 节气表
- `analysis_calendar.liuyue_timeline`: 目标年份 12 个节令月时间轴，每项包含起止节气、月柱和简要运势总结
- `analysis_calendar.jieqi_timeline`: 目标年份 24 个节气节点时间轴，每项包含节气切换点对应的流月、流日和简要影响
- `liuri_analysis`: 分析日期对应的流日信息

---

#### 4. `dayun_analysis`

大运（10年周期）分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `gender` | str | **是** | 性别（用于大运推算） |
| `analysis_age` | int | **是** | 分析年龄 |
| `name` | str | 否 | 姓名 |
| `birth_place` | str | 否 | 出生地 |
| `birth_minute` | int | 否 | 出生分钟 |
| `birth_timezone` | str | 否 | 出生时区 |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含指定年龄的大运分析与 `calendar_context`

---

#### 5. `liunian_analysis`

流年（年度运势）分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `target_year` | int | **是** | 目标分析年份 |
| `name` | str | 否 | 姓名 |
| `gender` | str | 否 | 性别 |
| `birth_place` | str | 否 | 出生地 |
| `birth_minute` | int | 否 | 出生分钟 |
| `birth_timezone` | str | 否 | 出生时区 |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含指定流年分析、`calendar_context` 与 `target_year_jieqi`

---

#### 6. `liuri_analysis`

流日（单日时运）分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `analysis_year` | int | 否 | 分析年份 |
| `analysis_month` | int | 否 | 分析月份 |
| `analysis_day` | int | 否 | 分析日期 |
| `birth_minute` | int | 否 | 出生分钟 |
| `birth_timezone` | str | 否 | 出生时区 |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含流日分析、`calendar_context` 与 `analysis_calendar`

---

#### 7. `liuyue_analysis`

流月（节令月）分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `analysis_year` | int | 否 | 分析年份 |
| `analysis_month` | int | 否 | 分析月份 |
| `analysis_day` | int | 否 | 分析日期 |
| `birth_minute` | int | 否 | 出生分钟 |
| `birth_timezone` | str | 否 | 出生时区 |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含流月分析、`liunian_info`、`calendar_context` 与 `analysis_calendar`

---

#### 7.1 `export_registry`

FateBridge 导出协议注册表工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `technique` | str | 否 | 技法 key，如 `qimen` |

**返回**: JSON 格式字符串，包含导出协议版本、全部技法 registry 与可选技法详情

---

#### 7.2 `export_parse`

FateBridge 快照导出解析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `technique` | str | **是** | 技法 key |
| `content` | str | **是** | 快照文本 |
| `selected_sections` | list[str] | 否 | 目标导出分段 |
| `planet_info` | dict | 否 | 行星信息导出配置 |
| `astro_meaning` | dict | 否 | 注释导出配置 |

**返回**: JSON 格式字符串，包含检测分段、过滤结果与最终 `export_text`

---

#### 7.3 `knowledge_registry`

本地悬浮知识目录工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `domain` | str | 否 | 可选域过滤 |

**返回**: JSON 格式字符串，包含 astrology / 六壬 / 奇门的知识分类目录

---

#### 7.4 `knowledge_read`

本地悬浮知识读取工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `domain` | str | **是** | 知识域 |
| `category` | str | **是** | 域内分类 |
| `key` | str | 否 | 主查询 key |
| `aspect_degree` | int | 否 | astrology 相位角 |
| `object_a` | str | 否 | astrology 对象 A |
| `object_b` | str | 否 | astrology 对象 B |
| `jiang_name` | str | 否 | 六壬将神名 |
| `tian_branch` | str | 否 | 六壬天盘地支 |
| `di_branch` | str | 否 | 六壬地盘地支 |

**返回**: JSON 格式字符串，包含命中的知识正文与 `rendered_text`

---

#### 8. `jieqi_year`

全年节气盘辅助工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `year` | int | **是** | 目标年份 |
| `zone` | str | 否 | 时区，默认 `Asia/Shanghai` |
| `lat` | str | 否 | 纬度文本提示 |
| `lon` | str | 否 | 经度文本提示 |
| `gps_lat` | float | 否 | GPS 纬度 |
| `gps_lon` | float | 否 | GPS 经度 |
| `jieqis` | list[str] | 否 | 只筛选指定节气 |

**返回**: JSON 格式字符串，包含全年 24 节气与重点筛选结果

---

#### 9. `nongli_time`

农历换算辅助工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `date` | str | **是** | 公历日期 |
| `time` | str | **是** | 时间 |
| `zone` | str | 否 | 时区 |
| `lon` | str | 否 | 经度文本提示 |
| `lat` | str | 否 | 纬度文本提示 |
| `gps_lat` | float | 否 | GPS 纬度 |
| `gps_lon` | float | 否 | GPS 经度 |
| `after23_new_day` | bool | 否 | 是否 23 点后视为次日 |
| `time_alg` | int | 否 | 时间算法透传位 |
| `ad` | int | 否 | 公元标记透传位 |

**返回**: JSON 格式字符串，包含农历、节气与四柱上下文

---

#### 10. `jieqi_timeline_analysis`

节气节点时间轴分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `birth_year` | int | **是** | 出生年份 |
| `birth_month` | int | **是** | 出生月份 |
| `birth_day` | int | **是** | 出生日期 |
| `birth_hour` | int | **是** | 出生时辰 |
| `target_year` | int | 否 | 目标年份 |
| `birth_minute` | int | 否 | 出生分钟 |
| `birth_timezone` | str | 否 | 出生时区 |
| `birth_longitude` | float | 否 | 出生地经度 |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

**返回**: JSON 格式字符串，包含全年 24 节气节点时间轴

---

#### 11. `gua_meiyi`

梅易卦义辅助工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | list[str] | **是** | 卦名或卦码列表 |

**返回**: JSON 格式字符串，包含批量卦义说明与摘要

---

#### 12. `meihua_analysis`

梅花时卦分析工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `analysis_year` | int | **是** | 起卦年份 |
| `analysis_month` | int | **是** | 起卦月份 |
| `analysis_day` | int | **是** | 起卦日期 |
| `analysis_hour` | int | **是** | 起卦时辰 |
| `analysis_minute` | int | 否 | 起卦分钟，默认：0 |
| `analysis_timezone` | str | 否 | 起卦时区 |
| `question` | str | 否 | 占问主题 |

**返回**: JSON 格式字符串，包含本卦、变卦、互卦、综卦、体用关系、四层卦义断辞、行动/风险提示与历法上下文

---

#### 13. `gua_lookup`

卦义检索工具。

**参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | str | **是** | 卦名或二进制卦码 |
| `lookup_mode` | str | 否 | 查询模式：`auto`、`hexagram`、`trigram` |

**返回**: JSON 格式字符串，包含命中卦象的义理主旨、断辞、卦象、宜忌提示与结构信息

---

## 数据类型

### 天干和地支

**十天干**:
- 阳干: 甲、丙、戊、庚、壬
- 阴干: 乙、丁、己、辛、癸

**十二地支**:
- 子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥

### 五行

- **木**: 生长、创造
- **火**: 热烈、光明
- **土**: 生成、承载
- **金**: 收敛、精锐
- **水**: 流动、智慧

### 十神

表示日干与其他干支的关系：

| 十神 | 说明 |
|------|------|
| 正官 | 克制日干的阳性天干 |
| 偏官 | 克制日干的阴性天干 |
| 正财 | 日干克制的阳性天干 |
| 偏财 | 日干克制的阴性天干 |
| 正印 | 生助日干的阳性天干 |
| 偏印 | 生助日干的阴性天干 |
| 食神 | 日干生助的阳性天干 |
| 伤官 | 日干生助的阴性天干 |
| 比肩 | 与日干同性的天干 |
| 劫财 | 与日干异性的天干 |

---

## 错误处理

### 错误响应格式

```json
{
  "detail": "Error message describing the issue"
}
```

### 常见错误

| 状态码 | 错误类型 | 原因 | 解决方案 |
|--------|----------|------|---------|
| 400 | Bad Request | 输入参数无效 | 检查日期有效性、范围检查 |
| 400 | ValueError | 无效的日期组合 | 确保月份与日期匹配（如2月无30日） |
| 500 | Internal Server Error | 服务器内部错误 | 检查服务器日志 |

### 验证规则

- `birth_year`: 1900-2100
- `birth_month`: 1-12
- `birth_day`: 1-31（需符合月份天数）
- `birth_hour`: 0-23
- `birth_minute`: 0-59
- `birth_longitude`: -180 到 180

---

## 代码示例

### Python - REST API

```python
import requests
import json

# 创建请求
url = "http://localhost:8000/api/calculate"
payload = {
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": True,
    "birth_place": "北京"
}

# 发送请求
response = requests.post(url, json=payload)

# 处理响应
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, ensure_ascii=False, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### Python - FastMCP API

```python
from fastmcp_server import analyze_destiny
import json

# 调用工具
result_json = analyze_destiny(
    1990,
    5,
    15,
    10,
    "张三",
    "男",
    "北京",
    birth_minute=30,
    birth_timezone="Asia/Shanghai",
    use_true_solar_time=True,
)
result = json.loads(result_json)

# 处理结果
print(f"日主: {result['day_master']['stem']}")
print(f"五行: {result['day_master']['element']}")
```

### JavaScript/TypeScript

```typescript
// REST API 调用
async function analyzeDestiny(birthInfo: {
  name?: string;
  gender?: string;
  birth_year: number;
  birth_month: number;
  birth_day: number;
  birth_hour: number;
  birth_minute?: number;
  birth_place?: string;
  birth_timezone?: string;
  birth_longitude?: number;
  use_true_solar_time?: boolean;
}) {
  const response = await fetch('http://localhost:8000/api/calculate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(birthInfo),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

// 使用示例
const analysis = await analyzeDestiny({
  name: "张三",
  birth_year: 1990,
  birth_month: 5,
  birth_day: 15,
  birth_hour: 10,
  birth_minute: 30,
  birth_timezone: "Asia/Shanghai",
  use_true_solar_time: true,
});

console.log(analysis);
```

### cURL

```bash
# 个人命理分析
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": true,
    "birth_place": "北京"
  }' | jq .

# 健康检查
curl http://localhost:8000/health | jq .
```

---

## 性能考虑

- 单个分析请求通常在 100ms 以内完成
- 系统可处理并发请求，无特殊限制
- 推荐生产环境使用反向代理（如 Nginx）

## 限制和注意事项

- 本 API 仅提供计算数据，不包含建议或预测
- 时辰计算基于 24 小时制，需要准确的出生时间
- 真太阳时修正依赖 `birth_timezone` + `birth_longitude`，或命中内置 `birth_place` 地点库
- `birth_place` 现在支持更广泛的离线地址匹配：可输入中文、英文或拼音，优先解析到更具体的城市，命不中城市时回退到可识别的省级近似值
- 离线解析不是联网街道级地理编码，最高精度仍建议直接传 `birth_longitude`
- 月柱与起运采用本地离线节气算法：以立春分年、以十二节判月，并按节令边界换算起运岁数
- 节气时刻基于 fixed-qì 近似算法，适合本地推演；若需要更高天文精度，建议接入专门历表
- 结果仅供参考，基于传统八字理论
- CORS 配置通过环境变量控制（生产环境务必配置）

---

## 更新日志

### v0.1.0 (当前版本)

- ✅ REST API 端点完成
- ✅ FastMCP 工具集成
- ✅ 错误处理改进
- ✅ 环境配置支持
