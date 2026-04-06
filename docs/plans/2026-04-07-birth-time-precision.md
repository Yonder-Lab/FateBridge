# Birth Time Precision Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add birth-minute, timezone, and true-solar-time-aware calculation inputs while keeping existing hour-only callers backward compatible.

**Architecture:** Introduce a single normalized birth-time pipeline in `fatebridge.utils.helpers` that converts raw birth inputs into a corrected `datetime` plus metadata. Thread that normalized time through calculation and timing services so four-pillar computation uses corrected local time without duplicating conversion logic in API or MCP layers.

**Tech Stack:** Python 3, Pydantic v2, FastAPI, FastMCP, pytest, python-dateutil

---

### Task 1: Add Regression Tests For Time Normalization

**Files:**
- Create: `tests/test_birth_time_precision.py`
- Read: `fatebridge/utils/helpers.py`
- Read: `fatebridge/core/calendar.py`

**Step 1: Write the failing test**

Add tests for:
- default behavior remains hour-based when minute/timezone options are omitted
- `birth_minute` is accepted and preserved in metadata
- timezone-aware offsets produce different corrected times when longitude is supplied
- true solar time correction can move a birth time across an hour boundary and change the hour pillar

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: FAIL because new fields and normalization helpers do not exist yet

**Step 3: Write minimal implementation**

Add normalization helpers and new `PersonInfo` fields required by the tests.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: PASS

### Task 2: Thread Normalized Time Through Services

**Files:**
- Modify: `fatebridge/services/calculation.py`
- Modify: `fatebridge/services/timing.py`

**Step 1: Write the failing test**

Extend tests to assert service outputs expose corrected time metadata and that hour pillar reflects corrected local time.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: FAIL because services still use raw `birth_hour`

**Step 3: Write minimal implementation**

Replace direct `create_birth_datetime(...)` calls with shared normalization output and return the correction metadata in service responses.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: PASS

### Task 3: Expand REST And MCP Inputs

**Files:**
- Modify: `api.py`
- Modify: `fastmcp_server.py`

**Step 1: Write the failing test**

Add API-level tests for new optional fields and backward compatibility of old payloads.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: FAIL because request models and tool signatures still expose only `birth_hour`

**Step 3: Write minimal implementation**

Add optional `birth_minute`, `birth_timezone`, `birth_longitude`, and `use_true_solar_time` inputs everywhere a person record is constructed.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: PASS

### Task 4: Document New Behavior

**Files:**
- Modify: `README.md`
- Modify: `docs/API.md`

**Step 1: Write the failing test**

No automated doc test. Verify docs by inspection after implementation.

**Step 2: Write minimal implementation**

Update examples, parameter tables, and explain that solar-term month logic remains simplified even with true solar time enabled.

**Step 3: Run verification**

Run:
- `pytest tests/test_birth_time_precision.py -q`
- `pytest -q`

Expected: PASS, or document any pre-existing unrelated failures
