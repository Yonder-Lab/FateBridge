"""Compare the research formulas with two reviewed, pinned external helpers.

Downloads source into a temporary directory, verifies its hash before import,
and saves only comparison results. This is an audit, not a runtime dependency.
Run probe.py first. Internet access is required for this optional comparison.
"""

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

COMMIT = "2666304c5cb4ac13091c8c1fcdd4e40c218b275a"
REPOSITORY = "JackieL233/fengshui-master"
FILES = {
    "minggua": "ffc23b2c7994d02642052f6402f0471e478697f59861153a5dbd6fd6ebcc3824",
    "flying_stars": "e426804ea08c6e2252fe7f825a37e47e43ba1a10733493bf828110eb16894bd9",
}
BASE = Path(__file__).parent
probe = json.loads((BASE / "probe-results.json").read_text(encoding="utf-8"))

with tempfile.TemporaryDirectory(prefix="fatebridge-fengshui-reference-") as directory:
    modules = {}
    for filename, expected_hash in FILES.items():
        url = (
            f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/"
            f"fengshui-master/scripts/{filename}.py"
        )
        with urlopen(url, timeout=30) as response:
            content = response.read()
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"Source hash mismatch: {filename}")
        path = Path(directory) / f"{filename}.py"
        path.write_bytes(content)
        module_name = f"audited_reference_{filename}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        modules[filename] = module

    minggua = modules["minggua"]
    numbers = {1: "坎", 2: "坤", 3: "震", 4: "巽", 6: "乾", 7: "兑", 8: "艮", 9: "离"}
    names = {
        "sheng_qi": "生气",
        "tian_yi": "天医",
        "yan_nian": "延年",
        "fu_wei": "伏位",
        "jue_ming": "绝命",
        "wu_gui": "五鬼",
        "liu_sha": "六煞",
        "huo_hai": "祸害",
    }
    directions = {
        "north": "坎",
        "southwest": "坤",
        "east": "震",
        "southeast": "巽",
        "northwest": "乾",
        "west": "兑",
        "northeast": "艮",
        "south": "离",
    }
    direction_cases = 0
    for number, name in numbers.items():
        for label, star in names.items():
            target = directions[minggua.DIRECTIONS[number][label]]
            assert probe["bazhai_table"][name][target] == star
            direction_cases += 1
    for year in range(1900, 2100):
        for convention in ("male", "female"):
            raw = (
                (1 - (year - 1864) if convention == "male" else 5 + (year - 1864)) - 1
            ) % 9 + 1
            expected = (2 if convention == "male" else 8) if raw == 5 else raw
            assert minggua.ming_gua(year, convention).gua_number == expected

    flying = modules["flying_stars"]
    assert flying.period_for_year(2026) == (9, 2024, 2043)
    assert flying.flying_chart(9).center == 9

output = {
    "repository": REPOSITORY,
    "commit": COMMIT,
    "sha256": FILES,
    "minggua_cases_1900_2099": 400,
    "eight_mansions_direction_pairs": direction_cases,
    "all_passed": True,
    "flying_stars_2026_year_argument_means": "period 9 scaffold, not annual center 1",
    "limits": [
        "No exact birth-instant handling in the reference minggua helper.",
        "No annual/monthly/natal engine in the inspected flying_stars helper.",
        "No independent Jinsuo engine was verified.",
    ],
}
(BASE / "external-comparison.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(output, ensure_ascii=False, indent=2))
