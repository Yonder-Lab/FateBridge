"""Pinned external computation + separately transcribed published natal facts.

Run with the project Python and Node.js on PATH. Only reviewed, hash-pinned
Apache-2.0 reference JS runs in a Node vm without filesystem/network globals.
Production has no Node or network dependency. Keeps upstream five-yellow
differences visible; never patches the external engine to make it agree.
"""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

from fatebridge.core.fengshui.models import XuankongRequest
from fatebridge.core.fengshui.xuankong import natal_rules, xuankong_natal

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests/fixtures/xuankong-reference.json"
COMMIT = "2eacd85b9878452469c6669e7fff05d2c6226c97"
REPOSITORY = "YuanZHAO321/FengShuiCalculators"
HASHES = {
    "data.js": "b27b1853164655aef6ce5a220c86dc6d6d330d633fac1e1d3c44d1db4d1b9952",
    "flyingstars.js": "cd6d8ff53c07dc58f972b02bc9fe312a0054def85b486c549aff6db81ffd96c6",
}
# This adapter only calls the independent implementation and selects numbers.
# It contains no FateBridge tables, flight logic or five-yellow correction.
HARNESS = """
const fs = require('fs'), vm = require('vm');
const context = vm.createContext({});
for (const file of ['data.js', 'flyingstars.js'])
  vm.runInContext(fs.readFileSync(file, 'utf8'), context, {timeout: 5000});
const facts = vm.runInContext(`(() => {
  const rows = [];
  for (let period = 1; period <= 9; period++)
    for (const m of CM.MOUNTAINS) {
      const r = FlyingStars.compute(period, m.code, 0);
      const palaces = {};
      for (const [d,p] of Object.entries(r.palaces))
        palaces[d] = [p.base, p.mountain, p.water];
      rows.push({period, facing_mountain:m.cn,
        facing_degrees: m.code === 'N2' ? 0 : (m.deg[0]+m.deg[1])/2,
        palaces});
    }
  return rows;
})()`, context, {timeout: 5000});
process.stdout.write(JSON.stringify(facts));
"""


def external_facts() -> dict:
    with tempfile.TemporaryDirectory(prefix="fatebridge-xuankong-reference-") as temp:
        directory = Path(temp)
        for file, expected_hash in HASHES.items():
            url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/docs/js/{file}"
            with urlopen(url, timeout=30) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != expected_hash:
                raise ValueError(f"Pinned SHA-256 mismatch: {file}")
            (directory / file).write_bytes(content)
        (directory / "audit.cjs").write_text(HARNESS)
        facts = json.loads(
            subprocess.check_output(["node", "audit.cjs"], cwd=directory, timeout=30)
        )
    return {
        "repository": REPOSITORY,
        "commit": COMMIT,
        "sha256": HASHES,
        "license": "Apache-2.0",
        "scope": "216 lower charts; external implementation has no replacement stars",
        "cases": facts,
    }


def actual_case(case: dict) -> dict:
    req = XuankongRequest.model_validate(
        {
            "house": {
                "facing_degrees": case["facing_degrees"],
                "north_reference": "magnetic",
            },
            "period": {
                "basis": "expert_confirmed",
                "period_number": case["period"],
                "evidence": "独立公开盘例",
            },
        }
    )
    chart = xuankong_natal(req)["chart"]
    assert chart is not None
    return chart


def compare(fixture: dict) -> dict:
    differences = []
    nonfive = matched = 0
    oracle = fixture["five_yellow_oracle"]
    five_checked = 0
    for fact in oracle["cases"]:
        chart = actual_case(fact)
        side = fact["side"]
        trace = chart["trace"][side]
        assert trace["seed_star_number"] == trace["center_star_number"] == 5
        assert trace["mapped_mountain"] == fact["mapped_mountain"]
        assert trace["yuan"] == fact["yuan"]
        assert trace["polarity"] == fact["expected_polarity"]
        assert list(chart[side + "_chart"].values()) == fact["five_flight_numbers"]
        five_checked += 1
    for case in fixture["external"]["cases"]:
        chart = actual_case(case)
        actual = {
            d: [
                p["period_star_number"],
                p["mountain_star_number"],
                p["facing_star_number"],
            ]
            for d, p in chart["palaces"].items()
        }
        centers = case["palaces"]["C"][1:]
        if 5 not in centers:
            nonfive += 1
            assert actual == case["palaces"], (case, actual)
        if actual == case["palaces"]:
            matched += 1
        else:
            # External code uses !facing.yang for a central mountain five.
            # This contradicts the selected period/same-yuan policy. Preserve
            # every difference, require that it affects only that branch.
            assert centers[0] == 5
            assert all(actual[d][::2] == case["palaces"][d][::2] for d in actual)
            trace = chart["trace"]["mountain"]
            # Require the *entire* external mountain sequence to be the exact
            # opposite flight, rather than tolerating arbitrary five-case drift.
            reversed_flight = oracle[
                "reverse" if trace["polarity"] == "yang" else "forward"
            ]
            assert [
                case["palaces"][d][1] for d in oracle["flight_path"]
            ] == reversed_flight
            differences.append(
                {
                    "period": case["period"],
                    "facing_mountain": case["facing_mountain"],
                    "kind": "upstream_mountain_five_uses_negated_facing_polarity",
                    "expected_policy": "borrow_period_same_yuan_keep_five",
                    "source_ids": ["X2", "X3"],
                    "yuan": trace["yuan"],
                    "mapped_mountain": trace["mapped_mountain"],
                    "selected_polarity": trace["polarity"],
                    "selected_flight": trace["flight"],
                    "external_flight": (
                        "reverse" if trace["flight"] == "forward" else "forward"
                    ),
                    "exact_opposite_five_flight_verified": True,
                    "external": case["palaces"],
                    "selected_ruleset": actual,
                }
            )
    for case in fixture["published"]:
        chart = actual_case(case)
        assert chart["chart_mode"] == case["chart_mode"]
        actual = {
            d: [
                p["period_star_number"],
                p["mountain_star_number"],
                p["facing_star_number"],
            ]
            for d, p in chart["palaces"].items()
        }
        assert actual == case["palaces"], (case["label"], actual)
    return {
        "ruleset": {
            "id": natal_rules()["ruleset"]["ruleset_id"],
            "version": natal_rules()["ruleset"]["version"],
            "registry_sha256": hashlib.sha256(
                (ROOT / "src/fatebridge/data/fengshui/xuankong-v1.json").read_bytes()
            ).hexdigest(),
        },
        "external_cases": len(fixture["external"]["cases"]),
        "non_five_cases_all_matched": nonfive,
        "external_matched": matched,
        "external_differences": differences,
        "published_cases_all_matched": len(fixture["published"]),
        "independent_five_polarity_cases_all_matched": five_checked,
        "five_oracle_scope": oracle["source_scope"],
        "scope": "numeric chart agreement under a selected traditional ruleset; no prediction validation",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-external", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    fixture = json.loads(FIXTURE.read_text())
    if args.refresh_external:
        fixture["external"] = external_facts()
        FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    report = compare(fixture)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: len(v) if k == "external_differences" else v
                for k, v in report.items()
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
