"""Run the independent daliurenpython transmission classes, without its UI.

References must be isolated Git checkouts at the commits below. This loads
unmodified AST definitions (only excludes imports/UI/calendar classes), with
the reference's own ganzhiwuxin objects. It does not replace reference math
with FateBridge helpers. All valid day/hour/month-general combinations run.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import subprocess
import sys
from datetime import datetime
from itertools import product
from pathlib import Path

from fatebridge.core.metaphysics import MetaphysicsSeed, build_liureng_board

REFERENCE_COMMIT = "2afe9194e3644d2ead5652ed8b366ae6c70d7087"
SUPPORT_COMMIT = "0efdcc5c473487ef61b2e941005716056174cc54"


def load_oracle(reference: Path, support: Path) -> dict:
    for path, expected in ((reference, REFERENCE_COMMIT), (support, SUPPORT_COMMIT)):
        actual = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
        if actual != expected:
            raise ValueError(f"Oracle version mismatch: {actual} != {expected}")
        if subprocess.check_output(
            ["git", "-C", str(path), "diff", "--", "shipan/shipan.py", "ganzhiwuxin"],
            text=True,
        ):
            raise ValueError("Oracle source has uncommitted changes")
    sys.path.insert(0, str(support))
    namespace = dict(vars(importlib.import_module("ganzhiwuxin")))
    source = reference / "shipan/shipan.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {"NoSanchuan", "寄宫", "干Of寄宫", "TianPan", "SiKe", "SanChuan"}
    tree.body = [
        node
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names
    ]
    exec(compile(tree, str(source), "exec"), namespace)
    return namespace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--ganzhi", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Optionally save the 720 reference boards for offline tests",
    )
    args = parser.parse_args()
    oracle = load_oracle(args.reference, args.ganzhi)
    stems, branches = "甲乙丙丁戊己庚辛壬癸", "子丑寅卯辰巳午未申酉戌亥"
    rows, errors, mismatches = [], [], []
    for day, hour, month_general in product(range(60), range(12), range(12)):
        stem, branch = stems[day % 10], branches[day % 12]
        key = stem + branch + branches[hour] + branches[month_general]
        try:
            tp = oracle["TianPan"](
                oracle["支"](branches[month_general]), oracle["支"](branches[hour])
            )
            sk = oracle["SiKe"](
                tp, oracle["干支"](oracle["干"](stem), oracle["支"](branch))
            )
            sc = oracle["SanChuan"](tp, sk)
            expected = [str(sc.初), str(sc.中), str(sc.末)]
            dt = datetime(2026, 1, 1, hour * 2)
            seed = MetaphysicsSeed(
                dt,
                dt,
                "+08:00",
                None,
                False,
                0,
                {
                    "year": ("丙", "午"),
                    "month": ("戊", "子"),
                    "day": (stem, branch),
                    "hour": (stems[(day % 10 * 2 + hour) % 10], branches[hour]),
                },
                {"current_solar_term": {"name": "冬至"}},
            )
            board = build_liureng_board(
                seed, month_general_override=branches[month_general]
            )
            got = [
                board["three_transmissions"][k]["branch"]
                for k in ("initial", "middle", "final")
            ]
            if got != expected:
                mismatches.append({"input": key, "ours": got, "reference": expected})
            if hour == 0:
                rows.append(
                    {
                        "day": stem + branch,
                        "offset": month_general,
                        "transmissions": expected,
                        "styles": sc.格局,
                    }
                )
        except Exception as exc:
            errors.append({"input": key, "error": repr(exc)})
    reference = {
        "repo": "https://github.com/d1210182010/daliurenpython-zh-tw",
        "commit": REFERENCE_COMMIT,
        "support_repo": "https://github.com/wlhyl/ganzhiwuxinForPython",
        "support_commit": SUPPORT_COMMIT,
        "loading": "Unmodified AST definitions: NoSanchuan, 寄宫, 干Of寄宫, TianPan, SiKe, SanChuan; original reference Ganzhi objects; no calendar/UI execution.",
        "source_sha256": hashlib.sha256(
            (args.reference / "shipan/shipan.py").read_bytes()
        ).hexdigest(),
    }
    result = {
        "summary": {
            "combinations": 8640,
            "unique_boards": 720,
            "differences": len(mismatches),
            "errors": len(errors),
        },
        "scope": "Same-input transformation only; preserves FateBridge calendar and贵人 conventions.",
        "reference": reference,
        "mismatches": mismatches,
        "errors": errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.fixture:
        args.fixture.write_text(
            json.dumps(
                {"reference": reference, "cases": rows}, ensure_ascii=False, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result["summary"], ensure_ascii=False))
    if errors or mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
