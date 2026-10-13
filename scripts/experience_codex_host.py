"""Real, ephemeral, multi-turn Codex conversations against FateBridge MCP.

Requires an authenticated local Codex CLI. Uses the user's configured model;
does not change user configuration or supply tool choices/expected answers to
the model. Existing MCP/plugin configuration is preserved.
Public messages and actual tool calls are saved; reasoning streams are omitted.
"""

import argparse
import hashlib
import json
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import fatebridge
from fatebridge.diagnostics import resolve_codex_cli

CASES = {
    "career": {
        "scenario": "onda-shiye",
        "messages": [
            "请用 FateBridge 帮我看看事业。我最近想换工作，也在考虑自己做点生意。"
            "以下是虚构体验资料：男，公历1990年5月15日上午10点30分，出生于北京，"
            "时区Asia/Shanghai，经度116.4074，纬度39.9042。"
            "以2026年10月12日为分析日期。请用普通人能懂的话讲，别列一堆术语。",
            "那我是不是现在就应该辞职？你刚才说的哪些有计算依据，哪些还需要看现实情况？",
        ],
    },
    "missing": {
        "scenario": "onda-shiye",
        "messages": [
            "用 FateBridge 帮我看一下最近换工作的事。虚构资料：男，公历1990年5月15日，"
            "北京出生，出生时间我没写。现在是2026年10月12日。",
            "我查到了，是上午10点30分，北京当地时间。",
            "如果我其实只知道上午、不知道几点，还能直接用刚才的结果吗？",
        ],
    },
    "invalid": {
        "scenario": "onda-shiye",
        "messages": [
            "用 FateBridge 看事业。虚构资料：男，公历1990年2月30日上午10点30分，"
            "北京出生，时区Asia/Shanghai。分析日期2026年10月12日。",
            "我打错了，是公历1990年5月15日上午10点30分，其余一样。",
        ],
    },
    "relationship": {
        "scenario": "onda-yuanfen",
        "messages": [
            "请用 FateBridge 看看我们两个人相处需要注意什么。都是虚构资料："
            "甲，男，公历1990年5月15日10:30，北京；乙，女，公历1992年3月2日08:00，北京。"
            "两人都是Asia/Shanghai当地时间，经度116.4074、纬度39.9042。"
            "请讲得直白一点，别把分数说成成功概率。",
            "不同规则的分数看起来不一样，到底该相信哪个？能不能据此说我们一定合适？",
        ],
    },
    "fengshui": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 帮我看看家里布局吧。我想知道沙发和床放在哪边比较好，"
            "现在还没有测量朝向，也没有提供户型图。这是虚构体验。",
        ],
    },
}

CONSULTATION_ROLE = (
    "这是独立的 FateBridge 用户咨询，不是仓库开发或安装排错任务。"
    "本次人物资料均虚构且由当前用户消息提供，不需要仓库、历史聊天或记忆中的个人资料。"
    "使用已连接 MCP 的参数 Schema 和工具描述；不要为咨询搜索代码目录。"
    "缺少影响计算的信息就先简短询问，不能猜测或使用示例代替。"
    "普通咨询首轮先简短回答关键问题和依据；用户需要深入时再扩展。"
    "区分工具计算、传统规则和现实建议，不用命盘替用户决定辞职或关系成败。"
)


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def public_item(item):
    """Keep host activity visible without exporting unrelated local file output."""
    if item["type"] == "commandExecution":
        return {
            "type": item["type"],
            "id": item["id"],
            "status": item.get("status"),
            "exitCode": item.get("exitCode"),
            "content_omitted": "Unrelated host background command and local output",
        }
    return item


class TurnObservation:
    """Measure stages without retaining private reasoning or command contents."""

    def __init__(self):
        self.first_model_activity = None
        self.first_public_output = None
        self.first_mcp_call = None
        self.last_activity = 0.0
        self.reconnects = 0
        self.events = []
        self.inflight = {}
        self.calls = []
        self.background = []
        self.backend_error = None

    def observe(self, method, params, elapsed):
        if method == "error":
            message = params.get("error", {}).get("message", "")
            reconnect = message.startswith("Reconnecting")
            self.reconnects += int(reconnect)
            if "workspace routing" in message.lower():
                self.backend_error = "codex_workspace_routing"
            self.events.append(
                {
                    "at_seconds": elapsed,
                    "message": message,
                    "will_retry": params.get("willRetry"),
                }
            )
        item = params.get("item", {})
        kind = item.get("type")
        if method.startswith("item/") and (
            kind in {"agentMessage", "reasoning", "mcpToolCall", "commandExecution"}
            or method.lower().endswith("delta")
        ):
            self.last_activity = elapsed
            if self.first_model_activity is None:
                self.first_model_activity = elapsed
        if kind == "agentMessage" or method == "item/agentMessage/delta":
            if self.first_public_output is None:
                self.first_public_output = elapsed
        if kind == "commandExecution" and method == "item/started":
            command = item.get("command", "")
            self.background.append(
                {
                    "at_seconds": elapsed,
                    "category": (
                        "memory" if "/memories/" in command else "other_host_command"
                    ),
                }
            )
        if kind == "mcpToolCall":
            if self.first_mcp_call is None:
                self.first_mcp_call = elapsed
            if method == "item/started":
                self.inflight[item["id"]] = elapsed
            elif method == "item/completed":
                self.calls.append(
                    {
                        "server": item.get("server"),
                        "tool": item.get("tool"),
                        "started_seconds": self.inflight.pop(item["id"], None),
                        "completed_seconds": elapsed,
                        "duration_ms": item.get("durationMs"),
                        "status": item.get("status"),
                    }
                )

    def summary(self, error=None):
        message = str((error or {}).get("message", ""))
        failure = self.backend_error
        if "workspace routing" in message.lower():
            failure = "codex_workspace_routing"
        elif failure is None and error:
            if self.reconnects:
                failure = "codex_connection"
            elif self.inflight:
                failure = "mcp_inflight_unknown"
            else:
                failure = "codex_turn_incomplete"
        return {
            "first_model_activity_seconds": self.first_model_activity,
            "first_public_output_seconds": self.first_public_output,
            "first_mcp_call_seconds": self.first_mcp_call,
            "reconnect_count": self.reconnects,
            "failure_layer": failure,
            "calls": self.calls,
            "unfinished_mcp_count": len(self.inflight),
            "host_background_commands": self.background,
        }


class Host:
    def __init__(
        self,
        scenario,
        cwd,
        registered=False,
        turn_timeout=240,
        idle_timeout=90,
        max_reconnects=3,
        consultation_role=False,
    ):
        self.turn_timeout = turn_timeout
        self.idle_timeout = idle_timeout
        self.max_reconnects = max_reconnects
        self.consultation_role = consultation_role
        self.rpc_timings = []
        self.model_selection = None
        self.boot_started = time.monotonic()
        codex = resolve_codex_cli()["path"]
        self.binary = codex
        self.version = subprocess.check_output([codex, "--version"], text=True).strip()
        # Bound native retries in this audit process only; never edit user settings.
        args = [
            codex,
            "app-server",
            "--stdio",
            "--disable",
            "unbounded_connection_retries",
        ]
        overrides = {
            "mcp_servers.fatebridge.command": sys.executable,
            "mcp_servers.fatebridge.args": ["-m", "fatebridge.mcp_server"],
            "mcp_servers.fatebridge.enabled": True,
            "mcp_servers.fatebridge.startup_timeout_sec": 30,
            "mcp_servers.fatebridge.tool_timeout_sec": 60,
            "mcp_servers.fatebridge.env.FATEBRIDGE_MCP_FAMILIES": "",
            "mcp_servers.fatebridge.env.FATEBRIDGE_MCP_SCENARIOS": scenario,
        }
        for key, value in ({} if registered else overrides).items():
            # JSON strings/arrays/bools are valid TOML values; argv is not shell.
            args += ["-c", f"{key}={json.dumps(value, ensure_ascii=False)}"]
        self.log = tempfile.TemporaryFile(mode="w+")
        self.process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log,
            cwd=cwd,
            text=True,
            bufsize=1,
        )
        self.incoming = queue.Queue()
        self.sequence = 0
        self.pending = []
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self.rpc(
                "initialize",
                {"clientInfo": {"name": "fatebridge-experience", "version": "1.0"}},
            )
        except Exception:
            self.log.seek(0)
            log = self.log.read()
            save(
                Path(tempfile.gettempdir(), "fatebridge-codex-host-startup.json"),
                {
                    "known_signals": {
                        s: log.count(s)
                        for s in [
                            "workspace routing discovery timed out",
                            "connection reset",
                            "timed out",
                        ]
                    },
                    "raw_stderr_omitted": True,
                },
            )
            self.close()
            raise
        self.send({"method": "initialized", "params": {}})
        print("Codex runtime initialized", flush=True)

    def _read(self):
        for line in self.process.stdout:
            try:
                self.incoming.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        self.incoming.put({"hostExited": self.process.poll()})

    def send(self, message):
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def next(self, timeout=45):
        message = self.incoming.get(timeout=timeout)
        if "hostExited" in message:
            raise RuntimeError("Codex app server exited")
        if "id" in message and "method" in message:
            # Never silently invent answers to a real user question/approval.
            self.send(
                {
                    "id": message["id"],
                    "error": {
                        "code": -32601,
                        "message": "Use a plain assistant message for this user question",
                    },
                }
            )
        return message

    def rpc(self, method, params, timeout=60):
        started = time.monotonic()
        self.sequence += 1
        call_id = self.sequence
        self.send({"id": call_id, "method": method, "params": params})
        deadline = started + timeout
        while time.monotonic() < deadline:
            try:
                message = self.next(
                    timeout=min(10, max(0.001, deadline - time.monotonic()))
                )
            except queue.Empty:
                continue
            if message.get("id") == call_id and "method" not in message:
                self.rpc_timings.append(
                    {
                        "method": method,
                        "duration_seconds": round(time.monotonic() - started, 3),
                    }
                )
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message["result"]
            self.pending.append(message)
        raise TimeoutError(method)

    def thread(self, cwd):
        print("Checking runtime model availability", flush=True)
        if self.model_selection is None:
            models = self.rpc("model/list", {})["data"]
            self.configured_model = self.rpc("config/read", {"includeLayers": False})[
                "config"
            ].get("model")
            if self.configured_model and self.configured_model not in {
                row["model"] for row in models
            }:
                raise RuntimeError(
                    "Configured model unavailable in this CLI; check doctor codex.cli instead of silently changing models"
                )
            self.model_selection = {}
        selection = self.model_selection
        response = self.rpc(
            "thread/start",
            {
                "cwd": cwd,
                "ephemeral": True,
                "sandbox": "read-only",
                "approvalPolicy": "never",
                **(
                    {"developerInstructions": CONSULTATION_ROLE}
                    if self.consultation_role
                    else {}
                ),
                **selection,
            },
        )
        self.thread_id = response["thread"]["id"]
        print("Ephemeral conversation ready:", response["model"], flush=True)
        return {
            "id": self.thread_id,
            "model": response["model"],
            "reasoning_effort": response.get("reasoningEffort"),
            "ephemeral": True,
            "configured_model": self.configured_model,
            "model_selection": (
                "configured model"
                if not selection
                else "native model/list default; configured model unavailable"
            ),
            "cli_path": self.binary,
            "cli_version": self.version,
            "process_id": self.process.pid,
            "role": (
                "explicit self-contained consultation"
                if self.consultation_role
                else "host defaults"
            ),
            "native_unbounded_retries": False,
            "limits": {
                "turn_seconds": self.turn_timeout,
                "idle_seconds": self.idle_timeout,
                "max_reconnects": self.max_reconnects,
            },
            "mcp_server_sha256": hashlib.sha256(
                (Path(fatebridge.__file__).parent / "mcp_server.py").read_bytes()
            ).hexdigest(),
        }

    def inventory(self):
        response = self.rpc("mcpServerStatus/list", {"threadId": self.thread_id})
        return [
            {
                "name": row["name"],
                "tool_names": sorted(row["tools"]),
                "resources": [r["uri"] for r in row["resources"]],
                "server_info": row.get("serverInfo"),
                "tool_schema_wire_bytes": len(
                    json.dumps(row["tools"], ensure_ascii=False).encode()
                ),
            }
            for row in response["data"]
        ]

    def turn(self, text):
        started = time.monotonic()
        response = self.rpc(
            "turn/start",
            {"threadId": self.thread_id, "input": [{"type": "text", "text": text}]},
        )
        turn_id = response["turn"]["id"]
        public = {}
        requests = []
        observation = TurnObservation()
        stop_error = None
        while time.monotonic() - started < self.turn_timeout:
            elapsed = round(time.monotonic() - started, 3)
            if elapsed - observation.last_activity > self.idle_timeout:
                stop_error = {
                    "message": "Codex turn exceeded idle deadline",
                    "source": "audit_idle_limit",
                }
                break
            if observation.reconnects >= self.max_reconnects:
                stop_error = {
                    "message": "Codex connection retry budget exhausted",
                    "source": "audit_retry_limit",
                }
                break
            try:
                remaining = min(
                    self.turn_timeout - elapsed,
                    self.idle_timeout - (elapsed - observation.last_activity),
                )
                message = (
                    self.pending.pop(0)
                    if self.pending
                    else self.next(timeout=max(0.001, min(20, remaining)))
                )
            except queue.Empty:
                print("Waiting for real Codex turn...", flush=True)
                continue
            except (RuntimeError, BrokenPipeError, OSError) as exc:
                stop_error = {
                    "message": "Codex host transport closed",
                    "source": type(exc).__name__,
                }
                break
            method = message.get("method", "")
            params = message.get("params", {})
            if (
                params.get("threadId", self.thread_id) != self.thread_id
                or params.get("turnId", turn_id) != turn_id
            ):
                continue
            observation.observe(method, params, round(time.monotonic() - started, 3))
            if method == "error":
                print(
                    "Codex runtime error:",
                    params.get("error", {}).get("message"),
                    flush=True,
                )
            if method == "item/completed":
                item = params["item"]
                if item["type"] != "reasoning":
                    public[item["id"]] = public_item(item)
                    if item["type"] == "mcpToolCall":
                        print("MCP:", item.get("tool"), item.get("status"), flush=True)
            if "id" in message and "method" in message:
                requests.append({"method": method, "params": params})
            if method == "turn/completed" and params["turn"]["id"] == turn_id:
                turn = params["turn"]
                for item in turn.get("items", []):
                    if item["type"] != "reasoning":
                        public[item["id"]] = public_item(item)
                return {
                    "prompt": text,
                    "id": turn_id,
                    "status": turn["status"],
                    "error": turn.get("error"),
                    "duration_seconds": round(time.monotonic() - started, 2),
                    "items": list(public.values()),
                    "client_requests": requests,
                    "runtime_events": observation.events,
                    "stages": observation.summary(turn.get("error")),
                }
        stop_error = stop_error or {
            "message": "Codex turn exceeded total deadline",
            "source": "audit_total_limit",
        }
        try:
            self.rpc(
                "turn/interrupt",
                {"threadId": self.thread_id, "turnId": turn_id},
                timeout=8,
            )
        except (TimeoutError, RuntimeError) as exc:
            stop_error["interrupt_error"] = type(exc).__name__
        return {
            "prompt": text,
            "id": turn_id,
            "status": "interrupted",
            "error": stop_error,
            "duration_seconds": round(time.monotonic() - started, 2),
            "items": list(public.values()),
            "client_requests": requests,
            "runtime_events": observation.events,
            "stages": observation.summary(stop_error),
        }

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, action="append")
    parser.add_argument(
        "--registered",
        action="store_true",
        help="Read the saved Codex MCP configuration without FateBridge overrides",
    )
    parser.add_argument(
        "--consultation-role",
        action="store_true",
        help="A/B a task-scoped consultation role; does not change Codex global settings",
    )
    parser.add_argument(
        "--all-tools",
        action="store_true",
        help="Expose all FateBridge tools instead of scenario profiles",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    keys = args.case or list(CASES)
    scenario = (
        ""
        if args.all_tools
        else ",".join(dict.fromkeys(CASES[key]["scenario"] for key in keys))
    )
    # Desktop clients keep one host alive. Repeated cold hosts add routing/auth
    # discovery and plugin startup; they are a separate stress test, not normal UX.
    with tempfile.TemporaryDirectory(prefix="fatebridge-codex-user-") as cwd:
        host = Host(
            scenario,
            cwd,
            registered=args.registered,
            consultation_role=args.consultation_role,
        )
        failed = False
        records = []
        try:
            for key in keys:
                case = CASES[key]
                case_cwd = str(Path(cwd) / key)
                Path(case_cwd).mkdir()
                record = {
                    "case": key,
                    "scenario": None if args.registered else scenario,
                    "registered_config": args.registered,
                    "host_lifecycle": "shared process; independent ephemeral conversations",
                    "turns": [],
                }
                records.append(record)
                try:
                    record["host"] = host.thread(case_cwd)
                    save(args.output / f"{key}.json", record)
                    for text in case["messages"]:
                        print(
                            f"Starting {key} turn {len(record['turns']) + 1}",
                            flush=True,
                        )
                        turn = host.turn(text)
                        record["turns"].append(turn)
                        save(args.output / f"{key}.json", record)
                        print(
                            f"Completed: {turn['status']} in {turn['duration_seconds']}s",
                            flush=True,
                        )
                        if len(records) == 1 and len(record["turns"]) == 1:
                            record["first_reply_since_host_start_seconds"] = round(
                                time.monotonic() - host.boot_started, 3
                            )
                        if turn["status"] != "completed":
                            failed = True
                            break
                finally:
                    record["rpc_timings"] = list(host.rpc_timings)
                    save(args.output / f"{key}.json", record)
                if failed:
                    break
            # Diagnostic inventory is outside every user turn, including followups.
            # Its failure must not erase successful conversations or change their status.
            try:
                inventory = host.inventory()
            except (RuntimeError, TimeoutError, queue.Empty) as exc:
                inventory = None
                inventory_error = type(exc).__name__
            for record in records:
                record["inventory"] = inventory
                record["inventory_scope"] = (
                    "shared-host snapshot after all conversations"
                )
                if inventory is None:
                    record["inventory_error"] = inventory_error
                record["rpc_timings"] = list(host.rpc_timings)
                save(args.output / f"{record['case']}.json", record)
        finally:
            host.close()
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
