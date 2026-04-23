import requests
import json
import traceback

base_url = "http://127.0.0.1:8010"

endpoints = [
    # BaZi / ZiWei
    ("/api/cn/bazi/birth", {"name": "Test", "gender": "男", "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14, "birth_place": "北京"}),
    ("/api/cn/bazi/direct", {"bazi": ["庚辰", "己卯", "壬午", "丁未"], "gender": "男", "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14}),
    ("/api/cn/ziwei/birth", {"name": "Test", "gender": "男", "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14, "birth_place": "北京"}),
    
    # QiMen / TaiYi
    ("/api/cn/qimen", {"analysis_year": 2024, "analysis_month": 1, "analysis_day": 1, "analysis_hour": 12}),
    ("/api/cn/taiyi", {"analysis_year": 2024, "analysis_month": 1, "analysis_day": 1, "analysis_hour": 12}),
    
    # Astrology
    ("/api/astro/chart", {"name": "Test", "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14, "birth_minute": 30, "birth_longitude": -0.1276, "birth_latitude": 51.5072, "birth_timezone": "Europe/London"}),
    ("/api/astro/timing/transit", {"birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14, "birth_minute": 30, "birth_longitude": -0.1276, "birth_latitude": 51.5072, "birth_timezone": "Europe/London", "analysis_year": 2024, "analysis_month": 1, "analysis_day": 1}),
    
    # Divination
    ("/api/divination/meihua", {"question": "Test", "analysis_year": 2024, "analysis_month": 1, "analysis_day": 1, "analysis_hour": 12, "number1": 1, "number2": 2}),
    ("/api/divination/sixyao", {"question": "Test", "date": "2024-01-01", "time": "12:00:00"}),
    
    # Compatibility
    ("/api/compatibility", {"person1_name": "P1", "person1_gender": "男", "person1_birth_year": 2000, "person1_birth_month": 1, "person1_birth_day": 1, "person1_birth_hour": 12, "person2_name": "P2", "person2_gender": "女", "person2_birth_year": 2001, "person2_birth_month": 1, "person2_birth_day": 1, "person2_birth_hour": 12}),

    # Other timing
    ("/api/timing/jieqi", {"jieqis": ["立春"], "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14}),
    ("/api/timing/liunian", {"name": "Test", "gender": "男", "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14, "target_year": 2024}),
    ("/api/timing/liuyue", {"name": "Test", "gender": "男", "birth_year": 2000, "birth_month": 4, "birth_day": 4, "birth_hour": 14, "analysis_year": 2024, "analysis_month": 1}),
]

results = []
for url, payload in endpoints:
    try:
        res = requests.post(f"{base_url}{url}", json=payload)
        status = res.status_code
        if status != 200:
            results.append(f"FAILED: {url} -> {status} {res.text}")
        else:
            results.append(f"SUCCESS: {url}")
    except Exception as e:
        results.append(f"ERROR: {url} -> {str(e)}")

for r in results:
    print(r)
