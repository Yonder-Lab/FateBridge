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
