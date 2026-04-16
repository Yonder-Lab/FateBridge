#!/usr/bin/env python3
"""
Benchmark the hottest FateBridge calculation paths.

This script is intentionally non-CI. Run it inside a fully provisioned project
environment to compare median wall time, profiled call counts, and peak memory
for the main conservative optimization targets.
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.services.bazi import calculate_bazi_birth
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.timing import calculate_comprehensive_timing
from fatebridge.utils.helpers import create_person_info


BenchmarkSpec = Tuple[Callable[..., Dict[str, Any]], tuple[Any, ...], dict[str, Any]]


def _build_person():
    return create_person_info(
        birth_year=2028,
        birth_month=4,
        birth_day=6,
        birth_hour=9,
        birth_minute=33,
        name="Benchmark",
        gender="男",
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4667,
    )


def _build_benchmarks() -> Dict[str, BenchmarkSpec]:
    person = _build_person()
    return {
        "calculate_destiny_analysis": (
            calculate_destiny_analysis,
            (person,),
            {},
        ),
        "calculate_bazi_birth": (
            calculate_bazi_birth,
            (person,),
            {
                "analysis_year": 2028,
                "analysis_month": 4,
                "analysis_day": 6,
            },
        ),
        "calculate_comprehensive_timing": (
            calculate_comprehensive_timing,
            (person,),
            {
                "analysis_year": 2028,
                "analysis_month": 4,
                "analysis_day": 6,
                "analysis_hour": 21,
                "analysis_minute": 55,
            },
        ),
    }


def _measure_wall_time(
    func: Callable[..., Dict[str, Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    repeats: int,
) -> list[float]:
    timings_ms: list[float] = []
    for _ in range(repeats):
        started_at = time.perf_counter()
        func(*args, **kwargs)
        timings_ms.append((time.perf_counter() - started_at) * 1000)
    return timings_ms


def _profile_once(
    func: Callable[..., Dict[str, Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Dict[str, Any]:
    profiler = cProfile.Profile()
    tracemalloc.start()
    profiler.enable()
    result = func(*args, **kwargs)
    profiler.disable()
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    if isinstance(result, dict) and "error" in result:
        raise RuntimeError(
            f"{func.__name__} returned an error payload during benchmarking: {result['error']}"
        )

    stats = pstats.Stats(profiler)
    return {
        "total_calls": stats.total_calls,
        "primitive_calls": stats.prim_calls,
        "peak_memory_kib": round(peak_memory / 1024, 2),
    }


def _run_benchmark(
    name: str,
    spec: BenchmarkSpec,
    repeats: int,
) -> Dict[str, Any]:
    func, args, kwargs = spec
    wall_times_ms = _measure_wall_time(func, args, kwargs, repeats)
    profile_stats = _profile_once(func, args, kwargs)

    return {
        "name": name,
        "repeats": repeats,
        "median_wall_time_ms": round(statistics.median(wall_times_ms), 2),
        "min_wall_time_ms": round(min(wall_times_ms), 2),
        "max_wall_time_ms": round(max(wall_times_ms), 2),
        **profile_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark FateBridge hot paths")
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Number of wall-time samples per function",
    )
    args = parser.parse_args()

    print("FateBridge Hot Path Benchmark")
    print(f"Repeats per function: {args.repeats}")
    print("")

    for name, spec in _build_benchmarks().items():
        result = _run_benchmark(name, spec, args.repeats)
        print(result["name"])
        print(f"  median_wall_time_ms: {result['median_wall_time_ms']}")
        print(f"  min_wall_time_ms: {result['min_wall_time_ms']}")
        print(f"  max_wall_time_ms: {result['max_wall_time_ms']}")
        print(f"  total_calls: {result['total_calls']}")
        print(f"  primitive_calls: {result['primitive_calls']}")
        print(f"  peak_memory_kib: {result['peak_memory_kib']}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
