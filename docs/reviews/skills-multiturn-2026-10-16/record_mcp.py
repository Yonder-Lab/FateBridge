#!/usr/bin/env python3
"""Append raw MCP observations. This does not establish that observations are authentic."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def deliveries(response):
    """Inspect only response envelopes for existing result-delivery references."""
    found = []
    def visit(value):
        if isinstance(value, dict):
            delivery = value.get("result_delivery")
            if isinstance(delivery, dict):
                found.append(delivery)
            for key, child in value.items():
                if key == "text" and isinstance(child, str):
                    try:
                        visit(json.loads(child))
                    except (ValueError, RecursionError):
                        pass
                elif isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(response)
    return found


def preserve_deferred(response, directory, record_number):
    snapshots = []
    seen = set()
    roots = [Path(x).resolve() for x in (tempfile.gettempdir(), "/tmp", "/var/tmp")]
    for delivery in deliveries(response):
        for key in ("file_path",):
            source = delivery.get(key)
            if not isinstance(source, str) or source in seen:
                continue
            seen.add(source)
            item = {"source_key": key, "source_path": source}
            snapshots.append(item)
            try:
                path = Path(source)
                if not path.is_absolute():
                    raise ValueError("reference is not an absolute local path")
                resolved = path.resolve(strict=True)
                if not any(resolved == root or root in resolved.parents for root in roots):
                    raise ValueError("reference is outside local temporary directories")
                descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                with os.fdopen(descriptor, "rb") as reader:
                    if not stat.S_ISREG(os.fstat(reader.fileno()).st_mode):
                        raise ValueError("reference is not a regular local file")
                    destination_dir = directory / "audit-deferred"
                    destination_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                    for suffix in range(1, 1000000):
                        destination = destination_dir / ("%06d-%03d-%d.bin" % (record_number, len(snapshots), suffix))
                        try:
                            out_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                            break
                        except FileExistsError:
                            continue
                    else:
                        raise RuntimeError("could not reserve deferred snapshot")
                    digest, size = hashlib.sha256(), 0
                    with os.fdopen(out_fd, "wb") as writer:
                        while True:
                            chunk = reader.read(1024 * 1024)
                            if not chunk:
                                break
                            writer.write(chunk)
                            digest.update(chunk)
                            size += len(chunk)
                        writer.flush()
                        os.fsync(writer.fileno())
                item.update(status="copied_local_file", filename=str(destination), sha256=digest.hexdigest(), bytes=size)
            except (OSError, ValueError, RuntimeError) as error:
                item.update(status="unavailable_local_reference", reason=str(error), limitation="May be remote, expired, inaccessible, or outside the permitted temporary paths; this is not evidence of successful retrieval.")
    return snapshots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--record-json", help="one complete JSON object; otherwise read stdin")
    parser.add_argument("--self-test-label", help="marks synthetic fixture records, never real tool evidence")
    args = parser.parse_args()
    raw = args.record_json if args.record_json is not None else sys.stdin.read()
    record = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-JSON number: " + value)))
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    kind = record.get("kind", "tool")
    if "response" not in record or not isinstance(record.get("arguments"), dict):
        raise ValueError("record requires object arguments and unmodified response")
    if kind == "tool":
        if not re.fullmatch(r"mcp__fatebridge__[A-Za-z0-9_]+", record.get("tool", "")):
            raise ValueError("tool must have the mcp__fatebridge__ prefix")
    elif kind == "resource":
        if not isinstance(record.get("resource_uri"), str) or not record["resource_uri"]:
            raise ValueError("resource records require resource_uri")
        if not isinstance(record.get("reader"), str) or not record["reader"]:
            raise ValueError("resource records require reader provenance")
    else:
        raise ValueError("kind must be tool or resource")
    directory = Path(args.directory).expanduser().absolute()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # O_EXCL is the append boundary; concurrent writers retry and never replace a file.
    existing = [int(p.stem) for p in directory.glob("[0-9]*.json") if p.stem.isdigit()]
    number = max(existing, default=0) + 1
    while True:
        filename = directory / ("%06d.json" % number)
        try:
            descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            break
        except FileExistsError:
            number += 1
    payload_sha = hashlib.sha256(canonical(record)).hexdigest()
    metadata = {
        "schema": "fatebridge_raw_mcp_observation_v1",
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "record_sha256": payload_sha,
        "record_sha256_format": "UTF-8 JSON, ensure_ascii=false, sort_keys=true, separators=(',',':'), allow_nan=false",
        "raw_input_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "authenticity": "Caller-supplied observation; the recorder does not attest tool execution.",
        "self_test_label": args.self_test_label,
        "deferred_snapshots": preserve_deferred(record["response"], directory, number),
    }
    # Embed the original input JSON verbatim, including all response content fields.
    encoded = ("{\"metadata\":" + json.dumps(metadata, ensure_ascii=False, separators=(",", ":")) + ",\"record\":" + raw + "}\n").encode("utf-8")
    with os.fdopen(descriptor, "wb") as writer:
        writer.write(encoded)
        writer.flush()
        os.fsync(writer.fileno())
    print(json.dumps({"filename": str(filename), "sha256": hashlib.sha256(encoded).hexdigest(), "record_sha256": payload_sha, "deferred_copied": sum(x["status"] == "copied_local_file" for x in metadata["deferred_snapshots"]), "deferred_unavailable": sum(x["status"] != "copied_local_file" for x in metadata["deferred_snapshots"]), "self_test_label": args.self_test_label}, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("record_mcp: " + type(error).__name__ + ": " + str(error), file=sys.stderr)
        sys.exit(1)
