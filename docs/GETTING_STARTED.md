# FateBridge 快速入门指南

5 分钟内开始使用 FateBridge。

## 目录

- [前置要求](#前置要求)
- [安装](#安装)
- [第一次运行](#第一次运行)
- [调用 API](#调用-api)
- [下一步](#下一步)

---

## 前置要求

在开始之前，确保您已安装：

- **Python 3.8+**：[下载](https://www.python.org/downloads/)
- **Node.js 16+** (可选，仅用于前端)：[下载](https://nodejs.org/)
- **Git**：[下载](https://git-scm.com/)

验证安装：

```bash
python --version   # Python 3.8+
node --version     # v16+ (可选)
git --version      # 2.x+
```

---

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge
```

### 2. 创建并激活虚拟环境

**macOS/Linux**:

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境

```bash
cp .env.example .env
```

编辑 `.env` 文件（可选，使用默认值即可）：

```bash
# .env
ALLOWED_ORIGINS=http://localhost:3000
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

---

## 第一次运行

### 启动 API 服务器

```bash
python api.py
```

您应该看到类似的输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 验证服务器

打开新的终端窗口，运行：

```bash
curl http://localhost:8000/health
```

响应应该是：

```json
{"status":"healthy"}
```

✅ 恭喜！API 服务器正在运行。

---

## 调用 API

### 方法 1: 使用 cURL（最简单）

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": true,
    "birth_place": "北京"
  }' | jq .
```

### 方法 2: 使用 Python

在新的 Python 脚本中 (`test_analysis.py`)：

```python
import requests
import json

# 定义请求数据
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
response = requests.post(
    'http://localhost:8000/api/calculate',
    json=payload
)

# 打印结果
result = response.json()
print(json.dumps(result, ensure_ascii=False, indent=2))
```

运行脚本：

```bash
pip install requests  # 如果还未安装

python test_analysis.py
```

### 方法 3: 使用 JavaScript/Node.js

创建文件 `test_analysis.js`：

```javascript
const payload = {
  name: "张三",
  birth_year: 1990,
  birth_month: 5,
  birth_day: 15,
  birth_hour: 10,
  birth_minute: 30,
  birth_timezone: "Asia/Shanghai",
  use_true_solar_time: true,
  birth_place: "北京"
};

fetch('http://localhost:8000/api/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
})
  .then(res => res.json())
  .then(data => console.log(JSON.stringify(data, null, 2)))
  .catch(err => console.error('Error:', err));
```

运行：

```bash
node test_analysis.js
```

---

## 响应示例

成功的响应包含：

```json
{
  "person_info": {
    "name": "张三",
    "birth_datetime": "1990年05月15日 10时30分",
    "normalized_birth_datetime": "1990年05月15日 10时19分",
    "gender": "男",
    "birth_place": "北京",
    "birth_timezone": "Asia/Shanghai",
    "time_adjustment": {
      "applied": true,
      "total_correction_minutes": -10.62
    }
  },
  "four_pillars": {
    "year": {"stem": "庚", "branch": "午"},
    "month": {"stem": "辛", "branch": "巳"},
    "day": {"stem": "庚", "branch": "辰"},
    "hour": {"stem": "辛", "branch": "巳"}
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
  "ten_gods": {...},
  "patterns": {...}
}
```

其中 `time_adjustment` 会包含实际采用的经度来源，以及在使用 `birth_place` 时解析出的 `resolved_place` 和 `resolution_level`，便于确认系统到底命中了城市还是省级近似值。

提示：

- 旧调用方式依然有效，只传 `birth_hour` 就能继续使用。
- 需要更高精度时，再补 `birth_minute`。
- 启用 `use_true_solar_time` 时，推荐同时传 `birth_timezone`，并显式传 `birth_longitude` 或使用内置支持的 `birth_place`。
- `birth_place` 支持中文、英文和拼音形式；系统会优先命中更具体的城市，命不中时再回退到省级近似值。

---

## 常见错误和解决方案

### 错误: "Connection refused"

```
[Errno 111] Connection refused
```

**原因**: API 服务器未运行。

**解决**:

```bash
# 确保在第一个终端运行
python api.py
```

### 错误: "400 Bad Request"

```json
{"detail": "Invalid birth date: 1990-02-30"}
```

**原因**: 无效的日期（如 2 月 30 日）。

**解决**: 使用有效的日期。

---

## 下一步

### 📚 学习更多

- [API 文档](API.md) - 所有可用端点
- [架构设计](ARCHITECTURE.md) - 系统如何工作
- [故障排除](TROUBLESHOOTING.md) - 解决常见问题

### 🧪 尝试更多功能

#### 1. 双人配合分析

在 Python 脚本中尝试：

```python
from fastmcp_server import two_person_compatibility

result = two_person_compatibility(
    "张三", 1990, 5, 15, 10,  # 第一人
    "李四", 1992, 8, 20, 14,  # 第二人
    relationship_type="marriage"
)

print(result)
```

#### 2. 时运分析

```python
from fastmcp_server import timing_analysis

result = timing_analysis(
    birth_year=1990,
    birth_month=5,
    birth_day=15,
    birth_hour=10,
    name="张三",
    analysis_year=2024  # 分析 2024 年
)

print(result)
```

### 💡 其他选项

1. **使用 FastMCP 与 AI 集成**

```bash
python fastmcp_server.py
```

配置您的 AI 助手使用 FateBridge。

2. **启动前端 Web 界面** (可选)

```bash
cd fatebridge-web
npm install
npm run dev

# 访问 http://localhost:3000
```

3. **贡献代码**

参考 [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 有用的命令参考

```bash
# 启动 API 服务器
python api.py

# 启动 FastMCP 服务器
python fastmcp_server.py

# 启动前端开发服务器
cd fatebridge-web && npm run dev

# 运行测试
pytest tests/ -v

# 查看代码风格问题
black --check fatebridge/
isort --check-only fatebridge/

# 自动修复代码风格
black fatebridge/
isort fatebridge/

# 检查类型错误
mypy fatebridge/

# 查看 API 文档
# 访问 http://localhost:8000/docs (Swagger UI)
# 访问 http://localhost:8000/redoc (ReDoc)
```

---

## 获取帮助

- 📖 查看 [README](../README.md)
- 🐛 查看 [故障排除指南](TROUBLESHOOTING.md)
- 💬 提交 GitHub Issue
- 📧 查看 [联系方式](../README.md#-联系)

---

## 下一个里程碑

现在您已经可以：

✅ 运行 FateBridge API
✅ 分析个人命理
✅ 分析两人配合

准备好了吗？

- 🔍 深入 [API 文档](API.md)
- 🏗️ 学习 [架构](ARCHITECTURE.md)
- 🛠️ 开始 [开发](DEVELOPMENT.md)

---

**祝分析愉快！🚀**
