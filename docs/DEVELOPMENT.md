# FateBridge 开发指南

本指南为想要参与 FateBridge 开发的开发者提供完整的设置、开发流程和最佳实践。

## 目录

- [环境设置](#环境设置)
- [项目结构](#项目结构)
- [开发工作流](#开发工作流)
- [测试](#测试)
- [代码风格](#代码风格)
- [调试](#调试)
- [提交指南](#提交指南)

---

## 环境设置

### 系统要求

- **Python**: 3.8 或更高版本
- **Node.js**: 16.x 或更高版本
- **npm** 或 **yarn**: 最新版本
- **Git**: 2.x 或更高版本

### 后端开发环境

#### 1. 克隆仓库

```bash
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge
```

#### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -e ".[dev]"
```

#### 4. 环境配置

```bash
# 复制环境模板
cp .env.example .env

# 编辑 .env 文件
# 必需配置:
ALLOWED_ORIGINS=http://localhost:3000
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### 前端开发环境

#### 1. 安装依赖

```bash
cd fatebridge-web
npm install
# 或
yarn install
```

#### 2. 环境配置

```bash
# 创建 .env.local 文件
cat > .env.local <<EOF
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

#### 3. 启动开发服务器

```bash
npm run dev
# 访问 http://localhost:3000
```

---

## 项目结构

### 详细的文件树

```
FateBridge/
├── docs/                          # 文档
│   ├── API.md                    # API 文档
│   ├── ARCHITECTURE.md           # 架构文档
│   └── DEVELOPMENT.md            # 本文档
│
├── fatebridge/                   # Python 核心包
│   ├── __init__.py
│   ├── core/                     # 核心计算
│   │   ├── __init__.py
│   │   ├── calendar.py          # 干支历法计算
│   │   ├── elements.py          # 五行分析
│   │   ├── rules.py             # 格局识别
│   │   └── timing.py            # 大运流年计算
│   │
│   ├── analysis/                # 高级分析
│   │   ├── __init__.py
│   │   ├── compatibility.py     # 双人配合
│   │   └── timing_effects.py    # 时运影响
│   │
│   └── utils/                   # 工具模块
│       ├── __init__.py
│       ├── data.py              # 数据定义和常量
│       └── helpers.py           # 共享工具函数
│
├── fatebridge-web/              # Next.js 前端
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── login/
│   │   ├── auth/
│   │   └── globals.css
│   ├── components/              # React 组件
│   ├── utils/
│   ├── package.json
│   └── tsconfig.json
│
├── api.py                       # FastAPI 服务器
├── fastmcp_server.py            # FastMCP 服务器
├── logic.py                     # 业务逻辑层
│
├── requirements.txt             # Python 依赖
├── pyproject.toml              # 项目配置
├── .env.example                # 环境模板
├── .gitignore                  # Git 忽略规则
│
├── README.md                   # 项目说明
├── FIXES.md                    # 修复记录
└── LICENSE                     # MIT 许可证
```

---

## 开发工作流

### 1. 创建新分支

```bash
# 从 master 创建新分支
git checkout -b feature/your-feature-name

# 分支命名规范
# feature/...      # 新功能
# fix/...         # bug 修复
# docs/...        # 文档改进
# refactor/...    # 代码重构
# test/...        # 测试相关
```

### 2. 开发流程

#### 后端开发示例

假设要添加"获取四柱信息"的 API 端点:

**第 1 步: 更新核心模块**

```python
# fatebridge/core/calendar.py

@classmethod
def get_pillar_descriptions(cls, pillars: Dict) -> Dict[str, str]:
    """获取四柱的详细描述"""
    descriptions = {
        "year": f"{pillars['year'][0]}{pillars['year'][1]} - 年柱",
        "month": f"{pillars['month'][0]}{pillars['month'][1]} - 月柱",
        "day": f"{pillars['day'][0]}{pillars['day'][1]} - 日柱",
        "hour": f"{pillars['hour'][0]}{pillars['hour'][1]} - 时柱",
    }
    return descriptions
```

**第 2 步: 添加 API 端点**

```python
# api.py

from fastapi import APIRouter

router = APIRouter()

@app.get("/api/pillars/{year}/{month}/{day}/{hour}")
async def get_pillars(year: int, month: int, day: int, hour: int) -> dict:
    """获取四柱信息"""
    try:
        birth_date = datetime(year, month, day, hour)
        pillars = BaZiCalendar.get_four_pillars(birth_date)
        descriptions = BaZiCalendar.get_pillar_descriptions(pillars)
        return {
            "pillars": pillars,
            "descriptions": descriptions
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**第 3 步: 编写测试**

```python
# tests/test_api.py

import pytest
from api import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_pillars(client):
    response = client.get("/api/pillars/1990/5/15/10")
    assert response.status_code == 200
    data = response.json()
    assert "pillars" in data
    assert "descriptions" in data
```

#### 前端开发示例

假设要创建"四柱展示"组件:

```typescript
// fatebridge-web/components/PillarDisplay.tsx

import React from 'react';

interface Pillar {
  stem: string;
  branch: string;
}

interface PillarDisplayProps {
  pillars: {
    year: Pillar;
    month: Pillar;
    day: Pillar;
    hour: Pillar;
  };
}

export const PillarDisplay: React.FC<PillarDisplayProps> = ({ pillars }) => {
  const pillarNames = ['年柱', '月柱', '日柱', '时柱'];
  const pillarValues = [pillars.year, pillars.month, pillars.day, pillars.hour];

  return (
    <div className="grid grid-cols-4 gap-4">
      {pillarNames.map((name, index) => (
        <div key={index} className="p-4 border rounded-lg">
          <h3 className="font-bold text-center mb-2">{name}</h3>
          <div className="text-3xl font-bold text-center">
            {pillarValues[index].stem}
            <br />
            {pillarValues[index].branch}
          </div>
        </div>
      ))}
    </div>
  );
};
```

在父组件中使用:

```typescript
// fatebridge-web/components/FateBridgeChart.tsx

import { PillarDisplay } from './PillarDisplay';

export const FateBridgeChart: React.FC<Props> = ({ analysis }) => {
  return (
    <div>
      <h2>四柱分析</h2>
      <PillarDisplay pillars={analysis.four_pillars} />
    </div>
  );
};
```

### 3. 测试和验证

```bash
# 运行后端测试
pytest tests/ -v

# 检查代码风格
black --check fatebridge/ api.py logic.py
isort --check-only fatebridge/ api.py logic.py

# 类型检查
mypy fatebridge/ api.py logic.py

# 运行前端测试
cd fatebridge-web
npm run test

# 构建检查
npm run build
```

### 4. 提交代码

```bash
# 查看更改
git status
git diff

# 添加文件
git add .

# 创建提交
git commit -m "feat: Add pillar descriptions API endpoint

- Add get_pillar_descriptions() method to BaZiCalendar
- Create /api/pillars endpoint for retrieving pillar details
- Add comprehensive test coverage
- Update API documentation

Related to: #123"

# 推送到远程
git push origin feature/your-feature-name
```

---

## 测试

### 测试结构

```
tests/
├── __init__.py
├── test_calendar.py        # 历法计算测试
├── test_elements.py        # 五行分析测试
├── test_rules.py           # 格局识别测试
├── test_compatibility.py   # 配合度测试
├── test_api.py             # API 端点测试
└── fixtures.py             # 测试数据
```

### 编写测试

```python
# tests/test_calendar.py

import pytest
from datetime import datetime
from fatebridge.core.calendar import BaZiCalendar

class TestBaZiCalendar:
    """四柱历法计算测试"""

    def test_year_pillar_1984(self):
        """测试 1984 年是甲子年"""
        stem, branch = BaZiCalendar.calculate_year_pillar(1984)
        assert stem == "甲"
        assert branch == "子"

    def test_day_pillar_base_date(self):
        """测试基准日期 1984-03-31 是甲子日"""
        stem, branch = BaZiCalendar.calculate_day_pillar(1984, 3, 31)
        assert stem == "甲"
        assert branch == "子"

    @pytest.mark.parametrize("year,expected_stem,expected_branch", [
        (1990, "庚", "午"),
        (2000, "庚", "辰"),
        (2020, "庚", "子"),
    ])
    def test_year_pillar_known_values(self, year, expected_stem, expected_branch):
        """参数化测试已知的年柱值"""
        stem, branch = BaZiCalendar.calculate_year_pillar(year)
        assert stem == expected_stem
        assert branch == expected_branch

    def test_invalid_date_raises_error(self):
        """测试无效日期抛出错误"""
        with pytest.raises(ValueError):
            BaZiCalendar.calculate_day_pillar(2000, 2, 30)
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_calendar.py

# 运行特定测试类
pytest tests/test_calendar.py::TestBaZiCalendar

# 运行特定测试
pytest tests/test_calendar.py::TestBaZiCalendar::test_year_pillar_1984

# 显示详细输出
pytest -v

# 显示覆盖率
pytest --cov=fatebridge --cov-report=html
```

---

## 代码风格

### Python 代码风格指南

遵循 [PEP 8](https://peps.python.org/pep-0008/)：

```python
# ✅ 好的代码
def calculate_five_elements(pillars: Dict[str, Tuple[str, str]]) -> Dict[str, int]:
    """计算五行分布。

    Args:
        pillars: 四柱信息字典

    Returns:
        五行计数字典
    """
    element_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}

    for pillar_name, (stem, branch) in pillars.items():
        element = get_element(stem)
        if element:
            element_count[element] += 1

    return element_count

# ❌ 避免
def calc5elem(p):
    c = {}
    for k, v in p.items():
        for s in v:
            if s in stems:
                c[get_e(s)] = c.get(get_e(s), 0) + 1
    return c
```

### 使用工具自动格式化

```bash
# 自动格式化代码
black fatebridge/ api.py logic.py

# 排序导入
isort fatebridge/ api.py logic.py

# 验证代码风格
flake8 fatebridge/ api.py logic.py
```

### TypeScript/React 代码风格

```typescript
// ✅ 好的代码
interface AnalysisResult {
  person_info: PersonInfo;
  four_pillars: FourPillars;
  element_distribution: ElementDistribution;
}

const AnalysisComponent: React.FC<AnalysisComponentProps> = ({
  analysis,
  onUpdate,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalysis = async () => {
    setIsLoading(true);
    try {
      const result = await analyzeDestiny(birthInfo);
      onUpdate(result);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="analysis-container">
      {/* 组件内容 */}
    </div>
  );
};

// ❌ 避免
const AnalysisComp = (props: any) => {
  const [loading, setLoading] = useState(false);

  const handle = () => {
    setLoading(true);
    analyzeDestiny(props.info).then(r => {
      props.cb(r);
    });
  };

  return <div>{/* ... */}</div>;
};
```

---

## 调试

### 后端调试

#### 使用 Python 调试器

```python
# 在代码中设置断点
import pdb

def calculate_fatebridge(person):
    pdb.set_trace()  # 调试器会在此处暂停
    result = ...
    return result
```

或使用 IDE 的调试功能（VSCode, PyCharm）。

#### 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def calculate_fatebridge(person):
    logger.debug(f"Calculating for: {person.name}")
    logger.debug(f"Birth date: {person.birth_datetime}")

    result = ...

    logger.debug(f"Result: {result}")
    return result
```

#### 运行单个 API 测试

```bash
# 启用详细日志
LOG_LEVEL=DEBUG python api.py

# 使用 curl 测试
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10
  }' | jq .
```

### 前端调试

#### 使用浏览器开发工具

```bash
npm run dev

# 打开浏览器 DevTools (F12)
# 查看 Console, Network, Elements 等选项卡
```

#### React DevTools

```bash
# 安装 React DevTools 浏览器扩展
# https://react-devtools-tutorial.vercel.app/

# 在代码中添加调试日志
console.log('Analysis result:', analysis);
console.error('API error:', error);
```

#### 使用 VS Code 调试

创建 `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["api:app", "--reload"],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

---

## 提交指南

### 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型

- `feat`: 新功能
- `fix`: 缺陷修复
- `docs`: 文档改进
- `style`: 代码风格（格式化、分号等）
- `refactor`: 代码重构
- `perf`: 性能改进
- `test`: 测试相关
- `chore`: 构建、依赖管理等

### 示例

```bash
git commit -m "feat(calendar): Add lunar calendar support

- Implement lunar to gregorian conversion
- Add traditional Chinese calendar calculations
- Include validation for lunar dates

Closes #42
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Pre-commit 钩子

创建 `.git/hooks/pre-commit`:

```bash
#!/bin/bash

# 格式检查
black --check fatebridge/ api.py logic.py || exit 1
isort --check-only fatebridge/ api.py logic.py || exit 1

# 类型检查
mypy fatebridge/ api.py logic.py || exit 1

# 测试
pytest tests/ || exit 1
```

```bash
chmod +x .git/hooks/pre-commit
```

---

## 常见问题

### Q: 如何添加新的依赖？

```bash
# 添加到 requirements.txt
pip install new-package
pip freeze > requirements.txt

# 或在 pyproject.toml 中声明
# 然后安装
pip install -e .
```

### Q: 如何运行特定的测试用例？

```bash
pytest tests/test_calendar.py::TestBaZiCalendar::test_year_pillar_1984 -v
```

### Q: 如何查看 API 文档？

项目提供 Swagger UI：

```bash
# 启动 API 服务器
python api.py

# 访问 http://localhost:8000/docs
```

### Q: 如何贡献文档？

文档在 `docs/` 目录中，使用 Markdown 格式。提交 PR 即可。

---

## 资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Next.js 文档](https://nextjs.org/docs)
- [React 文档](https://react.dev/)
- [Python PEP 8](https://peps.python.org/pep-0008/)
- [Pytest 文档](https://docs.pytest.org/)

---

## 获取帮助

- 查看 GitHub Issues
- 查看 Discussions
- 查看 TROUBLESHOOTING.md
- 联系维护者

祝开发愉快！🚀
