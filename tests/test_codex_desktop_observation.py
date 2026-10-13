"""Desktop timing is read-only and must not export private native content."""

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "desktop_observer", ROOT / "scripts/observe_codex_desktop.py"
)
observer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(observer)


def test_private_content_is_not_exported_and_remote_stages_are_unknown(tmp_path):
    secret = "PRIVATE_TOKEN_REASONING_MESSAGE"
    start = observer.timestamp("2026-10-13T00:00:00Z")
    rollout = tmp_path / "rollout.jsonl"
    records = [
        ("00", "event_msg", {"type": "task_started", "turn_id": "turn"}),
        ("01", "turn_context", {"model": "original", "effort": "high"}),
        ("02", "response_item", {"type": "reasoning", "text": secret}),
        (
            "03",
            "response_item",
            {
                "type": "custom_tool_call",
                "input": f"secret='{secret}'; await tools.mcp__fatebridge__bazi_career({{}})",
            },
        ),
        ("10", "event_msg", {"type": "task_complete"}),
    ]
    rollout.write_text(
        "\n".join(
            json.dumps(
                {
                    "timestamp": f"2026-10-13T00:00:{second}Z",
                    "type": kind,
                    "payload": payload,
                }
            )
            for second, kind, payload in records
        )
    )
    with sqlite3.connect(tmp_path / "state_5.sqlite") as db:
        db.execute(
            "create table threads(id,rollout_path,model,reasoning_effort,originator,source,cwd)"
        )
        db.execute(
            "insert into threads values(?,?,?,?,?,?,?)",
            (
                "thread",
                str(rollout),
                "original",
                "high",
                "Codex Desktop",
                "vscode",
                "/project",
            ),
        )
    with sqlite3.connect(tmp_path / "thread_history_1.sqlite") as db:
        db.execute("create table thread_turns(thread_id,turn_id,duration_ms,status)")
        db.execute(
            "insert into thread_turns values(?,?,?,?)",
            ("thread", "turn", 10000, "completed"),
        )
        db.execute(
            "create table thread_items(thread_id,turn_id,item_type,started_at_ms,completed_at_ms,item_json,rollout_ordinal)"
        )
        db.execute(
            "insert into thread_items values(?,?,?,?,?,?,?)",
            (
                "thread",
                "turn",
                "mcpToolCall",
                (start + 3) * 1000,
                (start + 3.1) * 1000,
                json.dumps(
                    {
                        "server": "fatebridge",
                        "tool": "bazi_career",
                        "durationMs": 100,
                        "arguments": {"secret": secret},
                    }
                ),
                1,
            ),
        )
    with sqlite3.connect(tmp_path / "logs_2.sqlite") as db:
        db.execute("create table logs(thread_id,ts,ts_nanos,target,feedback_log_body)")
        db.executemany(
            "insert into logs values(?,?,?,?,?)",
            [
                (
                    "thread",
                    start + 1,
                    0,
                    "feedback_tags",
                    f'tags_json={{"secret":"{secret}"}}',
                ),
                ("thread", start + 2, 0, "codex_core::stream_events_utils", secret),
                ("thread", start + 5, 0, "feedback_tags", "tags_json={}"),
                ("other", start + 6, 0, "feedback_tags", secret),
            ],
        )
    observed = observer.observe(tmp_path, "thread")
    assert secret not in json.dumps(observed)
    turn = observed["turns"][0]
    assert turn["request_count"] == 2
    assert turn["host_before_first_request_ms"] == 1000
    assert turn["mcp_calls"][0]["started_at_seconds"] == 3
    assert turn["requests"][0]["first_stream_event_after_ms"] == 1000
    assert turn["requests"][1]["first_stream_event_after_ms"] is None
    assert turn["code_calls"][0]["identifiers"] == [
        "tools.mcp__fatebridge__bazi_career"
    ]
    assert turn["remote_queue_ms"] is None
    assert turn["model_processing_ms"] is None
    with observer.connect(tmp_path / "logs_2.sqlite") as connection:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("delete from logs")
    with pytest.raises(ValueError, match="persisted Codex Desktop"):
        observer.observe(tmp_path, "missing")


def test_cached_catalog_negation_and_start_markers_are_not_fake_stage_durations():
    target = "codex_mcp::connection_manager::tool_catalog"
    event = observer.host_event(
        target,
        'using cached MCP tool catalog without waiting for startup server_name="codex_apps" secret=PRIVATE',
    )
    assert event == {
        "kind": "tool_catalog_cache_used_without_startup_wait",
        "server": "codex_apps",
    }
    for _ in range(2):
        marker = observer.host_event(
            "codex_core::session::world_state",
            "building step world state selected_capability_root_count=0",
        )
        assert marker == {
            "kind": "world_state_build_started",
            "selected_capability_root_count": 0,
        }
        assert "duration_ms" not in marker
    assert (
        observer.host_event("unknown", "startup failed server_name=fatebridge") is None
    )
    assert (
        observer.host_event(target, "unrecognized server_name=fatebridge")["kind"]
        == "tool_catalog_event_unclassified"
    )


def test_feature_readback_and_skill_counts_export_only_allowed_metadata():
    body = 'tags_json={"feature.code_mode_prewarm":"true","feature.code_mode_host":true,"authorization":"PRIVATE","feature.skill_search":"PRIVATE","unrelated_feature":true}'
    assert observer.request_flags(body) == {
        "code_mode_host": True,
        "code_mode_prewarm": True,
    }
    assert observer.request_flags('tags_json="PRIVATE"') == {}
    assert observer.request_flags("tags_json={bad") == {}
    assert observer.host_event(
        "codex_skills_extension::render_observability",
        "total_skills=2636 included_skills=200 omitted_skills=2436 budget_limit=5440 credential=999 secret=PRIVATE",
    ) == {
        "kind": "skill_snapshot_rendered",
        "total_skills": 2636,
        "included_skills": 200,
        "omitted_skills": 2436,
        "budget_limit": 5440,
    }
