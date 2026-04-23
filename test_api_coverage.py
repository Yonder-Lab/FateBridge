import requests
import json
from datetime import datetime

base_url = "http://127.0.0.1:8010"

payload_bazi = {
    "name": "TestUser",
    "gender": "男",
    "birth_year": 2000,
    "birth_month": 4,
    "birth_day": 4,
    "birth_hour": 14,
    "birth_place": "北京"
}

endpoints = [
    ("/api/cn/bazi/birth", payload_bazi),
    ("/api/cn/ziwei/birth", payload_bazi),
    ("/api/cn/qimen", {"year": 2024, "month": 1, "day": 1, "hour": 12}),
    ("/api/astro/chart", {"name": "Test", "year": 2000, "month": 1, "day": 1, "hour": 12, "minute": 0, "city": "London", "country": "GB"})
]

for url, payload in endpoints:
    try:
        res = requests.post(f"{base_url}{url}", json=payload)
        print(f"[{res.status_code}] {url}")
        if res.status_code != 200:
            print(res.text)
    except Exception as e:
        print(f"Error calling {url}: {e}")

