# FateBridge 快速入门

本指南以“先把服务跑起来，再发出第一条请求”为目标，适合第一次接触 FateBridge 的用户。

## 1. 前置要求

至少准备：

- Python 3.8+
- Git

如果你计划使用西占推运能力，建议额外确认相关本地运行时可用；否则核心 chart 家族可以继续使用，但西占推运类接口会直接报依赖缺失。详细见 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)。

## 2. 克隆与安装

```bash
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

## 3. 环境变量

复制模板：

```bash
cp .env.example .env
```

默认配置如下：

```bash
API_HOST=0.0.0.0
API_PORT=8010
ALLOWED_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
FATEBRIDGE_API_KEYS=
API_KEY_HEADER_NAME=X-API-Key
```

如果你只是本地调试，通常不需要修改。

- `FATEBRIDGE_API_KEYS` 为空时，REST API 默认不启用鉴权。
- 如果设置了 `FATEBRIDGE_API_KEYS=agent:replace-me`，访问业务端点时需要带 `X-API-Key: replace-me`。
- 端口 `8010` 应保持为内部访问端口，不要直接暴露为公网业务入口。

## 4. 启动 REST API

```bash
python api.py
# 或
fatebridge-api
```

看到类似输出即可：

```text
INFO:     Uvicorn running on http://0.0.0.0:8010
```

## 5. 验证服务

### 健康检查

```bash
curl http://localhost:8010/health
```

期望响应：

```json
{"status":"healthy"}
```

### 就绪与指标

```bash
curl http://localhost:8010/ready
curl http://localhost:8010/metrics
```

### 打开交互文档

浏览器访问：

- `http://localhost:8010/docs`
- `http://localhost:8010/redoc`

## 6. 发送第一条命理请求

```bash
curl -X POST http://localhost:8010/api/calculate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: replace-me" \
  -d '{
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "birth_place": "北京",
    "use_true_solar_time": true
  }'
```

如果你没有配置 `FATEBRIDGE_API_KEYS`，可以去掉 `X-API-Key` 这一行。

你会看到类似下面的字段：

- `person_info`
- `four_pillars`
- `day_master`
- `element_distribution`
- `patterns`
- `calendar_context`

## 7. 发送第一条占星请求

```bash
curl -X POST http://localhost:8010/api/astro/chart \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chart Demo",
    "birth_year": 1990,
    "birth_month": 4,
    "birth_day": 6,
    "birth_hour": 9,
    "birth_minute": 33,
    "birth_timezone": "Asia/Shanghai",
    "birth_longitude": 121.4667,
    "birth_latitude": 31.2167,
    "birth_place": "上海"
  }'
```

如果本地 `swisseph` 可用，结果里的 `chart_profile.engine_precision` 通常会显示高精度运行时；否则会回退到 FateBridge 的离线近似模型。

## 8. 启动 FastMCP

如果你不是通过 HTTP，而是要让 Agent 直接把 FateBridge 当工具箱使用：

```bash
python fastmcp_server.py
```

FastMCP 启动后，可把它注册到你的 MCP host 中。对应工具清单见 [API.md](API.md)。

## 9. 常见下一步

### 我想看所有接口

读 [API.md](API.md)。

### 我想理解代码结构

读 [ARCHITECTURE.md](ARCHITECTURE.md)。

### 我想知道哪些能力是近似实现

读 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)。

### 我已经遇到错误

读 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
