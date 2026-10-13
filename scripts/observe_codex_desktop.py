"""Read selected persisted Codex Desktop turns without exporting private traces.

No app-server, experimental flags, telemetry configuration or app restart is used.
Log bodies, messages, reasoning, credentials and tool arguments never enter output.
Remote queue and model processing are deliberately reported as unavailable.
"""

import argparse
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


def connect(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def code_calls(code):
    """Only function identifiers, never constants or arbitrary code/text."""
    return sorted(
        set(
            re.findall(
                r"\b(?:ALL_TOOLS\.(?:find|filter)|tools\.mcp__[A-Za-z_0-9]+)(?=\s*\()",
                code,
            )
        )
    )


def host_event(target, body):
    """Allowlist native event semantics; a start marker is never a duration.

    In particular, 'without waiting' must not become a startup wait. Raw log
    strings and arbitrary scalar fields are deliberately excluded.
    """
    lower = body.lower()
    event = None
    if (
        target == "codex_core::session::world_state"
        and "building step world state" in lower
    ):
        event = {"kind": "world_state_build_started"}
    elif target == "codex_core::shell_snapshot":
        event = {"kind": "session_shell_snapshot_event"}
    elif target == "codex_mcp::connection_manager::tool_catalog":
        if "using cached" in lower and "without waiting" in lower:
            kind = "tool_catalog_cache_used_without_startup_wait"
        elif "omitting" in lower:
            kind = "tool_catalog_server_omitted"
        else:
            kind = "tool_catalog_event_unclassified"
        event = {"kind": kind}
    elif target == "codex_skills_extension::render_observability":
        event = {"kind": "skill_snapshot_rendered"}
    elif target == "codex_skills_extension::shadow_selection_experiment":
        event = {"kind": "shadow_skill_selection_event"}
    elif (
        target == "codex_mcp::rmcp_client" and "startup" in lower and "failed" in lower
    ):
        event = {"kind": "mcp_startup_failed"}
    if event is None:
        return None
    server = re.search(r'\bserver_name="?([A-Za-z_][A-Za-z_0-9-]*)', body)
    if server:
        event["server"] = server[1]
    allowed = {
        "total_skills",
        "included_skills",
        "omitted_skills",
        "budget_limit",
        "selected_capability_root_count",
        "catalog_entries",
        "selected_entries",
    }
    event.update(
        {
            key: int(value)
            for key, value in re.findall(r"\b([a-z_]+)=(\d+)\b", body)
            if key in allowed
        }
    )
    return event


def request_flags(body):
    """Read only selected feature booleans, never arbitrary request tags."""
    if "tags_json=" not in body:
        return {}
    try:
        tags = json.JSONDecoder().raw_decode(body.split("tags_json=", 1)[1])[0]
    except (ValueError, TypeError):
        return {}
    if not isinstance(tags, dict):
        return {}
    result = {}
    for name in (
        "code_mode_host",
        "code_mode_prewarm",
        "deferred_tool_world_state",
        "incremental_tools",
        "skip_host_skill_discovery",
        "skill_search",
    ):
        value = tags.get("feature." + name)
        if isinstance(value, bool):
            result[name] = value
        elif value in ("true", "false"):
            result[name] = value == "true"
    return result


def observe(home, thread_id):
    with connect(home / "state_5.sqlite") as state:
        row = state.execute(
            "select id,rollout_path,model,reasoning_effort,originator,source,cwd "
            "from threads where id=?",
            (thread_id,),
        ).fetchone()
    if row is None or row["originator"] != "Codex Desktop":
        raise ValueError("Expected a persisted Codex Desktop thread")
    result = {
        key: row[key]
        for key in ("id", "model", "reasoning_effort", "originator", "source", "cwd")
    }
    turns = {}
    current = None
    with Path(row["rollout_path"]).open() as stream:
        for line in stream:
            record = json.loads(line)
            payload = record.get("payload", {})
            kind = payload.get("type")
            at = timestamp(record["timestamp"])
            if record["type"] == "event_msg" and kind == "task_started":
                current = payload["turn_id"]
                turns[current] = {
                    "turn_id": current,
                    "started_at": at,
                    "code_calls": [],
                }
            if current not in turns:
                continue
            turn = turns[current]
            if record["type"] == "turn_context":
                turn["model"] = payload.get("model")
                turn["effort"] = payload.get("effort")
            if record["type"] == "event_msg" and kind == "task_complete":
                turn["completed_at"] = at
            if record["type"] == "response_item" and kind in {
                "custom_tool_call",
                "function_call",
            }:
                code = payload.get("input", "")
                turn["code_calls"].append(
                    {
                        "at_seconds": round(at - turn["started_at"], 6),
                        "identifiers": code_calls(code),
                        "code_bytes": len(code.encode()),
                    }
                )
    with (
        connect(home / "thread_history_1.sqlite") as history,
        connect(home / "logs_2.sqlite") as logs,
    ):
        for turn in turns.values():
            native = history.execute(
                "select duration_ms,status from thread_turns where thread_id=? and turn_id=?",
                (thread_id, turn["turn_id"]),
            ).fetchone()
            turn["native_duration_ms"] = native["duration_ms"] if native else None
            turn["status"] = native["status"] if native else "unavailable"
            start, end = turn["started_at"], turn.get("completed_at", float("inf"))
            requests, events, timings, startup_failures = [], [], [], []
            host_events, flags, code_starts = [], [], []
            for log in logs.execute(
                "select ts,ts_nanos,target,feedback_log_body from logs "
                "where thread_id=? and ts>=? and ts<=? order by ts,ts_nanos",
                (thread_id, int(start), int(end) + 1 if end != float("inf") else 2**62),
            ):
                at = log["ts"] + log["ts_nanos"] / 1e9
                if not start <= at <= end:
                    continue
                body, target = log["feedback_log_body"], log["target"]
                event = host_event(target, body)
                if event:
                    event["at_seconds"] = round(at - start, 6)
                    host_events.append(event)
                    if event["kind"] == "mcp_startup_failed" and "server" in event:
                        startup_failures.append(
                            {
                                "server": event["server"],
                                "at_seconds": event["at_seconds"],
                            }
                        )
                if target == "feedback_tags" and "tags_json=" in body:
                    # A request-prepared boundary, not a server-received timestamp.
                    requests.append(at)
                    flags.append(request_flags(body))
                elif target == "codex_core::stream_events_utils":
                    events.append(at)
                    if re.search(r'\bitem_type="?custom_tool_call\b', body):
                        code_starts.append(at)
                elif target == "codex_code_mode::timing":
                    match = re.search(r"\bcode_mode_host_duration_ns=(\d+)", body)
                    if match:
                        timings.append(
                            {
                                "at_seconds": round(at - start, 6),
                                "execution_ms": int(match[1]) / 1e6,
                            }
                        )
            turn["request_count"] = len(requests)
            turn["requests"] = [
                {
                    "prepared_at_seconds": round(at - start, 6),
                    "first_stream_event_after_ms": (
                        round((min(following) - at) * 1000, 3) if following else None
                    ),
                }
                for index, at in enumerate(requests)
                for following in [
                    [
                        e
                        for e in events
                        if at
                        <= e
                        < (requests[index + 1] if index + 1 < len(requests) else end)
                    ]
                ]
            ]
            turn["host_before_first_request_ms"] = (
                round((requests[0] - start) * 1000, 3) if requests else None
            )
            turn["code_mode_executions"] = timings
            turn["mcp_startup_failures"] = startup_failures
            turn["host_preparation"] = {
                "events": [
                    event
                    for event in host_events
                    if not requests or event["at_seconds"] <= requests[0] - start
                ],
                "exclusive_plugin_startup_ms": None,
                "exclusive_tool_loading_ms": None,
                "exclusive_session_initialization_ms": None,
                "measurement_limit": "Events are concurrent boundaries; world-state markers are starts and cached catalogs explicitly avoid startup waits. No exclusive stage spans are exported.",
            }
            for index, request in enumerate(turn["requests"]):
                request["feature_flags"] = flags[index]
                boundary = requests[index + 1] if index + 1 < len(requests) else end
                streamed = [
                    at for at in code_starts if requests[index] <= at < boundary
                ]
                completed = [
                    call
                    for call in turn["code_calls"]
                    if requests[index] - start <= call["at_seconds"] < boundary - start
                ]
                request["streamed_code_window_ms"] = (
                    round(
                        (completed[0]["at_seconds"] - (streamed[0] - start)) * 1000, 3
                    )
                    if streamed and completed
                    else None
                )
                request["streamed_code_started_at_seconds"] = (
                    round(streamed[0] - start, 6) if streamed else None
                )
            calls = []
            for item in history.execute(
                "select started_at_ms,completed_at_ms,item_json from thread_items "
                "where thread_id=? and turn_id=? and item_type='mcpToolCall' order by rollout_ordinal",
                (thread_id, turn["turn_id"]),
            ):
                info = json.loads(item["item_json"])
                calls.append(
                    {
                        "server": info.get("server"),
                        "tool": info.get("tool"),
                        "duration_ms": info.get("durationMs"),
                        "started_at_seconds": round(
                            item["started_at_ms"] / 1000 - start, 6
                        ),
                        "completed_at_seconds": (
                            round(item["completed_at_ms"] / 1000 - start, 6)
                            if item["completed_at_ms"]
                            else None
                        ),
                    }
                )
            turn["mcp_calls"] = calls
            turn["remote_queue_ms"] = None
            turn["model_processing_ms"] = None
            turn["remote_measurement_limit"] = (
                "Client request/stream boundaries include transport, queue and model work; server substage metrics unavailable."
            )
    result["turns"] = list(turns.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread", action="append", required=True)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [observe(args.codex_home, thread) for thread in args.thread]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"threads": records}, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
