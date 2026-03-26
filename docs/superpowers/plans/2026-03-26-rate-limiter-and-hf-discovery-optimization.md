# Rate Limiter And Hugging Face Discovery Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve request scheduling and remove a redundant Hugging Face discovery fetch without changing external behavior.

**Architecture:** Keep both changes internal. Refactor `RateLimiter.acquire()` to reserve future start slots under lock and sleep outside the lock, then adjust Hugging Face discovery fallback so a successfully fetched paper page is not re-requested when search points back to the same arXiv id.

**Tech Stack:** Python 3.12, asyncio, pytest, uv

---

### Task 1: Lock in the new behavior with failing tests

**Files:**
- Modify: `tests/test_shared_services.py`

- [ ] **Step 1: Write the failing rate-limiter test**

Add a test proving two concurrent waiters can both enter their scheduled sleep path instead of one waiter blocking the other behind the rate-limiter lock.

- [ ] **Step 2: Write the failing Hugging Face discovery test**

Add a test proving a successful direct paper-page fetch with no repo does not trigger the same paper-page fetch a second time after title search resolves to the same arXiv id.

- [ ] **Step 3: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_shared_services.py -q`
Expected: FAIL because the current limiter sleeps while holding the lock and the current discovery flow refetches the same Hugging Face page.

- [ ] **Step 4: Commit**

```bash
git add tests/test_shared_services.py
git commit -m "test: cover limiter scheduling and hf duplicate fetch"
```

### Task 2: Implement the minimal optimizations

**Files:**
- Modify: `src/shared/http.py`
- Modify: `src/shared/discovery.py`

- [ ] **Step 1: Refactor RateLimiter scheduling**

Reserve the next allowed request-start time under lock, then sleep outside the lock for the reserved delay.

- [ ] **Step 2: Remove the duplicate Hugging Face paper-page fetch**

Only retry the paper page after search resolution if the original direct paper-page request failed; otherwise reuse the knowledge that the page was already inspected.

- [ ] **Step 3: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_shared_services.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/shared/http.py src/shared/discovery.py
git commit -m "perf: reduce limiter contention and hf duplicate fetches"
```

### Task 3: Verify shared behavior

**Files:**
- Modify: `docs/superpowers/specs/2026-03-26-rate-limiter-and-hf-discovery-optimization-design.md`
- Modify: `docs/superpowers/plans/2026-03-26-rate-limiter-and-hf-discovery-optimization.md`

- [ ] **Step 1: Run focused shared regressions**

Run: `uv run pytest tests/test_shared_services.py tests/test_csv_update.py tests/test_url_to_csv.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Commit docs if needed**

```bash
git add docs/superpowers/specs/2026-03-26-rate-limiter-and-hf-discovery-optimization-design.md docs/superpowers/plans/2026-03-26-rate-limiter-and-hf-discovery-optimization.md
git commit -m "docs: record rate limiter and hf discovery optimization"
```
