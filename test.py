import requests
import json

# 定义请求数据
payload = {
    "name": "左右",
    "gender": "男",
    "birth_year": 2000,
    "birth_month": 12,
    "birth_day": 10,
    "birth_hour": 9,
    "birth_place": "江苏"
}

# 发送请求
response = requests.post(
    'http://localhost:8000/api/calculate',
    json=payload
)

# 打印结果
result = response.json()
print(json.dumps(result, ensure_ascii=False, indent=2))