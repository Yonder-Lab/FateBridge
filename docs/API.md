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
| `birth_place` | string | 否 | 出生地点 | 默认："未提供" |

**响应 (200 OK)**:

```json
{
  "person_info": {
    "name": "张三",
    "birth_datetime": "1990年05月15日 10时",
    "gender": "男",
    "birth_place": "北京"
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
  }
}
```

**响应字段说明**:

- **person_info**: 个人基本信息
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

**返回**: JSON 格式字符串

**示例**:

```python
from fastmcp_server import analyze_destiny

result = analyze_destiny(1990, 5, 15, 10, "张三", "男", "北京")
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

**返回**: JSON 格式字符串，包含大运、流年、流月分析

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
result_json = analyze_destiny(1990, 5, 15, 10, "张三", "男", "北京")
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
  birth_place?: string;
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
- 结果仅供参考，基于传统八字理论
- CORS 配置通过环境变量控制（生产环境务必配置）

---

## 更新日志

### v0.1.0 (当前版本)

- ✅ REST API 端点完成
- ✅ FastMCP 工具集成
- ✅ 错误处理改进
- ✅ 环境配置支持
