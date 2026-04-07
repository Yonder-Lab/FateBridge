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
- `meihua.body_use_relation`: 体用五行关系

---

#### 4. 流日专项分析

**端点**: `POST /api/timing/liuri`

在出生盘基础上分析指定日期的流日影响。

**返回重点**:

- `calendar_context`: 出生时刻节气/农历上下文
- `analysis_calendar.analysis_date_context`: 分析日期节气上下文
- `liuri_info`: 流日干支、五行与星期
- `summary`: 流日摘要

---

#### 5. 节气节点时间轴

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

#### 7. `jieqi_timeline_analysis`

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

#### 8. `meihua_analysis`

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

**返回**: JSON 格式字符串，包含本卦、变卦、互卦、综卦、体用关系与历法上下文

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
