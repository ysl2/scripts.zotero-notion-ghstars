# Skip Low-Value Hugging Face Title Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Skip one low-value Hugging Face title-search request after a successful direct paper-page fetch that already showed no repo.

**Architecture:** Keep the discovery order intact except for one narrow optimization: when the direct Hugging Face paper-page request succeeds and yields no GitHub repo, jump straight to AlphaXiv instead of title-searching only to re-point at the same paper id.

**Tech Stack:** Python 3.12, pytest, uv

---

### Task 1: Lock in the new fallback behavior with failing tests

**Files:**
- Modify: `tests/test_shared_services.py`

- [ ] **Step 1: Update the fallback-to-AlphaXiv test**

Change the existing test so it expects a successful no-repo Hugging Face paper-page fetch to skip Hugging Face title search and proceed directly to AlphaXiv.

- [ ] **Step 2: Add a regression test for request-failure fallback**

Add a test proving Hugging Face title search still runs when the initial direct paper-page request fails.

- [ ] **Step 3: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_shared_services.py -q`
Expected: FAIL because the current code still performs title search after a successful no-repo paper-page fetch.

- [ ] **Step 4: Commit**

```bash
git add tests/test_shared_services.py
git commit -m "test: cover skipping low-value hf title search"
```

### Task 2: Implement the minimal optimization

**Files:**
- Modify: `src/shared/discovery.py`

- [ ] **Step 1: Skip title search after successful no-repo paper-page fetch**

Refactor the Hugging Face branch so title search only runs when the direct paper-page request failed.

- [ ] **Step 2: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_shared_services.py -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/shared/discovery.py
git commit -m "perf: skip low-value hf title search"
```

### Task 3: Verify shared behavior

**Files:**
- Modify: `docs/superpowers/specs/2026-03-26-skip-low-value-hf-title-search-design.md`
- Modify: `docs/superpowers/plans/2026-03-26-skip-low-value-hf-title-search.md`

- [ ] **Step 1: Run focused shared regressions**

Run: `uv run pytest tests/test_shared_services.py tests/test_csv_update.py tests/test_url_to_csv.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Commit docs if needed**

```bash
git add docs/superpowers/specs/2026-03-26-skip-low-value-hf-title-search-design.md docs/superpowers/plans/2026-03-26-skip-low-value-hf-title-search.md
git commit -m "docs: record low-value hf title-search optimization"
```
