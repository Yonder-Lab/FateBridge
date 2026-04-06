# Address Resolution Enhancement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Broaden offline `birth_place` parsing so full-form Chinese addresses resolve more often without requiring manual longitude input.

**Architecture:** Replace the current tiny keyword map with a structured offline location catalog that supports aliases, specificity ranking, and province-level fallback. Keep the normalization entrypoint unchanged so API and service layers continue to call one helper while gaining richer address parsing behavior.

**Tech Stack:** Python 3, Pydantic v2, pytest

---

### Task 1: Add failing tests for broader address parsing

**Files:**
- Modify: `tests/test_birth_time_precision.py`
- Read: `fatebridge/utils/helpers.py`

**Step 1: Write the failing test**

Add tests for:
- full-form Chinese addresses like `浙江省宁波市海曙区...` resolving via `birth_place`
- specificity selection preferring city over province when both appear
- province-level fallback still working for unknown city details

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: FAIL because the current offline table is too small and only does naive substring matching

**Step 3: Write minimal implementation**

Introduce structured entries plus ranked alias matching.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_birth_time_precision.py -q`
Expected: PASS

### Task 2: Document offline parsing scope

**Files:**
- Modify: `README.md`
- Modify: `docs/API.md`

**Step 1: Update docs**

Clarify that:
- full-form Chinese addresses now use broader offline matching
- parsing is still offline and approximate, not street-level network geocoding
- explicit `birth_longitude` remains the highest-precision option

**Step 2: Run verification**

Run:
- `pytest tests/test_birth_time_precision.py -q`
- `pytest -q`

Expected: PASS
