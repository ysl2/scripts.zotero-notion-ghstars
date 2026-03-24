# CSV Update Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `.csv` CLI mode that updates rows in place using normalized arXiv URLs as the identity for Github discovery and Stars refresh, while preserving unrelated columns and reusing existing Notion/HTML logic where possible.

**Architecture:** Introduce a shared paper-enrichment layer that accepts a paper title, normalized arXiv URL, and optional existing Github value, then decides whether to reuse an existing repository or run the current Hugging Face -> AlphaXiv discovery flow before refreshing stars. Keep the CLI split by input type (`no arg` -> Notion, `.html` -> HTML export, `.csv` -> CSV in-place update) and let both HTML and CSV modes share progress printing and enrichment behavior.

**Tech Stack:** Python, asyncio, aiohttp, csv module, pytest

---

### Task 1: Cover CLI Dispatch And CSV Update Behavior With Tests

**Files:**
- Modify: `tests/test_dispatch.py`
- Create: `tests/test_csv_update.py`

- [ ] **Step 1: Write the failing dispatch tests**

Add tests proving `.csv` arguments route to a CSV runner, invalid `.csv` paths fail cleanly, and `no arg` / `.html` behavior remains unchanged.

- [ ] **Step 2: Run the dispatch tests to verify they fail**

Run: `uv run pytest tests/test_dispatch.py -vv`
Expected: FAIL because the CSV runner and path validation do not exist yet.

- [ ] **Step 3: Write the failing CSV update tests**

Add tests for:
- in-place overwrite
- preserving unrelated columns and column order
- appending missing `Github` / `Stars` columns when absent
- skipping rows with missing or invalid arXiv URLs
- normalizing arXiv URLs by stripping versions
- reusing existing valid Github URLs without rediscovery
- discovering Github when `Github` is empty
- printing per-row progress and a summary

- [ ] **Step 4: Run the CSV update tests to verify they fail**

Run: `uv run pytest tests/test_csv_update.py -vv`
Expected: FAIL because the CSV update implementation does not exist yet.

### Task 2: Build A Shared URL And Enrichment Layer

**Files:**
- Create: `shared/paper_identity.py`
- Create: `shared/paper_enrichment.py`
- Modify: `html_to_csv/pipeline.py`
- Modify: `notion_sync/pipeline.py`
- Test: `tests/test_csv_update.py`
- Test: `tests/test_notion_mode.py`
- Test: `tests/test_html_to_csv.py`

- [ ] **Step 1: Implement URL normalization and arXiv identity helpers**

Create helpers for:
- extracting an arXiv ID from supported URLs
- normalizing any supported arXiv URL to `https://arxiv.org/abs/<id>`
- building a sortable key from the canonical URL

- [ ] **Step 2: Implement shared Github/Stars enrichment**

Create a helper that:
- accepts `name`, `url`, and optional `existing_github`
- normalizes the arXiv URL
- keeps an existing valid Github URL when present
- otherwise runs the current discovery logic
- refreshes stars when a valid Github repository exists
- returns enough metadata for progress reporting and skip handling

- [ ] **Step 3: Refactor HTML and Notion paths to reuse the shared helpers where practical**

Keep current behavior intact while reducing duplicated URL/Github decision logic.

- [ ] **Step 4: Run focused regression tests**

Run: `uv run pytest tests/test_html_to_csv.py tests/test_notion_mode.py -vv`
Expected: PASS with existing behavior preserved.

### Task 3: Add CSV Runner And CLI Dispatch

**Files:**
- Create: `csv_update/runner.py`
- Create: `csv_update/pipeline.py`
- Modify: `main.py`
- Modify: `tests/test_main.py`
- Test: `tests/test_dispatch.py`
- Test: `tests/test_csv_update.py`

- [ ] **Step 1: Implement the CSV pipeline**

Read the CSV with `csv.DictReader`, preserve field order, append `Github` / `Stars` when missing, process rows concurrently, and rewrite the same file atomically after all row outcomes are known.

- [ ] **Step 2: Implement the CSV runner**

Reuse the same runtime config, concurrency settings, clients, and progress printing style already used by HTML mode.

- [ ] **Step 3: Extend `main.py` dispatch**

Support:
- `uv run main.py` -> Notion mode
- `uv run main.py /path/file.html` -> HTML export mode
- `uv run main.py /path/file.csv` -> CSV in-place update mode

- [ ] **Step 4: Run targeted tests**

Run: `uv run pytest tests/test_dispatch.py tests/test_main.py tests/test_csv_update.py -vv`
Expected: PASS

### Task 4: Full Verification And Commit

**Files:**
- Modify: any files needed from previous tasks only

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -vv`
Expected: PASS

- [ ] **Step 2: Sanity-check the CSV mode on a temporary sample**

Run the CLI on a temporary `.csv` fixture and confirm the file is updated in place with progress output.

- [ ] **Step 3: Commit the implementation**

```bash
git add main.py csv_update shared html_to_csv notion_sync tests docs/superpowers/plans/2026-03-24-csv-update-mode.md
git commit -m "feat: add csv update mode"
```
