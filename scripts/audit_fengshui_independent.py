"""Optional pinned comparison; production and ordinary tests remain offline.

Downloads only the previously reviewed reference helper, verifies its SHA-256
before importing it, and records reference facts (not vendored source). The
reference is MIT licensed. Exact-year boundaries are outside its capability.
Run: .venv/bin/python scripts/audit_fengshui_independent.py
"""

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

from fatebridge.core.fengshui.bazhai import minggua, sectors
from fatebridge.core.fengshui.models import MingguaRequest

COMMIT = "2666304c5cb4ac13091c8c1fcdd4e40c218b275a"
HASH = "ffc23b2c7994d02642052f6402f0471e478697f59861153a5dbd6fd6ebcc3824"
URL = f"https://raw.githubusercontent.com/JackieL233/fengshui-master/{COMMIT}/fengshui-master/scripts/minggua.py"
DESTINATION = (
    Path(__file__).parents[1] / "tests" / "fixtures" / "fengshui-reference.json"
)


def main() -> None:
    with urlopen(URL, timeout=30) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != HASH:
        raise ValueError("Pinned reference SHA-256 mismatch")
    with tempfile.TemporaryDirectory(
        prefix="fatebridge-fengshui-reference-"
    ) as directory:
        path = Path(directory) / "minggua.py"
        path.write_bytes(content)
        spec = importlib.util.spec_from_file_location("reference_minggua", path)
        assert spec is not None and spec.loader is not None
        reference = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reference
        spec.loader.exec_module(reference)
        years = []
        for year in range(1900, 2100):
            values = []
            for convention in ("male", "female"):
                expected = reference.ming_gua(year, convention).gua_number
                actual = minggua(
                    MingguaRequest(
                        effective_birth_year=year, gender_convention=convention
                    )
                )["candidates"][0]["palace_number"]
                assert actual == expected, (year, convention, actual, expected)
                values.append(expected)
            years.append([year, *values])
        numbers = {
            1: "坎",
            2: "坤",
            3: "震",
            4: "巽",
            6: "乾",
            7: "兑",
            8: "艮",
            9: "离",
        }
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
            "north": "N",
            "southwest": "SW",
            "east": "E",
            "southeast": "SE",
            "northwest": "NW",
            "west": "W",
            "northeast": "NE",
            "south": "S",
        }
        table = {}
        for number, trigram in numbers.items():
            table[trigram] = {}
            for label, star in names.items():
                direction = directions[reference.DIRECTIONS[number][label]]
                assert (
                    sectors(trigram, "reference", "test")[direction]["star"]["name"]
                    == star
                )
                table[trigram][direction] = star
    result = {
        "source_url": URL,
        "commit": COMMIT,
        "sha256": HASH,
        "reference_license": "MIT",
        "scope": "1900–2099 effective years only; no birth instant, annual stars, Jinsuo or natal chart verification",
        "minggua_columns": ["year", "male", "female"],
        "minggua_numbers": years,
        "bazhai_table": table,
        "comparison": {"minggua_cases": 400, "direction_pairs": 64, "all_passed": True},
    }
    DESTINATION.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["comparison"]))


if __name__ == "__main__":
    main()
