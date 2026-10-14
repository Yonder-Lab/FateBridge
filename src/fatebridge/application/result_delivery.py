"""Bounded, lossless delivery of large results without recalculating them."""

import hashlib
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fatebridge.utils.errors import ParameterError

DEFAULT_MCP_RESPONSE_CHARS = 8192
PAGE_CHARS = 2048
RETENTION_SECONDS = 3600
MAX_STORED_BYTES = 64 * 1024 * 1024
_RESULT_ID = re.compile(r"[0-9a-f]{48}\Z")


def _invalid(message: str, path: str, code: str) -> ParameterError:
    return ParameterError(message, [{"path": path, "code": code}])


def _json(value: Any, compact: bool = True) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        **({"separators": (",", ":")} if compact else {"indent": 2}),
    )


class ResultStore:
    """Private temporary artifacts shared by transports on the same host."""

    def __init__(self, directory: Optional[Path] = None) -> None:
        self.directory = directory or Path(tempfile.gettempdir()) / (
            f"fatebridge-results-{os.getuid()}"
        )

    def _directory(self) -> Path:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.directory.lstat()
        if self.directory.is_symlink() or info.st_uid != os.getuid():
            raise RuntimeError("Result artifact directory is not owned by this user")
        if info.st_mode & 0o077:
            raise RuntimeError("Result artifact directory must be private")
        return self.directory

    def _prune(self, reserve_bytes: int = 0) -> None:
        records = []
        now = time.time()
        for path in self._directory().glob("*.json"):
            if not _RESULT_ID.fullmatch(path.stem) or path.is_symlink():
                continue
            try:
                info = path.stat()
                if info.st_mtime + RETENTION_SECONDS <= now:
                    path.unlink(missing_ok=True)
                else:
                    records.append((info.st_mtime, info.st_size, path))
            except FileNotFoundError:
                continue
        total = sum(size for _, size, _ in records)
        for _, size, path in sorted(records):
            if total <= MAX_STORED_BYTES - reserve_bytes:
                break
            path.unlink(missing_ok=True)
            total -= size

    def put(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._prune()
        text = _json(payload)
        encoded = text.encode("utf-8")
        if len(encoded) > MAX_STORED_BYTES:
            raise _invalid(
                "结果超过本地交付存储容量，请缩小 fields", "fields", "result_too_large"
            )
        result_id = secrets.token_hex(24)
        path = self._directory() / f"{result_id}.json"
        expires_at = time.time() + RETENTION_SECONDS
        record = _json({"expires_at": expires_at, "payload": payload})
        self._prune(reserve_bytes=len(record.encode("utf-8")))
        staging = path.with_suffix(".pending")
        fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(record)
        staging.replace(path)
        return {
            "mode": "paged",
            "result_id": result_id,
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "total_chars": len(text),
            "total_bytes": len(encoded),
            "expires_at": expires_at,
            "page_chars": PAGE_CHARS,
            "manifest_uri": f"fatebridge://results/{result_id}",
            "first_page_uri": f"fatebridge://results/{result_id}/pages/0",
            "rest_manifest_path": f"/api/results/{result_id}",
            "file_path": str(path),
            "file_payload_path": "payload",
            "available_fields": list(payload),
            "deferred_fields": [],
        }

    def get(self, result_id: str) -> Dict[str, Any]:
        if not _RESULT_ID.fullmatch(result_id):
            raise _invalid("无效结果引用", "result_id", "invalid_result_id")
        path = self._directory() / f"{result_id}.json"
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, encoding="utf-8") as handle:
                record = json.load(handle)
        except (FileNotFoundError, OSError, ValueError):
            raise _invalid(
                "结果引用不存在或已过期", "result_id", "result_unavailable"
            ) from None
        if not isinstance(record, dict) or not isinstance(record.get("payload"), dict):
            raise _invalid("结果引用已损坏", "result_id", "result_unavailable")
        expires_at = record.get("expires_at")
        if not isinstance(expires_at, (int, float)):
            raise _invalid("结果引用已损坏", "result_id", "result_unavailable")
        if expires_at <= time.time():
            path.unlink(missing_ok=True)
            raise _invalid("结果引用已过期，请重新计算", "result_id", "result_expired")
        payload: Dict[str, Any] = record["payload"]
        return payload

    def manifest(self, result_id: str) -> Dict[str, Any]:
        payload = self.get(result_id)
        text = _json(payload)
        return {
            "result_id": result_id,
            "run_metadata": payload.get("run_metadata"),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "total_chars": len(text),
            "page_chars": PAGE_CHARS,
            "file_payload_path": "payload",
            "fields": [
                {
                    "path": name,
                    "first_page_uri": (
                        f"fatebridge://results/{result_id}/fields/{name}/0"
                    ),
                }
                for name in payload
            ],
            "note": (
                "按所需点路径读取字段，也支持数组数字索引；分页 text 是 JSON 文档片段，"
                "完整读取需按 next_offset 拼接并核对 sha256，不要把单页当全文解析。"
            ),
        }

    def page(
        self, result_id: str, offset: int = 0, path: Optional[str] = None
    ) -> Dict[str, Any]:
        if offset < 0:
            raise _invalid("分页 offset 不能为负数", "offset", "invalid_offset")
        value: Any = self.get(result_id)
        if path is not None:
            if len(path) > 1000 or len(path.split(".")) > 64:
                raise _invalid("结果字段路径过长", "path", "invalid_result_path")
            for part in path.split("."):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif (
                    isinstance(value, list)
                    and part.isdecimal()
                    and len(part) < 10
                    and int(part) < len(value)
                ):
                    value = value[int(part)]
                else:
                    raise _invalid("结果字段路径不存在", "path", "unknown_result_path")
        text = _json(value)
        if offset > len(text):
            raise _invalid("分页 offset 超出结果长度", "offset", "invalid_offset")
        end = min(offset + PAGE_CHARS, len(text))
        next_offset = end if end < len(text) else None
        uri_base = (
            f"fatebridge://results/{result_id}/fields/{path}"
            if path is not None
            else f"fatebridge://results/{result_id}/pages"
        )
        return {
            "result_id": result_id,
            "path": path,
            "offset": offset,
            "next_offset": next_offset,
            "next_uri": (
                f"{uri_base}/{next_offset}" if next_offset is not None else None
            ),
            "total_chars": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text": text[offset:end],
        }


RESULT_STORE = ResultStore()


def bound_response(
    payload: Dict[str, Any], response_char_limit: int = 0, *, compact: bool = True
) -> Dict[str, Any]:
    """Return either an intact payload or an explicit lossless delivery envelope."""
    if response_char_limit == 0:
        return payload
    if not 4096 <= response_char_limit <= 65536:
        raise _invalid(
            "response_char_limit 须为 0 或 4096–65536",
            "response_char_limit",
            "invalid_response_limit",
        )
    if len(_json(payload, compact)) <= response_char_limit:
        return payload
    delivery = RESULT_STORE.put(payload)
    output: Dict[str, Any] = {
        "run_metadata": payload.get("run_metadata"),
        "result_delivery": delivery,
    }
    fields = [key for key in payload if key != "run_metadata"]
    delivery["deferred_fields"] = list(fields)
    if len(_json(output, compact)) > response_char_limit:
        raise _invalid(
            "回执超过响应预算，请增大 response_char_limit",
            "response_char_limit",
            "response_limit_too_small",
        )
    priority = ["summary", "analysis_context", "status", "comprehensive_summary"]
    for key in dict.fromkeys([*priority, *fields]):
        if key not in payload or key == "run_metadata":
            continue
        candidate = dict(output)
        candidate[key] = payload[key]
        candidate["result_delivery"] = {
            **delivery,
            "deferred_fields": [
                name for name in delivery["deferred_fields"] if name != key
            ],
        }
        if len(_json(candidate, compact)) <= response_char_limit:
            output = candidate
            delivery = output["result_delivery"]
    return output
