"""Fault injection for real-host evidence: no live models or credentials."""

import importlib.util
import json
import queue
from collections import deque
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "codex_host_experience",
    Path(__file__).resolve().parents[1] / "scripts/experience_codex_host.py",
)
host_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(host_module)


def message(method, **params):
    return {
        "method": method,
        "params": {"threadId": "thread", "turnId": "turn", **params},
    }


@pytest.mark.parametrize(
    "item",
    [
        {"type": "reasoning", "content": "private", "encrypted_content": "secret"},
        {"type": "message", "role": "system", "content": "private"},
        {"type": "custom_tool_call_output", "output": "private token secret"},
    ],
)
def test_raw_diagnostics_retain_no_message_reasoning_or_tool_output(item):
    result = host_module.raw_event_metadata("rawResponseItem/completed", {"item": item})
    encoded = json.dumps(result)
    assert "private" not in encoded and "secret" not in encoded


def test_code_mode_diagnostics_distinguish_discovery_from_execution():
    observation = host_module.TurnObservation()
    for at, code in [
        (10, "text(ALL_TOOLS.filter(t => /career/.test(t.name)))"),
        (17, "text(await tools.mcp__fatebridge__bazi_career({private:'secret'}))"),
    ]:
        metadata = host_module.raw_event_metadata(
            "rawResponseItem/completed",
            {"item": {"type": "custom_tool_call", "name": "exec", "input": code}},
        )
        observation.observe(
            "rawResponseItem/completed", {"safe_metadata": metadata}, at
        )
    events = observation.summary(duration=30)["tool_loading_events"]
    assert "ALL_TOOLS.filter" in events[0]["callees"]
    assert events[1]["tool_identifiers"] == ["mcp__fatebridge__bazi_career"]
    assert events[1]["at_seconds"] == 17
    assert "secret" not in json.dumps(events) and "private" not in json.dumps(events)


def test_raw_response_diagnostic_discards_usage_metadata():
    assert host_module.raw_event_metadata(
        "rawResponse/completed", {"usageMetadata": {"private": "secret"}}
    ) == {"kind": "response_completed"}


def test_read_sanitizes_raw_events_before_queueing():
    host = object.__new__(host_module.Host)
    host.incoming = queue.Queue()
    host.notification_counts = host_module.Counter()
    host.process = type(
        "Process",
        (),
        {
            "stdout": [
                json.dumps(
                    message(
                        "rawResponseItem/completed",
                        item={"type": "reasoning", "content": "private secret"},
                    )
                )
            ],
            "poll": lambda _: 0,
        },
    )()
    host._read()
    result = host.incoming.get_nowait()
    assert result["params"]["safe_metadata"] == {"kind": "reasoning"}
    assert "private" not in json.dumps(result) and "secret" not in json.dumps(result)


@pytest.fixture
def fake_host(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])

    class FakeHost(host_module.Host):
        def __init__(self, notifications):
            self.thread_id = "thread"
            self.pending = []
            self.turn_timeout = 240
            self.idle_timeout = 90
            self.max_reconnects = 3
            self.notifications = deque(notifications)
            self.interrupted = False

        def rpc(self, method, params, timeout=60):
            if method == "turn/start":
                return {"turn": {"id": "turn"}}
            assert method == "turn/interrupt"
            self.interrupted = True
            return {}

        def next(self, timeout):
            if self.notifications and self.notifications[0][0] <= clock[0] + timeout:
                clock[0], value = self.notifications.popleft()
                return value
            clock[0] += timeout
            raise queue.Empty

    return FakeHost, clock


def test_routing_failure_is_not_mislabeled_as_fatebridge_error(fake_host):
    factory, _ = fake_host
    error = {"message": "workspace routing discovery timed out"}
    host = factory(
        [
            (5, message("error", error=error, willRetry=False)),
            (
                6,
                message(
                    "turn/completed",
                    turn={
                        "id": "turn",
                        "status": "failed",
                        "error": error,
                        "items": [],
                    },
                ),
            ),
        ]
    )
    result = host.turn("a user question")
    assert result["status"] == "failed"
    assert result["stages"]["failure_layer"] == "codex_workspace_routing"
    assert result["stages"]["first_model_activity_seconds"] is None
    assert result["stages"]["calls"] == []


def test_reconnection_budget_preserves_failure_without_silent_retry(fake_host):
    factory, _ = fake_host
    host = factory(
        [
            (
                n * 10,
                message(
                    "error", error={"message": f"Reconnecting... {n}/5"}, willRetry=True
                ),
            )
            for n in range(1, 4)
        ]
    )
    result = host.turn("a user question")
    assert result["status"] == "interrupted" and host.interrupted
    assert result["duration_seconds"] == 30
    assert result["stages"]["failure_layer"] == "codex_connection"
    assert len(result["runtime_events"]) == 3


def test_idle_tool_timeout_keeps_partial_answer_and_unknown_tool_state(fake_host):
    factory, _ = fake_host
    host = factory(
        [
            (
                5,
                message(
                    "item/completed",
                    item={"id": "answer", "type": "agentMessage", "text": "正在计算"},
                ),
            ),
            (
                6,
                message(
                    "item/started",
                    item={
                        "id": "mcp",
                        "type": "mcpToolCall",
                        "tool": "bazi_career",
                        "server": "fatebridge",
                    },
                ),
            ),
        ]
    )
    result = host.turn("a user question")
    assert result["duration_seconds"] == 96
    assert result["items"][0]["text"] == "正在计算"
    assert result["stages"]["failure_layer"] == "mcp_inflight_unknown"
    assert result["stages"]["unfinished_mcp_count"] == 1


def test_reasoning_activity_prevents_false_idle_failure_but_is_not_saved(fake_host):
    factory, _ = fake_host
    host = factory(
        [
            (n, message("item/reasoning/textDelta", delta="private reasoning"))
            for n in [30, 60, 85]
        ]
        + [
            (
                100,
                message(
                    "turn/completed",
                    turn={
                        "id": "turn",
                        "status": "completed",
                        "items": [
                            {
                                "id": "r",
                                "type": "reasoning",
                                "text": "private reasoning",
                            }
                        ],
                    },
                ),
            )
        ]
    )
    result = host.turn("a user question")
    assert result["status"] == "completed" and not host.interrupted
    assert "private reasoning" not in json.dumps(result)
    assert result["stages"]["first_model_activity_seconds"] == 30


def test_shared_host_ignores_notifications_from_previous_conversation(fake_host):
    factory, _ = fake_host
    host = factory(
        [
            (
                1,
                message(
                    "item/completed",
                    threadId="previous-thread",
                    item={
                        "id": "previous",
                        "type": "agentMessage",
                        "text": "previous answer",
                    },
                ),
            ),
            (
                2,
                message(
                    "turn/completed",
                    turn={"id": "turn", "status": "completed", "items": []},
                ),
            ),
        ]
    )
    result = host.turn("new conversation")
    assert result["items"] == []
    assert result["stages"]["first_public_output_seconds"] is None


def test_usage_and_final_stream_are_distinct_from_commentary():
    observation = host_module.TurnObservation({"inputTokens": 100, "outputTokens": 20})
    observation.observe(
        "item/started",
        {"item": {"id": "c", "type": "agentMessage", "phase": "commentary"}},
        1,
    )
    observation.observe(
        "item/agentMessage/delta", {"itemId": "c", "delta": "Working"}, 2
    )
    observation.observe(
        "item/agentMessage/delta", {"itemId": "final", "delta": "Answer"}, 12
    )
    observation.observe(
        "item/completed",
        {
            "item": {
                "id": "final",
                "type": "agentMessage",
                "phase": "final_answer",
                "text": "Answer",
            }
        },
        15,
    )
    usage = {
        "tokenUsage": {
            "last": {"inputTokens": 50, "outputTokens": 10},
            "total": {"inputTokens": 150, "outputTokens": 30},
        }
    }
    observation.observe("thread/tokenUsage/updated", usage, 15)
    observation.observe("thread/tokenUsage/updated", usage, 15.1)
    summary = observation.summary(duration=16)
    assert summary["first_public_output_seconds"] == 1
    assert summary["first_final_answer_delta_seconds"] == 12
    assert summary["turn_token_usage"] == {"inputTokens": 50, "outputTokens": 10}
    assert len(summary["token_usage_samples"]) == 1
    assert "Working" not in json.dumps(summary) and "Answer" not in json.dumps(summary)


def test_parallel_mcp_intervals_are_not_double_counted():
    observation = host_module.TurnObservation()
    for identity, begin, end in [("long", 10, 30), ("short", 15, 20)]:
        observation.observe(
            "item/started", {"item": {"id": identity, "type": "mcpToolCall"}}, begin
        )
        observation.observe(
            "item/completed",
            {"item": {"id": identity, "type": "mcpToolCall", "status": "completed"}},
            end,
        )
    summary = observation.summary(duration=40)
    assert summary["time_partition"]["mcp_active_wall_seconds"] == 20
    assert summary["time_partition"]["before_first_mcp_seconds"] == 10
    assert summary["time_partition"]["after_last_mcp_seconds"] == 10


def test_rpc_deadline_does_not_wait_past_remaining_budget(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(host_module.time, "monotonic", lambda: clock[0])
    host = object.__new__(host_module.Host)
    host.sequence = 0
    host.pending = []
    host.rpc_timings = []
    host.send = lambda _: None

    def next_message(timeout):
        clock[0] += timeout
        raise queue.Empty

    host.next = next_message
    with pytest.raises(TimeoutError):
        host.rpc("initialize", {}, timeout=1)
    assert clock[0] == 1


def test_inventory_diagnostics_do_not_block_any_user_turn(monkeypatch, tmp_path):
    events = []

    class StubHost:
        def __init__(self, *args, **kwargs):
            self.boot_started = host_module.time.monotonic()
            self.rpc_timings = []

        def thread(self, cwd):
            return {"id": "thread", "model": "configured model"}

        def turn(self, text):
            events.append("user_turn")
            return {"status": "completed", "duration_seconds": 0, "items": []}

        def inventory(self):
            events.append("inventory")
            return []

        def close(self):
            events.append("close")

    monkeypatch.setattr(host_module, "Host", StubHost)
    monkeypatch.setattr(
        host_module.sys,
        "argv",
        ["experience", "--case", "missing", "--output", str(tmp_path)],
    )
    host_module.main()
    assert events == ["user_turn", "user_turn", "user_turn", "inventory", "close"]
    record = json.loads((tmp_path / "missing.json").read_text())
    assert len(record["turns"]) == 3
    assert record["inventory_scope"].endswith("after all conversations")
