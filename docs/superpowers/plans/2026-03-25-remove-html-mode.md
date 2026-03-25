# Remove HTML Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the legacy HTML input path and refactor shared paper/export helpers into `shared/` so only Notion, arXiv Xplorer URL export, and CSV update remain.

**Architecture:** Move generic paper dataclasses, CSV writing, and arXiv client code out of `html_to_csv` and into `shared/`. Then update the three surviving flows to depend only on `shared/`, delete the HTML-specific code, and simplify dispatch/tests accordingly.

**Tech Stack:** Python, asyncio, aiohttp, pytest, uv

---

### Task 1: Move shared paper models and CSV IO out of `html_to_csv`

**Files:**
- Create: `shared/papers.py`
- Create: `shared/csv_io.py`
- Modify: `shared/paper_export.py`
- Modify: `csv_update/pipeline.py`
- Modify: `url_to_csv/arxivxplorer.py`
- Test: `tests/test_url_to_csv.py`
- Test: `tests/test_csv_update.py`

- [ ] **Step 1: Write the failing tests**

Update imports in tests so they expect shared modules instead of `html_to_csv` models/helpers.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_url_to_csv.py tests/test_csv_update.py -q`
Expected: import failures from missing shared modules

- [ ] **Step 3: Write minimal implementation**

Create `shared/papers.py` with `PaperSeed`, `PaperRecord`, `PaperOutcome`, `ConversionResult`, and `sort_records`. Create `shared/csv_io.py` with CSV header constants and CSV writing helpers. Update consumers to import from `shared`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_url_to_csv.py tests/test_csv_update.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/papers.py shared/csv_io.py shared/paper_export.py csv_update/pipeline.py url_to_csv/arxivxplorer.py tests/test_url_to_csv.py tests/test_csv_update.py
git commit -m "refactor: move shared paper export primitives"
```

### Task 2: Move the arXiv client into `shared`

**Files:**
- Create: `shared/arxiv.py`
- Modify: `notion_sync/runner.py`
- Test: `tests/test_notion_mode.py`

- [ ] **Step 1: Write the failing test**

Update tests/imports to require `notion_sync` to use `shared.arxiv.ArxivClient`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_notion_mode.py -q`
Expected: import or patch target failures

- [ ] **Step 3: Write minimal implementation**

Move the arXiv client implementation to `shared/arxiv.py` and update Notion code to import it from there.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_notion_mode.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shared/arxiv.py notion_sync/runner.py tests/test_notion_mode.py
git commit -m "refactor: share arxiv client outside html mode"
```

### Task 3: Remove HTML dispatch and delete HTML-specific code

**Files:**
- Modify: `main.py`
- Modify: `tests/test_dispatch.py`
- Modify: `tests/test_concurrency_settings.py`
- Delete: `html_to_csv/__init__.py`
- Delete: `html_to_csv/arxiv.py`
- Delete: `html_to_csv/csv_writer.py`
- Delete: `html_to_csv/html_parser.py`
- Delete: `html_to_csv/models.py`
- Delete: `html_to_csv/pipeline.py`
- Delete: `html_to_csv/runner.py`
- Delete: `tests/test_html_to_csv.py`

- [ ] **Step 1: Write the failing tests**

Update dispatch/concurrency tests so only URL, CSV, and Notion remain valid modes.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dispatch.py tests/test_concurrency_settings.py -q`
Expected: failures because main and concurrency assertions still mention HTML mode

- [ ] **Step 3: Write minimal implementation**

Remove HTML path handling from `main.py`, update tests/imports, and delete obsolete HTML files.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dispatch.py tests/test_concurrency_settings.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_dispatch.py tests/test_concurrency_settings.py
git rm -r html_to_csv tests/test_html_to_csv.py
git commit -m "refactor: remove legacy html mode"
```

### Task 4: Full verification

**Files:**
- Modify: any touched files needed for final cleanup
- Test: `tests/test_main.py`
- Test: `tests/test_url_to_csv.py`
- Test: `tests/test_csv_update.py`
- Test: `tests/test_notion_mode.py`

- [ ] **Step 1: Run focused regression tests**

Run: `uv run pytest tests/test_main.py tests/test_dispatch.py tests/test_url_to_csv.py tests/test_csv_update.py tests/test_notion_mode.py -q`
Expected: PASS

- [ ] **Step 2: Run full suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: Commit final cleanup**

```bash
git add .
git commit -m "refactor: simplify repository modes"
```
