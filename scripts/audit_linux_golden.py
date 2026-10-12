"""Read-only golden audit in the real Linux x86_64 / Python 3.12 environment.

python -m scripts.audit_linux_golden --report /tmp/golden.json \
    --actual-dir /tmp/golden-actual

Never freezes baselines or bypasses the environment guard. Save differing
outputs for review, then update only explicitly reviewed fixtures separately.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


def changed_paths(expected: Any, actual: Any, path: str = "") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}.{key}" if path else key
            if key not in expected or key not in actual:
                result.append(child)
            else:
                result.extend(changed_paths(expected[key], actual[key], child))
        return result
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [path]
        return [
            child
            for i, (a, b) in enumerate(zip(expected, actual))
            for child in changed_paths(a, b, f"{path}[{i}]")
        ]
    return [] if expected == actual else [path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--actual-dir", type=Path)
    args = parser.parse_args()
    environment = f"{platform.system()}-{platform.machine()}"
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if environment != "Linux-x86_64" or python != "3.12":
        parser.error(
            f"requires Linux-x86_64 / Python 3.12; got {environment} / {python}"
        )
    if os.getenv("FATEBRIDGE_SKIP_GOLDEN_DIFF"):
        parser.error("FATEBRIDGE_SKIP_GOLDEN_DIFF must be unset")

    from tests.golden.runner import SNAPSHOT_DIR, compute_outputs, golden_diff_active

    assert golden_diff_active()
    outputs = compute_outputs()
    frozen = {p.stem for p in SNAPSHOT_DIR.glob("*.json")}
    differences = {}
    for slug, actual in outputs.items():
        path = SNAPSHOT_DIR / f"{slug}.json"
        expected = path.read_text().rstrip("\n") if path.exists() else "null"
        if actual != expected:
            differences[slug] = {
                "changed_paths": changed_paths(
                    json.loads(expected), json.loads(actual)
                ),
                "expected_sha256": hashlib.sha256(expected.encode()).hexdigest(),
                "actual_sha256": hashlib.sha256(actual.encode()).hexdigest(),
            }
            if args.actual_dir:
                args.actual_dir.mkdir(parents=True, exist_ok=True)
                (args.actual_dir / f"{slug}.json").write_text(actual + "\n")
    report = {
        "environment": environment,
        "python": platform.python_version(),
        "image": os.getenv("FATEBRIDGE_AUDIT_IMAGE"),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in (
                "pyswisseph",
                "kerykeion",
                "fastmcp",
                "mcp",
                "lunardate",
                "pydantic",
                "pytest",
            )
        },
        "golden_diff_active": golden_diff_active(),
        "cases": len(outputs),
        "matched": len(outputs) - len(differences),
        "differences": differences,
        "missing_snapshots": sorted(set(outputs) - frozen),
        "stale_snapshots": sorted(frozen - set(outputs)),
        "baseline_mutated": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "differences"}))
    return int(bool(differences or frozen != set(outputs)))


if __name__ == "__main__":
    raise SystemExit(main())
