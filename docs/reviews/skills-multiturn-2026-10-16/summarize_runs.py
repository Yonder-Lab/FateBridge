"""Inventory recorded real calls and replies; no semantic pass/fail grading."""

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def payloads(value):
    if isinstance(value, dict):
        if "run_metadata" in value or "result_delivery" in value:
            yield value
        for key, child in value.items():
            if key == "text" and isinstance(child, str):
                try:
                    yield from payloads(json.loads(child))
                except ValueError:
                    pass
            elif isinstance(child, (dict, list)):
                yield from payloads(child)
    elif isinstance(value, list):
        for child in value:
            yield from payloads(child)


def main():
    scenarios = []
    for directory in sorted((BASE / "runs").glob("dialogue_*")):
        turns = []
        for turn in sorted(directory.glob("turn-*")):
            calls = []
            for path in sorted(turn.glob("[0-9]*.json")):
                envelope = json.loads(path.read_text())
                record = envelope["record"]
                response = record.get("response")
                found = list(payloads(response))
                body = max(found, key=lambda x: len(json.dumps(x)), default={})
                receipt = body.get("run_metadata") or {}
                calls.append(
                    {
                        "record_file": str(path.relative_to(BASE)),
                        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "kind": record.get("kind"),
                        "tool": record.get("tool") or record.get("reader"),
                        "arguments": record.get("arguments"),
                        "recorded_at_utc": envelope["metadata"]["recorded_at_utc"],
                        "invocation_error": record.get("invocation_error"),
                        "is_error": response.get("isError") if isinstance(response, dict) else None,
                        "run_id": receipt.get("run_id"),
                        "trace_id": receipt.get("trace_id"),
                        "parent_run_id": receipt.get("parent_run_id"),
                        "business_output_sha256": receipt.get("business_output_sha256"),
                        "engine_is_approximate": receipt.get("engine_is_approximate"),
                        "duration_ms": receipt.get("duration_ms"),
                        "top_level_fields": sorted(k for k in body if k != "run_metadata"),
                        "result_delivery": body.get("result_delivery"),
                        "deferred_snapshots": envelope["metadata"].get("deferred_snapshots", []),
                    }
                )
            reply = turn / "assistant.md"
            user = turn / "user.md"
            turns.append(
                {
                    "turn": turn.name,
                    "user": user.read_text().strip() if user.exists() else None,
                    "assistant": reply.read_text().strip() if reply.exists() else None,
                    "assistant_sha256": hashlib.sha256(reply.read_bytes()).hexdigest() if reply.exists() else None,
                    "calls": calls,
                    "skills_read": json.loads((turn / "skills-read.json").read_text()) if (turn / "skills-read.json").exists() else None,
                }
            )
        scenarios.append({"agent": directory.name, "turns": turns})
    summary = {
        "scope": "Observed calls and saved replies; semantic audit separate",
        "scenarios": scenarios,
        "counts": {
            "scenarios_started": len(scenarios),
            "saved_replies": sum(bool(t["assistant"]) for c in scenarios for t in c["turns"]),
            "tool_calls": sum(r["kind"] == "tool" for c in scenarios for t in c["turns"] for r in t["calls"]),
            "resource_calls": sum(r["kind"] == "resource" for c in scenarios for t in c["turns"] for r in t["calls"]),
        },
    }
    (BASE / "run-inventory.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
