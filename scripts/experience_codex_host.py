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
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from contextlib import nullcontext
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
    "fengshui-facing": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 看看我的书桌朝向。这是虚构体验资料：男，公历2000年12月10日出生，"
            "出生时刻不知道。坐着工作时面朝西，还没有测房屋坐向，也不知道桌子在房屋哪一宫。"
            "桌子不能搬，但椅子和显示器能转向。我应该怎么调整？",
            "我刚才说错了，坐着工作实际面朝东，西边是显示器背面的方向。其余资料不变。"
            "现在还需要调整吗？请按我更正后的情况说。",
        ],
    },
    "fengshui-form": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 看看家里书桌摆得怎么样。虚构体验：我坐下工作时门在右后方，"
            "背后的墙离我约1.5米。我没量罗盘，也不想提供生辰。这样的布局需要改吗？",
            "我确认：正常面朝桌子时看不见门，要转头；门口到座位不在直线上；身后没有紧贴的实体靠背。"
            "桌子很重不能搬，也不允许添镜子。房间和预算都很有限，我现在能做什么？",
            "后来换座位试了一下：现在正面能看到门，仍然不在入口直线上，椅子身后有实体墙。"
            "只是墙依然离座位约1.5米。请重新看这三个确认的条件，别把距离当成固定吉凶标准。",
        ],
    },
    "fengshui-shared": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 看家里共用床的摆法。虚构资料：甲为男，公历1990年5月15日出生；"
            "乙为女，公历1990年6月16日出生，出生时刻均不知。住宅坐坎已确认，"
            "床在房屋北侧宫位已确认，床头朝北。我们两个人同用一张床，不能换房间。"
            "若各自合适的方向不同，怎样给我们一个可执行方案？",
            "不能把其中一个人的判断覆盖另一个。我们也不能搬床，但可以调床头方向。"
            "你有共同匹配方向吗？没有的话请说明需要我们自己权衡什么。",
        ],
    },
    "fengshui-annual": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 看看书桌位置的年度风水。虚构体验：我已确认桌子位于全宅南宫，"
            "朝向东，位置不能改变。想按2026年Adelina Pang的年度规则看看是否有条件性的元素方案。"
            "不用生辰，不要把桌子的朝向当作位置，也别保证能改变健康或财富。",
            "如果到2027年，刚才南宫的物件方案还能直接照用吗？请按2027年看。",
        ],
    },
    "fengshui-conflicting": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 看书桌形态，这是虚构体验：正常坐着面朝显示器，入口在正后方，"
            "没有镜子，我又说正常坐姿不转头就能看见入口。是否需要调整？",
            "我描述错了：入口实际在前方偏左，正常坐姿能看到；不在门口直线上；"
            "身后有实墙。这次都确认了。是否还需要为了风水专门挪动？",
        ],
    },
    "fengshui-unsupported": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 帮我看书柜和餐桌怎么摆。这是虚构体验：书柜在已确认的东宫，"
            "餐桌在已确认的西宫，餐桌的长边朝南北。门在餐桌的左前方，没有正对它。"
            "我想知道是否该为了风水移动这两件家具，能不能用你已有的计算判断？",
        ],
    },
    "fengshui-form-transfer": {
        "scenario": "fengshui",
        "messages": [
            "用 FateBridge 看厨房灶台的室内形态。这是虚构体验：做饭时入口在左边，"
            "正常姿势看得到门，灶台不在入口直线上，操作者身后没有实体墙。"
            "我不知道住宅坐向，不提供生辰，也不知道燃气旋钮能不能算火门。"
            "灶台不能搬动，按已有规则是否需要改？",
            "我重新观察，站着正常做饭看不到入口，得转头才能看见；"
            "不在入口直线上这一项仍然确认。门的具体相对方向我没再量。"
            "不允许加镜子，能否重新判断，并告诉我有哪些条件仍未改善？",
        ],
    },
    "fengshui-bed-transfer": {
        "scenario": "fengshui",
        "messages": [
            "请用 FateBridge 看我的床头摆向，这是虚构体验。女，公历1985年8月23日出生，"
            "出生时间不清楚。床头现在朝西南，整张床在住宅哪一宫和住宅坐向都不知道。"
            "房间狭小，床不能换位置，但可以改变床头摆向。请按已知资料判断我是否需要调整。",
            "我刚才把方向说错了：床头实际朝南，西南是我躺下时看向的位置，不是床头方向。"
            "床的位置与住宅坐向仍不知道，也仍然不能搬床。请按新的资料判断还需不需要改。",
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


def raw_event_metadata(method, params):
    """Allowlist timing/tool identifiers; never retain raw messages or reasoning."""
    if method == "rawResponse/completed":
        return {"kind": "response_completed"}
    if method != "rawResponseItem/completed":
        return None
    item = params.get("item", {})
    kind = item.get("type")
    result = {"kind": kind}
    if kind in {"custom_tool_call", "function_call"}:
        code = item.get("input", item.get("arguments", ""))
        code = code if isinstance(code, str) else ""
        result.update(
            name=item.get("name"),
            code_bytes=len(code.encode()),
            callees=sorted(
                set(re.findall(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(", code))
            ),
            tool_identifiers=sorted(set(re.findall(r"\bmcp__[A-Za-z_0-9]+", code))),
        )
    elif kind in {"custom_tool_call_output", "function_call_output"}:
        result["output_bytes"] = len(
            json.dumps(item.get("output", ""), ensure_ascii=False).encode()
        )
    elif kind == "message":
        result.update(role=item.get("role"), phase=item.get("phase"))
    return result


class TurnObservation:
    """Measure stages without retaining private reasoning or command contents."""

    def __init__(self, previous_tokens=None):
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
        self.previous_tokens = previous_tokens or {}
        self.token_samples = []
        self.agent_messages = {}
        self.reasoning_activity_count = 0
        self.startups = []
        self.tool_loading_events = []

    def observe(self, method, params, elapsed):
        if method in {"rawResponse/completed", "rawResponseItem/completed"}:
            metadata = params.get("safe_metadata")
            if metadata is not None:
                self.tool_loading_events.append({"at_seconds": elapsed, **metadata})
        if method == "thread/tokenUsage/updated":
            usage = params.get("tokenUsage", {})
            # Numeric usage only; no raw API items, prompts or reasoning text.
            sample = {"at_seconds": elapsed}
            for part in ["last", "total"]:
                sample[part] = {
                    k: v
                    for k, v in usage.get(part, {}).items()
                    if isinstance(v, int) and not isinstance(v, bool)
                }
            if (
                not self.token_samples
                or sample["total"] != self.token_samples[-1]["total"]
            ):
                self.token_samples.append(sample)
        if method == "mcpServer/startupStatus/updated":
            self.startups.append(
                {
                    "at_seconds": elapsed,
                    "server": params.get("name", params.get("server")),
                    "status": params.get("status"),
                }
            )
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
        if kind == "reasoning" or method.startswith("item/reasoning/"):
            self.reasoning_activity_count += 1
        if kind == "agentMessage" or method == "item/agentMessage/delta":
            identity = item.get("id", params.get("itemId"))
            entry = self.agent_messages.setdefault(identity, {})
            entry.setdefault("started_seconds", elapsed)
            if method == "item/agentMessage/delta":
                entry.setdefault("first_delta_seconds", elapsed)
                entry["last_delta_seconds"] = elapsed
            if kind == "agentMessage":
                entry["phase"] = item.get("phase")
            if method == "item/completed":
                entry["completed_seconds"] = elapsed
                entry["characters"] = len(item.get("text", ""))
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
                        "result_wire_bytes": len(
                            json.dumps(
                                item.get("result", {}), ensure_ascii=False
                            ).encode()
                        ),
                    }
                )

    def summary(self, error=None, duration=None):
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
        totals = self.token_samples[-1]["total"] if self.token_samples else {}
        intervals = sorted(
            (c["started_seconds"], c["completed_seconds"])
            for c in self.calls
            if c["started_seconds"] is not None
        )
        merged = []
        for begin, end in intervals:
            if merged and begin <= merged[-1][1]:
                merged[-1][1] = max(end, merged[-1][1])
            else:
                merged.append([begin, end])
        final = [
            v for v in self.agent_messages.values() if v.get("phase") == "final_answer"
        ]
        return {
            "first_model_activity_seconds": self.first_model_activity,
            "first_public_output_seconds": self.first_public_output,
            "first_mcp_call_seconds": self.first_mcp_call,
            "reconnect_count": self.reconnects,
            "failure_layer": failure,
            "calls": self.calls,
            "unfinished_mcp_count": len(self.inflight),
            "host_background_commands": self.background,
            "mcp_startup_notifications": self.startups,
            "agent_messages": list(self.agent_messages.values()),
            "first_final_answer_delta_seconds": min(
                (v["first_delta_seconds"] for v in final if "first_delta_seconds" in v),
                default=None,
            ),
            "reasoning_activity_count": self.reasoning_activity_count,
            "token_usage_samples": self.token_samples,
            "tool_loading_events": self.tool_loading_events,
            "turn_token_usage": (
                {k: v - self.previous_tokens.get(k, 0) for k, v in totals.items()}
                if totals
                else None
            ),
            "time_partition": {
                "before_first_mcp_seconds": intervals[0][0] if intervals else None,
                "mcp_active_wall_seconds": round(sum(b - a for a, b in merged), 3),
                "between_mcp_calls_seconds": (
                    round(
                        max(b for _, b in intervals)
                        - intervals[0][0]
                        - sum(b - a for a, b in merged),
                        3,
                    )
                    if intervals
                    else None
                ),
                "after_last_mcp_seconds": (
                    round(duration - max(b for _, b in intervals), 3)
                    if intervals and duration is not None
                    else None
                ),
                "boundary": "Host-observed intervals; non-MCP time includes planning, network and streaming, not pure model compute",
            },
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
        effort=None,
        direct_tools=False,
        trace_tool_loading=False,
    ):
        self.turn_timeout = turn_timeout
        self.idle_timeout = idle_timeout
        self.max_reconnects = max_reconnects
        self.consultation_role = consultation_role
        self.effort = effort
        self.direct_tools = direct_tools
        self.trace_tool_loading = trace_tool_loading
        self.token_totals = {}
        self.startup_events = []
        self.notification_counts = Counter()
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
        if direct_tools:
            args += ["--disable", "code_mode_host"]
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
                {
                    "clientInfo": {"name": "fatebridge-experience", "version": "1.0"},
                    **(
                        {"capabilities": {"experimentalApi": True}}
                        if trace_tool_loading
                        else {}
                    ),
                },
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
                message = json.loads(line)
                message["_received_at"] = time.monotonic()
                metadata = raw_event_metadata(
                    message.get("method"), message.get("params", {})
                )
                if metadata is not None:
                    params = message.get("params", {})
                    # Sanitize before enqueueing, not just before writing reports.
                    message["params"] = {
                        "threadId": params.get("threadId"),
                        "turnId": params.get("turnId"),
                        "safe_metadata": metadata,
                    }
                if "method" in message:
                    self.notification_counts[message["method"]] += 1
                if message.get("method") == "mcpServer/startupStatus/updated":
                    params = message.get("params", {})
                    self.startup_events.append(
                        {
                            "since_host_boot_seconds": round(
                                message["_received_at"] - self.boot_started, 3
                            ),
                            "server": params.get("name"),
                            "status": params.get("status"),
                            "thread_id": params.get("threadId"),
                        }
                    )
                self.incoming.put(message)
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
                **({"experimentalRawEvents": True} if self.trace_tool_loading else {}),
                **(
                    {"developerInstructions": CONSULTATION_ROLE}
                    if self.consultation_role
                    else {}
                ),
                **selection,
            },
        )
        self.thread_id = response["thread"]["id"]
        self.token_totals = {}
        print("Ephemeral conversation ready:", response["model"], flush=True)
        return {
            "id": self.thread_id,
            "model": response["model"],
            "reasoning_effort": response.get("reasoningEffort"),
            "turn_effort_override": self.effort,
            "direct_tools_process_override": self.direct_tools,
            "trace_tool_loading": self.trace_tool_loading,
            "instruction_sources": response.get("instructionSources", []),
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
            {
                "threadId": self.thread_id,
                "input": [{"type": "text", "text": text}],
                **({"effort": self.effort} if getattr(self, "effort", None) else {}),
            },
        )
        turn_id = response["turn"]["id"]
        public = {}
        requests = []
        observation = TurnObservation(getattr(self, "token_totals", {}))
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
            if params.get("threadId") not in [None, self.thread_id] or params.get(
                "turnId"
            ) not in [None, turn_id]:
                continue
            observation.observe(
                method,
                params,
                round(message.get("_received_at", time.monotonic()) - started, 3),
            )
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
                if observation.token_samples:
                    self.token_totals = observation.token_samples[-1]["total"]
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
                    "stages": observation.summary(
                        turn.get("error"), time.monotonic() - started
                    ),
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
            "stages": observation.summary(stop_error, time.monotonic() - started),
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
        "--trace-tool-loading",
        action="store_true",
        help="Opt into native raw events but retain only timing, call identifiers and sizes",
    )
    parser.add_argument(
        "--direct-tools",
        action="store_true",
        help="A/B native direct tool calling versus code_mode_host; subprocess only",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Use a real consultation workspace and its normal instructions/config; otherwise use a temporary directory",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high"],
        help="Compare per-conversation reasoning effort on the same model; no global setting changes",
    )
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
    workspace = (
        nullcontext(str(args.cwd.resolve()))
        if args.cwd
        else tempfile.TemporaryDirectory(prefix="fatebridge-codex-user-")
    )
    with workspace as cwd:
        host = Host(
            scenario,
            cwd,
            registered=args.registered,
            consultation_role=args.consultation_role,
            effort=args.effort,
            direct_tools=args.direct_tools,
            trace_tool_loading=args.trace_tool_loading,
        )
        failed = False
        records = []
        try:
            for key in keys:
                case = CASES[key]
                case_cwd = cwd if args.cwd else str(Path(cwd) / key)
                Path(case_cwd).mkdir(exist_ok=True)
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
                record["mcp_startup_events"] = list(getattr(host, "startup_events", []))
                record["notification_counts"] = dict(
                    getattr(host, "notification_counts", {})
                )
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
