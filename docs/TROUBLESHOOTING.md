# FateBridge 故障排除指南

常见问题、错误消息和解决方案。

## 目录

- [安装问题](#安装问题)
- [运行时错误](#运行时错误)
- [API 问题](#api-问题)
- [前端问题](#前端问题)
- [数据验证问题](#数据验证问题)
- [性能问题](#性能问题)
- [获取更多帮助](#获取更多帮助)

---

## 安装问题

### 问题: Python 版本不兼容

**错误信息**:
```
Python 3.7 not supported. Python 3.8+ required.
```

**原因**: FateBridge 需要 Python 3.8 或更新版本。

**解决方案**:
```bash
# 检查 Python 版本
python --version

# 使用特定版本安装
python3.9 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

---

### 问题: 虚拟环境激活失败

**错误信息**:
```bash
command not found: activate
```

**原因**: 使用了错误的激活脚本。

**解决方案**:
```bash
# macOS/Linux:
source venv/bin/activate

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (CMD):
venv\Scripts\activate.bat

# 验证激活
which python  # 应该显示 venv 中的 python 路径
```

---

### 问题: 依赖安装失败

**错误信息**:
```
ERROR: Could not find a version that satisfies the requirement fastapi==0.109.0
```

**原因**: PyPI 服务器问题或版本不可用。

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 清除缓存后重试
pip cache purge
pip install -r requirements.txt

# 或使用指定的 PyPI 镜像
pip install -r requirements.txt -i https://pypi.tsinghua.edu.cn/simple
```

---

### 问题: Node.js 依赖安装失败

**错误信息**:
```
npm ERR! code E404
npm ERR! 404 Not Found - GET https://registry.npmjs.org/some-package
```

**原因**: npm 注册表问题或包不存在。

**解决方案**:
```bash
cd fatebridge-web

# 清除缓存
npm cache clean --force

# 重新安装
rm -rf node_modules package-lock.json
npm install

# 或使用 yarn
yarn install
```

---

## 运行时错误

### 问题: ModuleNotFoundError

**错误信息**:
```
ModuleNotFoundError: No module named 'fatebridge'
```

**原因**: Python 路径配置不正确。

**解决方案**:
```bash
# 确保在项目根目录
cd /path/to/FateBridge

# 安装开发模式
pip install -e .

# 或设置 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/FateBridge"

# 验证模块
python -c "import fatebridge; print(fatebridge.__file__)"
```

---

### 问题: 端口已占用

**错误信息**:
```
[ERROR] Address already in use: ('0.0.0.0', 8000)
```

**原因**: 端口 8000 被其他进程占用。

**解决方案**:
```bash
# 查找占用端口的进程 (macOS/Linux)
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用不同端口
API_PORT=8001 python api.py

# Windows 查询占用端口
netstat -ano | findstr :8000
```

---

### 问题: CORS 错误

**错误信息** (浏览器控制台):
```
Access to XMLHttpRequest at 'http://localhost:8000/api/calculate'
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**原因**: CORS 配置不正确。

**解决方案**:
```bash
# 检查 .env 文件
cat .env

# 确保 ALLOWED_ORIGINS 包含前端 URL
ALLOWED_ORIGINS=http://localhost:3000

# 重启 API 服务器
python api.py
```

---

## API 问题

### 问题: 400 Bad Request - 无效的日期

**错误信息**:
```json
{
  "detail": "Invalid birth date: 1990-02-30"
}
```

**原因**: 提供了无效的日期（如 2 月 30 日）。

**解决方案**:
```python
# 验证日期有效性
import calendar
from datetime import datetime

def validate_date(year: int, month: int, day: int) -> bool:
    """检查日期是否有效"""
    try:
        datetime(year, month, day)
        return True
    except ValueError:
        return False

# 使用前检查
if validate_date(1990, 2, 30):
    # 进行分析
    pass
else:
    print("Invalid date")

# 日期范围：
# - 月份: 1-12
# - 日期: 1-28/29/30/31 (取决于月份和闰年)
# - 时辰: 0-23 (24小时制)
```

---

### 问题: 500 Internal Server Error

**错误信息**:
```json
{
  "detail": "Internal server error"
}
```

**原因**: 服务器内部错误。

**解决方案**:
```bash
# 1. 检查服务器日志
LOG_LEVEL=DEBUG python api.py

# 2. 查看详细错误消息
# 日志中应包含完整的错误堆栈

# 3. 常见原因：
# - 数据库连接失败
# - 导入错误
# - 计算异常

# 4. 验证环境
python -c "from fatebridge.core.calendar import BaZiCalendar; print('OK')"

# 5. 测试简单请求
curl http://localhost:8000/health
```

---

### 问题: 超时错误

**错误信息**:
```
requests.exceptions.ReadTimeout: HTTPConnectionPool(host='localhost', port=8000):
Read timed out. (read timeout=5)
```

**原因**: 请求耗时过长。

**解决方案**:
```python
import requests

# 增加超时时间
response = requests.post(
    'http://localhost:8000/api/calculate',
    json=payload,
    timeout=30  # 30 秒超时
)

# 或检查计算性能
import time

start = time.time()
result = calculate_fatebridge(person)
elapsed = time.time() - start

print(f"Calculation took {elapsed:.3f} seconds")

# 如果超过 1 秒，检查是否有性能问题
```

---

## 前端问题

### 问题: 页面空白或无法加载

**症状**: 访问 http://localhost:3000 显示空白页面。

**原因**:
- 开发服务器未运行
- 构建失败
- 环境变量未配置

**解决方案**:
```bash
cd fatebridge-web

# 1. 检查开发服务器
npm run dev

# 2. 检查构建
npm run build

# 3. 检查环境变量
cat .env.local

# 4. 查看浏览器控制台错误 (F12)

# 5. 清除 Next.js 缓存
rm -rf .next/
npm run dev
```

---

### 问题: API 连接失败

**症状**: 无法从前端连接到后端 API。

**原因**:
- API 服务器未运行
- 前端 API URL 错误
- CORS 配置问题

**解决方案**:
```bash
# 1. 启动 API 服务器
python api.py

# 2. 验证 API 在线
curl http://localhost:8000/health

# 3. 检查前端配置
# .env.local 中的 NEXT_PUBLIC_API_URL 应该是:
NEXT_PUBLIC_API_URL=http://localhost:8000

# 4. 检查浏览器网络标签
# 查看请求 URL 和状态码
```

---

### 问题: 组件崩溃

**错误信息** (浏览器控制台):
```
Uncaught Error: Cannot read property 'name' of undefined
```

**原因**: 数据结构不匹配或数据未加载。

**解决方案**:
```typescript
// 添加类型检查
interface Analysis {
  person_info?: {
    name: string;
  };
}

const AnalysisComponent = ({ analysis }: { analysis?: Analysis }) => {
  if (!analysis?.person_info) {
    return <div>Loading...</div>;
  }

  return <div>{analysis.person_info.name}</div>;
};

// 或使用可选链
<div>{analysis?.person_info?.name ?? 'Unknown'}</div>
```

---

## 数据验证问题

### 问题: 字段缺失错误

**错误信息**:
```json
{
  "detail": [
    {
      "loc": ["body", "birth_year"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**原因**: 请求体缺少必需字段。

**解决方案**:
```python
# 正确的请求格式
payload = {
    "birth_year": 1990,      # 必需
    "birth_month": 5,        # 必需
    "birth_day": 15,         # 必需
    "birth_hour": 10,        # 必需
    "name": "张三",           # 可选
    "gender": "男",           # 可选
    "birth_place": "北京",   # 可选
}

# 检查所有必需字段都已包含
assert all(key in payload for key in [
    "birth_year", "birth_month", "birth_day", "birth_hour"
])
```

---

### 问题: 字段类型错误

**错误信息**:
```json
{
  "detail": [
    {
      "loc": ["body", "birth_year"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

**原因**: 字段类型不正确。

**解决方案**:
```python
# ❌ 错误
payload = {
    "birth_year": "1990",  # 字符串
    "birth_month": "5",    # 字符串
}

# ✅ 正确
payload = {
    "birth_year": 1990,    # 整数
    "birth_month": 5,      # 整数
}

# 验证类型
import json
payload = json.loads('{"birth_year": 1990, "birth_month": 5}')
```

---

### 问题: 字段值范围错误

**错误信息**:
```json
{
  "detail": [
    {
      "loc": ["body", "birth_month"],
      "msg": "ensure this value is less than or equal to 12",
      "type": "value_error.number.not_le",
      "ctx": {"limit_value": 12}
    }
  ]
}
```

**原因**: 字段值超出允许范围。

**解决方案**:
```python
# 有效范围
birth_year: 1900-2100
birth_month: 1-12
birth_day: 1-31
birth_hour: 0-23

# 验证范围
def validate_input(year: int, month: int, day: int, hour: int) -> bool:
    return (
        1900 <= year <= 2100 and
        1 <= month <= 12 and
        1 <= day <= 31 and
        0 <= hour <= 23
    )
```

---

## 性能问题

### 问题: 响应缓慢

**症状**: API 请求耗时超过 5 秒。

**原因**:
- 系统资源不足
- Python 解释器开销
- 不必要的计算

**解决方案**:
```python
# 1. 性能分析
import cProfile
import pstats

def profile_calculation():
    profiler = cProfile.Profile()
    profiler.enable()

    result = calculate_fatebridge(person)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

# 2. 监控执行时间
import time

start = time.perf_counter()
result = calculate_fatebridge(person)
elapsed = time.perf_counter() - start

print(f"Calculation: {elapsed*1000:.1f}ms")

# 3. 缓存结果
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_calculate(birth_year, birth_month, birth_day, birth_hour):
    return calculate_fatebridge(...)
```

---

### 问题: 内存使用过高

**症状**: 应用程序占用过多内存或经常崩溃。

**原因**:
- 大型数据结构保留在内存中
- 内存泄漏
- 递归过深

**解决方案**:
```python
# 1. 监控内存
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f"Memory: {memory_info.rss / 1024 / 1024:.1f} MB")

# 2. 及时释放资源
def process_batch(items):
    for item in items:
        result = process_item(item)
        yield result  # 使用生成器而非列表

# 3. 限制缓存大小
from functools import lru_cache

@lru_cache(maxsize=128)  # 限制缓存条目数
def expensive_calculation(...):
    ...
```

---

## 获取更多帮助

### 提交问题时包含的信息

```
## 环境信息
- 操作系统: (macOS / Linux / Windows)
- Python 版本: (python --version)
- Node.js 版本: (node --version)
- npm 版本: (npm --version)

## 问题描述
清晰地描述问题和重现步骤。

## 错误消息
完整的错误堆栈跟踪。

## 预期行为
应该发生什么。

## 实际行为
实际发生了什么。
```

### 获取帮助的方式

1. **查看日志**: 启用 DEBUG 日志获取详细信息
2. **检查文档**: 查看 API.md 和 ARCHITECTURE.md
3. **提交 Issue**: 在 GitHub 上提交详细的问题报告
4. **查看讨论**: 在 GitHub Discussions 中分享经验

---

## 常见命令参考

```bash
# 启用调试日志
LOG_LEVEL=DEBUG python api.py

# 检查依赖
pip show fastapi pydantic

# 验证安装
python -c "import fatebridge; print(fatebridge.__version__)"

# 运行测试
pytest tests/ -v --tb=short

# 清除缓存
rm -rf .pytest_cache __pycache__ .mypy_cache .next/ node_modules/

# 查看系统信息
uname -a  # macOS/Linux
systeminfo  # Windows
```

---

希望这个指南能帮助您解决问题！

如果问题仍未解决，请在 GitHub 上提交 Issue。
