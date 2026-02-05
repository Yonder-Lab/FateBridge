# FateBridge - 命运之桥

基于 FastMCP 框架的中国传统命理工具，连接古典智慧与现代技术，为您搭建通向命运洞察的桥梁。

## 主要功能

### 核心计算功能
- 四柱命理计算（年、月、日、时柱）
- 日主分析和五行分布
- 喜用神分析
- 十神关系分析
- 格局识别

### 高级分析功能
- 个人命理全面分析
- 双人配合分析
- 五行互补性分析
- 关系类型适配（婚姻、友谊、商业等）
- 传统合盘算法

### 技术特点
- 基于 FastMCP 框架的标准化 API
- 精确的中国传统历法计算
- 类型安全的数据验证
- 模块化的代码架构

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 启动 FastMCP 服务器

```bash
python fastmcp_server.py
```

### API 接口

#### 1. 个人命理分析 (analyze_destiny)

```python
# 参数说明
analyze_destiny(
    birth_year: int,           # 出生年份，如 1990
    birth_month: int,          # 出生月份 (1-12)
    birth_day: int,            # 出生日期 (1-31)
    birth_hour: int,           # 出生时辰 (0-23)
    name: str = "未提供",       # 姓名（可选）
    gender: str = "未知",       # 性别（可选）
    birth_place: str = "未提供" # 出生地（可选）
)
```

#### 2. 双人配合分析 (two_person_compatibility)

```python
# 参数说明
two_person_compatibility(
    person1_name: str,         # 第一人姓名
    person1_birth_year: int,   # 第一人出生年份
    person1_birth_month: int,  # 第一人出生月份
    person1_birth_day: int,    # 第一人出生日期
    person1_birth_hour: int,   # 第一人出生时辰
    person2_name: str,         # 第二人姓名
    person2_birth_year: int,   # 第二人出生年份
    person2_birth_month: int,  # 第二人出生月份
    person2_birth_day: int,    # 第二人出生日期
    person2_birth_hour: int,   # 第二人出生时辰
    person1_gender: str = "未知",      # 第一人性别（可选）
    person1_birth_place: str = "未提供", # 第一人出生地（可选）
    person2_gender: str = "未知",      # 第二人性别（可选）
    person2_birth_place: str = "未提供", # 第二人出生地（可选）
    relationship_type: str = "general" # 关系类型
)
```

### 关系类型说明

- `marriage` - 婚姻关系
- `friendship` - 友谊关系  
- `business` - 商业合作
- `family` - 家庭关系
- `general` - 一般关系

### 核心模块直接使用

```python
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.elements import ElementAnalysis
from datetime import datetime

# 计算四柱命理
birth_time = datetime(1990, 5, 15, 10)
pillars = BaZiCalendar.get_four_pillars(birth_time)
print(BaZiCalendar.format_pillars(pillars))

# 五行分析
element_analysis = ElementAnalysis.comprehensive_analysis(pillars)
print("日主强弱:", element_analysis['day_master']['strength'])
```

## 项目结构

```
FateBridge/
├── fatebridge/                          # 核心计算模块
│   ├── core/                      # 基础功能
│   │   ├── calendar.py           # 八字历法计算
│   │   ├── elements.py           # 五行分析
│   │   └── rules.py              # 八字规则
│   ├── analysis/                  # 分析功能
│   │   └── compatibility.py      # 合盘分析
│   └── utils/                     # 工具模块
│       └── data.py               # 数据定义
├── fastmcp_server.py             # FastMCP 服务器
└── README.md                     # 项目文档
```

## 核心算法

### 日柱计算
- 使用1984年3月31日作为甲子日基准点
- 通过日期差值计算干支循环

### 时柱计算
- 传统时辰划分：每个时辰2小时
- 子时: 23:00-01:00, 丑时: 01:00-03:00, 等等
- 根据日干推算时干

## 验证案例

```python
# 测试案例1: 1990年5月15日10时
# 八字: 庚午 辛巳 庚辰 辛巳
# 日主: 庚金

# 测试案例2: 1992年8月20日14时  
# 八字: 壬申 戊申 戊辰 己未
# 日主: 戊土

# 合盘分析测试
# 传统合盘得分: 10分
# 关系类型: marriage
```

## 技术特点

1. **准确的历法计算**：基于中国传统历法进行精确的干支计算
2. **全面的五行分析**：包含五行分布、强弱分析、喜用神推算
3. **智能合盘算法**：多维度分析两人的八字配合度
4. **标准化接口**：基于 FastMCP 框架，提供标准化的 API 接口
5. **类型安全**：使用 Pydantic 进行数据验证和类型检查

## 注意事项

- 本工具仅提供计算数据，不包含任何建议或预测
- 计算结果基于传统八字理论，仅供参考
- 时辰计算基于24小时制，需要准确的出生时间
- 功能测试已通过，确保业务逻辑的准确性

## 版本信息

当前版本：2.0.0

## 许可证

本项目仅供学习和研究使用。

## MCP服务器

项目包含MCP服务器，可与AI助手集成：

```bash
python fastmcp_server.py
```

## 许可证

MIT License