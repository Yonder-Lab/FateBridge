# FateBridge Gap Remediation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the highest-value gaps identified in the `horosa-skill` comparison audit across algorithm depth, performance, developer ergonomics, Agent usability, and documentation accuracy.

**Architecture:** Keep FateBridge's current lightweight Python-first structure, but reduce duplicated surface definitions, make standalone predictive tools compute only the requested technique, clarify which metaphysics methods are exact vs approximate vs placeholder, and add the missing execution metadata needed for Agent workflows.

**Tech Stack:** Python 3, FastAPI, FastMCP, Pydantic v2, pytest

---

## Priority Summary

### P0

- fix stale and contradictory documentation
- add explicit capability matrix for exact / approximate / placeholder methods
- remove the biggest predictive recomputation hotspot
- expand API/MCP parity coverage beyond the current small subset

### P1

- reduce API/MCP duplication with a shared tool registry
- improve relative-chart depth and eliminate placeholder branches where feasible
- add basic run metadata for Agent workflows

### P2

- add a dispatch layer for natural-language tool routing
- add trace / artifact / benchmark infrastructure
- consider a packaged offline runtime strategy if FateBridge needs multi-runtime parity

---

### Task 1: Repair Documentation Drift

**Files:**
- Modify: `README.md`
- Modify: `docs/API.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DEVELOPMENT.md`
- Modify: `docs/GETTING_STARTED.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Modify: `docs/README.md`

**Step 1: Audit stale references**

Remove or rewrite references to:
- the removed in-repo web frontend
- the removed logic aggregation layer
- the obsolete standalone fixes log
- the legacy default port that no longer matches current runtime defaults

**Step 2: Update the real surface area**

Document the current backend-only structure and the actual exposed endpoint/tool inventory, especially:
- standalone western timing endpoints
- export helpers
- knowledge helpers
- Chinese metaphysics helpers

**Step 3: Add an explicit compatibility note**

Document which areas are:
- implemented
- approximate / offline lightweight
- placeholder / contract-compatible only

**Step 4: Verify by inspection**

Run a targeted `rg` check over the edited primary docs and environment template.

Expected: no stale references remain unless intentionally preserved and explained

---

### Task 2: Publish A Capability Matrix

**Files:**
- Create: `docs/ALGORITHM_COVERAGE.md`
- Read: `fastmcp_server.py`
- Read: `fatebridge/core/astrology.py`
- Read: `fatebridge/core/astrology_predictive.py`
- Read: `fatebridge/core/phase2_local.py`
- Read: `fatebridge/core/almanac.py`

**Step 1: Enumerate methods by domain**

Include:
- astro core charts
- relative / derived charts
- predictive timing systems
- Chinese metaphysics mainline tools
- Phase 2 local techniques
- export / knowledge helpers

**Step 2: Add execution-quality status**

For each method, mark one of:
- `Implemented`
- `Approximate`
- `Placeholder`
- `Excluded`

**Step 3: Record acceptance notes**

Clarify important caveats such as:
- lightweight offline chart approximations in `fatebridge.core.astrology`
- predictive methods depending on `kerykeion` / Swiss Ephemeris
- relative-chart modes that still degrade to placeholder output

**Step 4: Verify**

Manual review only. The matrix should match the current code, not aspirational future scope.

---

### Task 3: Stop Full Predictive Bundle Recomputations

**Files:**
- Modify: `fatebridge/services/western_timing_tools.py`
- Modify: `fatebridge/services/western_timing.py`
- Modify: `fatebridge/core/astrology_predictive.py`
- Modify: `tests/test_western_timing_tools.py`

**Step 1: Write the failing test**

Add a regression test proving that a standalone tool like `solarreturn` does not need to calculate unrelated sections such as:
- primary directions
- zodiacal releasing
- firdaria / decennials

The test can use monkeypatching or counters to ensure only the requested builder runs.

**Step 2: Run test to verify it fails**

Run:
- `pytest tests/test_western_timing_tools.py -q`

Expected: FAIL because `_calculate_tool()` currently calls the full `calculate_western_timing_analysis(...)`

**Step 3: Write minimal implementation**

Introduce a selective predictive execution path so standalone tools only build:
- their own payload
- shared natal/context dependencies
- only the snapshot sections they actually need

**Step 4: Run verification**

Run:
- `pytest tests/test_western_timing_tools.py -q`
- `pytest tests/test_western_timing.py -q`
- `pytest -q --durations=15`

Expected: PASS, with the slowest standalone timing tests materially improved

---

### Task 4: Expand API And MCP Parity Tests

**Files:**
- Modify: `tests/test_api_alignment.py`
- Read: `api.py`
- Read: `fastmcp_server.py`

**Step 1: Extend parity coverage**

Add API/MCP equivalence tests for at least:
- `astro_chart`
- `astro_relative_chart`
- `solarreturn`
- `pdchart`
- `qimen`
- `taiyi`
- `jinkou`
- `knowledge_registry`
- `knowledge_read`

**Step 2: Run test to verify gaps**

Run:
- `pytest tests/test_api_alignment.py -q`

Expected: either FAIL because mismatches exist, or reveal that the surface is only partially covered

**Step 3: Write minimal implementation**

Normalize any API/MCP divergences in:
- request defaults
- field naming
- response shape
- snapshot payload behavior

**Step 4: Run verification**

Run:
- `pytest tests/test_api_alignment.py -q`
- `pytest -q`

Expected: PASS

---

### Task 5: Reduce Surface Duplication With A Shared Registry

**Files:**
- Modify: `api.py`
- Modify: `fastmcp_server.py`
- Create: `fatebridge/services/tool_registry.py`

**Step 1: Introduce a shared definition layer**

Create a registry that centralizes:
- tool names
- labels
- request model hooks
- service runner bindings
- descriptions

**Step 2: Refactor one vertical slice first**

Start with a limited family, for example:
- export helpers
- knowledge helpers
- standalone western timing tools

**Step 3: Expand only after parity holds**

Migrate the remaining tools in batches so API and MCP stop drifting independently.

**Step 4: Run verification**

Run:
- `pytest tests/test_api_alignment.py -q`
- `pytest -q`

Expected: PASS with no behavior changes

---

### Task 6: Deepen Relative Chart Coverage

**Files:**
- Modify: `fatebridge/core/astrology.py`
- Modify: `tests/test_astrology_tools.py`
- Modify: `docs/ALGORITHM_COVERAGE.md`

**Step 1: Identify placeholder modes**

List which `relative` modes still route through `_build_unimplemented_relative_payload(...)`.

**Step 2: Write failing tests**

Add tests for the most important currently-placeholder modes to assert:
- `mode_status != "placeholder"`
- main `chart` payload is populated when the mode conceptually requires one

**Step 3: Write minimal implementation**

Promote the highest-value placeholder mode(s) to real computed output using the same current offline approximation philosophy.

**Step 4: Run verification**

Run:
- `pytest tests/test_astrology_tools.py -q`
- `pytest -q`

Expected: PASS

---

### Task 7: Add Basic Agent Run Metadata

**Files:**
- Create: `fatebridge/services/run_metadata.py`
- Modify: `api.py`
- Modify: `fastmcp_server.py`
- Modify: service modules that return snapshots

**Step 1: Add lightweight metadata**

Without introducing a full database yet, add optional response metadata such as:
- `run_id`
- `trace_id`
- `tool_name`
- `engine`
- `generated_at`

**Step 2: Thread metadata consistently**

Ensure both REST and MCP paths expose the same metadata shape for the same tool.

**Step 3: Keep it file-light**

Start with in-memory IDs and response metadata only. Do not add persistence in this task.

**Step 4: Run verification**

Run:
- `pytest tests/test_api_alignment.py -q`
- `pytest -q`

Expected: PASS

---

### Task 8: Design Phase For Dispatch, Trace, Memory, And Benchmarks

**Files:**
- Create: `docs/AGENT_RUNTIME_ROADMAP.md`

**Step 1: Write a design-only roadmap**

Cover:
- natural-language dispatch
- trace JSONL
- artifact storage
- benchmark / golden cases
- optional runtime install / doctor flow

**Step 2: Keep it incremental**

Split the roadmap into:
- lightweight in-repo additions
- medium-complexity local persistence
- heavy multi-runtime packaging work

**Step 3: Define adoption trigger**

State clearly when FateBridge should stay Python-first, and when it becomes worth adopting a `horosa-skill`-style packaged runtime model.

**Step 4: Verify**

Manual review only.

---

## Recommended Execution Order

1. Task 1: Repair Documentation Drift
2. Task 2: Publish A Capability Matrix
3. Task 3: Stop Full Predictive Bundle Recomputations
4. Task 4: Expand API And MCP Parity Tests
5. Task 5: Reduce Surface Duplication With A Shared Registry
6. Task 6: Deepen Relative Chart Coverage
7. Task 7: Add Basic Agent Run Metadata
8. Task 8: Design Phase For Dispatch, Trace, Memory, And Benchmarks

## Exit Criteria

- docs describe the repository as it actually exists today
- the predictive standalone tools no longer compute the full bundle by default
- API and MCP parity is tested across the major tool families
- relative-chart placeholder status is either reduced or explicitly documented
- Agent-facing metadata is available in a consistent minimal form
- the next-stage runtime roadmap is written down instead of living only in audit notes
