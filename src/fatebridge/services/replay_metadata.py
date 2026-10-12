"""Portable, privacy-conscious execution receipts for the shared registrar."""

import hashlib
import json
import platform
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from fatebridge import __version__
from fatebridge.core.execution_context import CallClock, ExecutionOptions
from fatebridge.core.schema_cache import contract_fingerprint

METADATA_SCHEMA_VERSION = "1.0"


def digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digests(root: Path, pattern: str) -> Dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob(pattern))
        if path.is_file()
    }


@lru_cache(maxsize=1)
def environment_receipt() -> Dict[str, Any]:
    """Snapshot immutable deployment inputs once per process, without Git calls."""
    root = Path(__file__).resolve().parents[1]
    dependencies: Dict[str, Optional[str]] = {}
    for package in (
        "pydantic",
        "kerykeion",
        "pyswisseph",
        "lunardate",
        "python-dateutil",
        "pytz",
    ):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = None
    receipt = {
        "package_version": __version__,
        "python": platform.python_version(),
        "platform": platform.system() + "-" + platform.machine(),
        "dependencies": dependencies,
        "implementation_sha256": digest(_file_digests(root, "*.py")),
        "bundled_data_sha256": digest(_file_digests(root / "data", "*.json")),
    }
    return {**receipt, "environment_sha256": digest(receipt)}


def ephemeris_inventory() -> Dict[str, Any]:
    """Fingerprint configured file inventory, not a claim about files actually used."""
    from fatebridge.core import ephemeris_runtime

    directory = ephemeris_runtime.configured_ephemeris_path()
    return _ephemeris_inventory(directory)


@lru_cache(maxsize=8)
def _ephemeris_inventory(directory: Any) -> Dict[str, Any]:
    files: Dict[str, str] = {}
    if directory:
        # Swiss Ephemeris accepts a platform-delimited search path.
        import os

        for index, item in enumerate(str(directory).split(os.pathsep)):
            root = Path(item)
            for path in sorted(root.glob("*.se1")):
                files[f"{index}/{path.name}"] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    return {
        "scope": "configured_se1_inventory; actual model is reported separately",
        "files": files,
        "sha256": digest(files),
    }


def provenance_values(payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """Small allowlist of non-personal policy facts that survive projection."""
    keys = {
        "ephemeris_model",
        "rule_version",
        "ruleset_version",
        "time_policy",
        "day_ganzhi_strategy",
        "calendar_engine",
        "school_version",
        "policy_version",
        "time_algorithm",
        "engine_precision",
        "ruleset_id",
        "bundle_version",
    }
    found: Dict[str, set[str]] = {}
    queue: List[Any] = [payload]
    while queue:
        current = queue.pop()
        if isinstance(current, dict):
            if isinstance(current.get("ruleset_id"), str) and isinstance(
                current.get("version"), str
            ):
                found.setdefault("ruleset", set()).add(
                    current["ruleset_id"] + "@" + current["version"]
                )
            for key, value in current.items():
                if key in keys and isinstance(value, str):
                    found.setdefault(key, set()).add(value)
                elif isinstance(value, (dict, list)):
                    queue.append(value)
        elif isinstance(current, list):
            queue.extend(current)
    return {key: sorted(values) for key, values in sorted(found.items())}


def execution_receipt(
    spec: Any,
    request: Any,
    result: Dict[str, Any],
    *,
    clock: CallClock,
    options: ExecutionOptions,
    elapsed_ms: float,
    generated_seed: bool,
) -> Dict[str, Any]:
    policy = spec.reproducibility
    as_of = clock.instant.isoformat().replace("+00:00", "Z")
    inputs = request.model_dump(mode="json")

    # Presence of these flags changes fail-loud true-solar behavior even when
    # their default values equal the submitted values. Other explicit defaults
    # have identical semantics, including MCP's expanded signature defaults.
    def solar_presence(model: BaseModel, prefix: str = "") -> List[str]:
        present = []
        for field in type(model).model_fields:
            value = getattr(model, field)
            if isinstance(value, BaseModel):
                present.extend(solar_presence(value, prefix + field + "."))
            elif (
                field.endswith("use_true_solar_time")
                and field in model.model_fields_set
            ):
                present.append(prefix + field)
        return present

    presence = sorted(solar_presence(request))
    input_digest = digest(
        {"tool_key": spec.key, "inputs": inputs, "presence": presence}
    )
    environment = environment_receipt()
    environment = {**environment, "ephemeris": ephemeris_inventory()}
    environment["environment_sha256"] = digest(
        {
            key: value
            for key, value in environment.items()
            if key != "environment_sha256"
        }
    )
    time_defaults = [
        field for field in policy.current_time_fields if inputs.get(field) is None
    ]
    random_used = False
    if spec.key == "sixyao":
        from fatebridge.core.local_techniques.sixyao import needs_random_coin_cast

        random_used = needs_random_coin_cast(inputs)
    overrides = {"seed": inputs["seed"]} if random_used else {}
    body = {key: value for key, value in result.items() if key != "run_metadata"}
    return {
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "package_version": __version__,
        "contract_sha256": contract_fingerprint(spec.request_model, spec.output_model),
        "input_sha256": input_digest,
        "business_output_sha256": digest(body),
        "duration_ms": round(elapsed_ms, 3),
        "effective_time": {"as_of": as_of, "clock_timezones": sorted(clock.reads)},
        "determinism": {
            "uses_current_time": bool(clock.reads)
            and bool(time_defaults or policy.implicit_current_time),
            "current_time_fields_defaulted": time_defaults if clock.reads else [],
            "randomness_used": random_used,
            "seed_generated": generated_seed,
            "replayable_with_receipt": True,
            "scope": "business payload in identical implementation/data/runtime; metadata IDs and duration vary",
        },
        "runtime": environment,
        "provenance": provenance_values(body),
        "replay": {
            "as_of": as_of,
            "overrides": overrides,
            "requires_original_input": True,
        },
        "warnings": (
            (
                ["current_time_frozen"]
                if clock.reads and (time_defaults or policy.implicit_current_time)
                else []
            )
            + (["random_seed_generated"] if generated_seed else [])
        ),
        **(
            {"parent_run_id": options.parent_run_id}
            if options.parent_run_id is not None
            else {}
        ),
    }
