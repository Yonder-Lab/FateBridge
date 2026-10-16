"""Archive this task's observed dialogues and build readable transcript views.

No model or FateBridge calls are made. Raw records are copied byte for byte.
The private checks were not delivered to consultation actors.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

SOURCE = Path("/tmp/fatebridge-natural-acceptance-20261015")
DEST = Path(__file__).resolve().parent


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    baseline = json.loads((SOURCE / "cases.json").read_text())["cases"]
    replays = json.loads((SOURCE / "retest-cases.json").read_text())
    case_map = {
        f"dialogue_{chr(97 + i)}": {
            "id": case["id"],
            "phase": "baseline",
            "messages": case["messages"],
        }
        for i, case in enumerate(baseline)
    }
    for case in replays:
        case_map[case["agent"]] = {
            "id": case.get(
                "baseline_case",
                "held_out_timing" if "timing" in case["kind"] else "held_out_profile",
            ),
            "phase": case["kind"],
            "messages": case["messages"],
            "revision_note": case.get("third_turn_note"),
        }

    for directory in (
        "runs",
        "baseline",
        "revised",
        "revised-2",
        "revised-3",
        "before-targeted-fixes",
    ):
        shutil.copytree(SOURCE / directory, DEST / directory, dirs_exist_ok=True)
    filenames = [
        "cases.json",
        "private-checks.json",
        "retest-cases.json",
        "baseline-run-inventory.json",
        "baseline-complete-skill-hashes.json",
        "logging-helper.txt",
        "record_mcp.py",
        "summarize_runs.py",
        "initial-status.txt",
        "engineering-pytest.txt",
        "audit-baseline.json",
        "audit-retest.json",
        "audit-holdout.json",
        "engineering-checks.json",
        "cli-preflight.json",
        "skill-validation.json",
        "targeted-fixes.patch",
        "liunian-narrow-engineering.json",
        "audit-efficiency.json",
    ]
    for filename in filenames:
        source = SOURCE / filename
        if source.exists():
            shutil.copyfile(source, DEST / filename)
    for filename in (
        "audit-baseline.md",
        "audit-retest.md",
        "audit-holdout.md",
        "audit-efficiency.md",
    ):
        source = SOURCE / filename
        if source.exists():
            raw = source.read_text()
            (DEST / filename.replace(".md", ".raw.md")).write_text(raw)
            (DEST / filename).write_text(
                "> 本副本仅将临时归档链接改为本目录；审查正文未改，原文另存 `.raw.md`。\n\n"
                + raw.replace(str(SOURCE), str(DEST))
            )

    transcripts = DEST / "transcripts"
    transcripts.mkdir(exist_ok=True)
    inventory = []
    index = [
        "# 自然多轮对话原文",
        "",
        "人物均为虚构。每轮答复按原文保留；失败调用也保留。",
        "",
    ]
    for agent, case in case_map.items():
        run = SOURCE / "runs" / agent
        if not run.exists():
            continue
        lines = [f"# {agent} / {case['id']} / {case['phase']}", ""]
        if case.get("revision_note"):
            lines.extend([case["revision_note"], ""])
        completed = 0
        records = []
        errors = []
        for i, message in enumerate(case["messages"], 1):
            turn = run / f"turn-{i:02d}"
            answer = turn / "assistant.md"
            saved_user = turn / "user.md"
            user_source = (
                "user.md" if saved_user.exists() else "cases.json中的实际已发送消息"
            )
            if saved_user.exists():
                assert saved_user.read_text().strip() == message
            lines.extend(
                [f"## 第{i}轮", "", f"用户（来源：{user_source}）：", "", message, ""]
            )
            if not answer.exists():
                lines.extend(["本轮尚无保存答复。", ""])
                continue
            completed += 1
            lines.extend(
                ["助手原文：", "", answer.read_text().strip(), "", "本轮原始调用：", ""]
            )
            for record_path in sorted(turn.glob("[0-9]*.json")):
                envelope = json.loads(record_path.read_text())
                record = envelope["record"]
                response = record.get("response")
                is_error = bool(record.get("invocation_error")) or (
                    isinstance(response, dict) and bool(response.get("isError"))
                )
                name = record.get("tool") or record.get("reader")
                relative = record_path.relative_to(SOURCE)
                item = {
                    "path": str(relative),
                    "tool": name,
                    "kind": record["kind"],
                    "is_error": is_error,
                    "sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(),
                }
                records.append(item)
                if is_error:
                    errors.append(item)
                suffix = "（返回错误，原样保留）" if is_error else ""
                lines.append(f"- [{name}](../{relative.as_posix()}){suffix}")
            if not list(turn.glob("[0-9]*.json")):
                lines.append("- 本轮没有新增 FateBridge 调用。")
            lines.append("")
        filename = f"{agent}.md"
        (transcripts / filename).write_text("\n".join(lines))
        index.append(
            f"- [{agent} / {case['id']} / {case['phase']}](transcripts/{filename})：{completed}轮"
        )
        inventory.append(
            {
                "agent": agent,
                "case": case["id"],
                "phase": case["phase"],
                "expected_turns": len(case["messages"]),
                "saved_replies": completed,
                "records": records,
                "error_records": errors,
            }
        )
    (DEST / "transcripts.md").write_text("\n".join(index) + "\n")
    dump(DEST / "observed-inventory.json", inventory)

    # Original metadata may reference temporary paths. Keep originals untouched
    # and supply an explicit relocation map instead of rewriting raw evidence.
    relocation = {
        str(source): str(DEST / source.relative_to(SOURCE))
        for source in (SOURCE / "runs").rglob("*")
        if source.is_file()
    }
    dump(DEST / "archive-path-map.json", relocation)
    hashes = {
        str(path.relative_to(DEST)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(DEST.rglob("*"))
        if path.is_file() and path.name != "artifact-hashes.json"
    }
    dump(DEST / "artifact-hashes.json", hashes)
    print(
        json.dumps(
            {
                "dialogues": len(inventory),
                "saved_replies": sum(c["saved_replies"] for c in inventory),
                "raw_records": sum(len(c["records"]) for c in inventory),
                "error_records": sum(len(c["error_records"]) for c in inventory),
                "artifact_files": len(hashes),
            }
        )
    )


if __name__ == "__main__":
    main()
