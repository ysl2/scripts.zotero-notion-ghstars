# Arxivxplorer URL To CSV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an end-to-end URL input mode that accepts an `arxivxplorer.com` search URL, fetches the full result set via the site’s paging API, enriches papers with the existing Github/Stars logic, and writes a CSV into the current working directory.

**Architecture:** Keep the existing Notion, HTML, and CSV modes intact, but add a new URL runner plus an `arxivxplorer` client/parser that converts search API results into canonical `PaperSeed` objects. Refactor the current HTML export pipeline slightly so both HTML mode and URL mode reuse the same seed-to-CSV enrichment/export path and the same progress printing.

**Tech Stack:** Python 3.12, asyncio, aiohttp, csv module, pytest

---

### Task 1: Cover URL Dispatch And Arxivxplorer Parsing With Tests

**Files:**
- Modify: `tests/test_dispatch.py`
- Create: `tests/test_url_to_csv.py`

- [ ] **Step 1: Write the failing dispatch tests**

Add tests proving:
- an `https://arxivxplorer.com/...` argument routes to a URL runner
- unsupported URLs fail cleanly
- existing no-arg / `.html` / `.csv` behavior is preserved

- [ ] **Step 2: Run the dispatch tests to verify they fail**

Run: `uv run pytest tests/test_dispatch.py -vv`
Expected: FAIL because URL mode dispatch does not exist yet.

- [ ] **Step 3: Write the failing arxivxplorer parsing and pagination tests**

Add tests for:
- parsing `q`, repeated `cats`, and repeated `year` params from the input URL
- deriving a stable CSV output path in the current working directory
- fetching sequential pages until an empty page is returned
- deduplicating canonical arXiv URLs across pages
- skipping non-arXiv search results

- [ ] **Step 4: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_url_to_csv.py -vv`
Expected: FAIL because URL mode implementation does not exist yet.

### Task 2: Extract A Shared Seed-To-CSV Export Path

**Files:**
- Create: `shared/paper_export.py`
- Modify: `html_to_csv/csv_writer.py`
- Modify: `html_to_csv/pipeline.py`
- Test: `tests/test_html_to_csv.py`
- Test: `tests/test_url_to_csv.py`

- [ ] **Step 1: Write the minimal shared export helper**

Move the “concurrent enrichment of `PaperSeed` -> `PaperRecord` -> CSV write” flow into a shared helper that accepts:
- a list of `PaperSeed`
- an explicit output CSV path
- discovery/github clients
- shared status/progress callbacks

- [ ] **Step 2: Refactor HTML mode to reuse the shared export helper**

Keep HTML parsing separate, but hand off parsed seeds to the shared exporter so URL mode can reuse the exact same downstream logic.

- [ ] **Step 3: Run focused regression tests**

Run: `uv run pytest tests/test_html_to_csv.py -vv`
Expected: PASS with no behavior regression in HTML mode.

### Task 3: Implement Arxivxplorer URL Mode

**Files:**
- Create: `url_to_csv/__init__.py`
- Create: `url_to_csv/arxivxplorer.py`
- Create: `url_to_csv/pipeline.py`
- Create: `url_to_csv/runner.py`
- Modify: `main.py`
- Modify: `tests/test_concurrency_settings.py`
- Modify: `tests/test_main.py`
- Test: `tests/test_url_to_csv.py`

- [ ] **Step 1: Implement arxivxplorer URL parsing and paging**

Add helpers/client code that:
- validates `arxivxplorer.com` URLs
- converts search URLs into API query params for `https://search.arxivxplorer.com`
- requests pages sequentially until an empty page
- emits status updates while pages are being fetched
- converts valid arXiv results into `PaperSeed(name=title, url=https://arxiv.org/abs/<id>)`

- [ ] **Step 2: Implement the URL runner**

Create a runner that:
- sets up the shared clients and concurrency config
- fetches all seeds from arxivxplorer
- chooses an output CSV path in the current working directory
- reuses the shared seed-to-CSV exporter and existing progress output

- [ ] **Step 3: Extend `main.py` dispatch**

Support:
- `uv run main.py` -> Notion mode
- `uv run main.py /path/file.html` -> HTML export mode
- `uv run main.py /path/file.csv` -> CSV update mode
- `uv run main.py 'https://arxivxplorer.com/?...'` -> URL export mode

- [ ] **Step 4: Run targeted tests**

Run: `uv run pytest tests/test_dispatch.py tests/test_main.py tests/test_url_to_csv.py tests/test_concurrency_settings.py -vv`
Expected: PASS

### Task 4: End-To-End Verification And Commit

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update usage documentation**

Document the new URL invocation form and the output path behavior.

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -vv`
Expected: PASS

- [ ] **Step 3: Run a real arxivxplorer URL export**

Run:
`uv run main.py 'https://arxivxplorer.com/?q=streaming+semantic+3d+reconstruction&cats=cs.CV&year=2026&year=2025&year=2024'`

Verify:
- progress is shown while paging and while enriching papers
- a CSV is written in the current working directory
- the filename is stable and derived from the query

- [ ] **Step 4: Commit**

```bash
git add main.py url_to_csv shared html_to_csv tests README.md docs/superpowers/plans/2026-03-24-arxivxplorer-url-to-csv.md
git commit -m "feat: add arxivxplorer url export mode"
```
