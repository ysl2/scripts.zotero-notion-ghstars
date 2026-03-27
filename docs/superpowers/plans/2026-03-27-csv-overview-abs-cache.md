# CSV Overview/Abs Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend CSV update mode so each arXiv-backed row can also populate cached `Overview` and `Abs` markdown files under `./cache`, while keeping GitHub/stars refresh behavior unchanged.

**Architecture:** Keep `github -> stars` enrichment on the existing shared path, and add a separate AlphaXiv content client plus a small cache service for `overview` and `abs`. CSV rows still execute concurrently, but each row now fans out into three independent branches: GitHub/stars, overview cache, and abs cache.

**Tech Stack:** Python, asyncio, aiohttp, csv module, pathlib, pytest

---

### Task 1: Cover CSV Content Cache Behavior With Tests

**Files:**
- Modify: `tests/test_csv_update.py`

- [ ] **Step 1: Write failing tests for the new columns**

Cover:
- `Overview` / `Abs` columns appended after `Github` / `Stars`
- relative paths written into the CSV
- project-level cache files written only on cache miss
- `github -> stars`, `overview`, and `abs` running independently per row

- [ ] **Step 2: Run the CSV tests to verify they fail**

Run: `uv run pytest tests/test_csv_update.py -vv`
Expected: FAIL because CSV mode does not yet know about AlphaXiv content caching.

### Task 2: Add AlphaXiv Content Fetching And Cache Writing

**Files:**
- Create: `src/shared/alphaxiv_content.py`
- Create: `src/shared/paper_content.py`
- Modify: `src/shared/settings.py`
- Modify: `src/csv_update/pipeline.py`
- Modify: `src/csv_update/runner.py`

- [ ] **Step 1: Implement the AlphaXiv content client**

Use the public AlphaXiv APIs:
- `GET /papers/v3/{arxiv_id}` for title, abstract, and `versionId`
- `GET /papers/v3/{versionId}/overview/en` for overview markdown

- [ ] **Step 2: Implement the file-cache service**

Write markdown files atomically to:
- `cache/overview/<arxiv_id>.md`
- `cache/abs/<arxiv_id>.md`

- [ ] **Step 3: Wire CSV rows to fan out into three branches**

Within each row:
- branch A: existing GitHub discovery and stars refresh
- branch B: ensure overview cache
- branch C: ensure abs cache

- [ ] **Step 4: Run focused tests**

Run: `uv run pytest tests/test_csv_update.py -vv`
Expected: PASS

### Task 3: Update Docs And Verify

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: Document the new CSV columns and cache layout**

- [ ] **Step 2: Ignore `cache/` output**

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest`
Expected: PASS
