# FateBridge - 命运之桥

基于 FastMCP 框架的中国传统命理工具，连接古典智慧与现代技术，为您搭建通向命运洞察的桥梁。

**[English](README_EN.md)** | 中文

---

## ✨ 特性

### 🎯 核心功能

- **四柱命理计算**：精确计算年、月、日、时柱
- **五行分析**：全面的五行分布与强弱分析
- **十神关系**：详细的十神配置分析
- **格局识别**：识别三合、六合、六冲等特殊格局
- **喜用神推算**：科学推断命局所需的平衡元素

### 🤝 高级功能

- **双人配合分析**：深度分析两人八字的配合程度
- **五行互补性分析**：评估两人五行的协调性
- **十神关系对比**：分析两人十神的互动
- **关系类型适配**：针对婚姻、友谊、商业、家庭等特定关系的专化分析
- **时运分析**：大运、流年、流月的综合影响评估

### 💻 技术特点

- ✅ 基于 FastMCP 框架的标准化 API
- ✅ 精确的中国传统历法计算
- ✅ Pydantic 数据验证确保类型安全
- ✅ 模块化架构便于扩展
- ✅ 全面的错误处理和日志记录
- ✅ CORS 和安全配置
- ✅ 生产级代码质量

---

## 🚀 快速开始

### 系统要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 后端启动

```bash
# 1. 克隆仓库
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境
cp .env.example .env

# 5. 启动 API 服务器
python api.py
# API 将在 http://localhost:8000 运行

# 6. （可选）启动 FastMCP 服务器
python fastmcp_server.py
```

### 前端启动

```bash
cd fatebridge-web

# 1. 安装依赖
npm install

# 2. 配置环境
cp .env.example .env.local
# 编辑 .env.local，设置 API 地址

# 3. 启动开发服务器
npm run dev
# 前端将在 http://localhost:3000 运行
```

### 健康检查

```bash
# 检查 API 是否在线
curl http://localhost:8000/health
# 返回: {"status":"healthy"}
```

---

## 📚 使用示例

### REST API 示例

#### Python

```python
import requests
import json

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

response = requests.post(url, json=payload)
result = response.json()

print(json.dumps(result, ensure_ascii=False, indent=2))
```

#### JavaScript/TypeScript

```typescript
const response = await fetch('http://localhost:8000/api/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: '张三',
    birth_year: 1990,
    birth_month: 5,
    birth_day: 15,
    birth_hour: 10,
  }),
});

const analysis = await response.json();
console.log(analysis);
```

#### cURL

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10
  }' | jq .
```

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
print(f"日主: {element_analysis['day_master']['day_element']}")
print(f"强弱: {element_analysis['day_master']['strength_level']}")
```

---

## 📖 文档

### 用户文档

- [API 文档](docs/API.md) - 完整的 API 参考
- [快速入门](docs/GETTING_STARTED.md) - 详细的入门指南
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题解决

### 开发者文档

- [架构设计](docs/ARCHITECTURE.md) - 系统架构和模块设计
- [开发指南](docs/DEVELOPMENT.md) - 开发环境和工作流
- [贡献指南](CONTRIBUTING.md) - 如何参与开发
- [修复记录](FIXES.md) - 最近的安全和质量修复

---

## 📁 项目结构

```
FateBridge/
├── docs/                          # 文档
│   ├── API.md                    # API 完整参考
│   ├── ARCHITECTURE.md           # 架构设计
│   ├── DEVELOPMENT.md            # 开发指南
│   └── TROUBLESHOOTING.md        # 故障排除
│
├── fatebridge/                   # Python 核心包
│   ├── core/
│   │   ├── calendar.py          # 干支历法计算
│   │   ├── elements.py          # 五行分析
│   │   ├── rules.py             # 格局识别
│   │   └── timing.py            # 时运分析
│   ├── analysis/
│   │   ├── compatibility.py     # 双人配合
│   │   └── timing_effects.py    # 时运影响
│   └── utils/
│       ├── data.py              # 数据定义
│       └── helpers.py           # 工具函数
│
├── fatebridge-web/              # Next.js 前端
│   ├── app/                     # 页面和路由
│   ├── components/              # React 组件
│   └── utils/                   # 工具函数
│
├── api.py                       # FastAPI 服务器
├── fastmcp_server.py            # FastMCP 服务器
├── logic.py                     # 业务逻辑层
├── requirements.txt             # Python 依赖
├── pyproject.toml              # 项目配置
└── CONTRIBUTING.md             # 贡献指南
```

---

## 🔌 API 端点

### REST API

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/calculate` | 个人命理分析 |
| `GET` | `/health` | 健康检查 |

### FastMCP 工具

| 工具 | 说明 |
|------|------|
| `analyze_destiny` | 个人命理分析 |
| `two_person_compatibility` | 双人配合分析 |
| `timing_analysis` | 综合时运分析 |
| `dayun_analysis` | 大运专项分析 |
| `liunian_analysis` | 流年专项分析 |

---

## ⚙️ 配置

### 环境变量

```bash
# 复制环境模板
cp .env.example .env

# 编辑 .env 文件
ALLOWED_ORIGINS=http://localhost:3000  # CORS 允许的源
API_HOST=0.0.0.0                       # API 绑定地址
API_PORT=8000                          # API 端口
LOG_LEVEL=INFO                         # 日志级别
```

### 安全配置

生产环境必须配置：

```bash
# 设置允许的源为您的域名
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 使用 HTTPS
# 配置反向代理（Nginx、Apache）

# 启用速率限制（未来实现）
# 实施认证和授权（未来实现）
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 查看覆盖率
pytest --cov=fatebridge tests/

# 检查代码风格
black --check fatebridge/
isort --check-only fatebridge/

# 类型检查
mypy fatebridge/
```

---

## 🔒 安全

本项目包含以下安全特性：

- ✅ 输入验证（Pydantic）
- ✅ CORS 配置
- ✅ 错误处理（无堆栈泄露）
- ✅ 结构化日志记录
- ✅ 环境变量配置

详见 [FIXES.md](FIXES.md) 中的安全改进。

---

## 📈 性能

- 单个分析请求：< 100ms
- 双人配合分析：< 150ms
- 支持并发请求
- 优化的算法复杂度：O(1)

---

## 🗺️ 路线图

### 近期（v0.2.0）

- [ ] 批量分析 API
- [ ] 结果缓存（Redis）
- [ ] 数据库持久化

### 中期（v0.3.0）

- [ ] 用户认证系统
- [ ] 历史记录管理
- [ ] 高级建议引擎

### 长期（v1.0.0）

- [ ] GraphQL API
- [ ] WebSocket 实时分析
- [ ] 移动应用
- [ ] 预测模型

---

## 🤝 贡献

我们欢迎各种形式的贡献！

- 🐛 报告 Bug
- 💡 提议新功能
- 📝 改进文档
- 🔧 提交代码

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE)。

---

## 📧 联系

- GitHub Issues：报告 Bug 和功能请求
- GitHub Discussions：提问和讨论
- Email：[提交建议](mailto:your-email@example.com)

---

## 🙏 致谢

感谢所有为 FateBridge 做出贡献的人！

特别感谢：

- FastMCP 框架的开发者
- 传统八字理论的研究者
- 所有提出反馈和建议的用户

---

## ⭐ 如果喜欢，请给个 Star！

如果 FateBridge 对您有帮助，请在 GitHub 上给我们一个 ⭐

这将帮助我们获得更多关注，吸引更多贡献者。

---

**Made with ❤️ by the FateBridge Community**