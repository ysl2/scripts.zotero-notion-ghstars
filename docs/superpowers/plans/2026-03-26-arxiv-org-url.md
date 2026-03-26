# arXiv.org URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `arxiv.org` collection URL mode that exports full arXiv collection results to CSV while reusing the existing shared normalization, enrichment, and CSV export pipeline.

**Architecture:** Add a dedicated `src/url_to_csv/arxiv_org.py` adapter alongside the existing source adapters. Keep source detection and URL dispatch in `src/url_to_csv/sources.py` and `src/url_to_csv/pipeline.py`, while preserving the shared downstream flow for arXiv normalization, Github discovery, star lookup, progress printing, sorting, and CSV writing.

**Tech Stack:** Python 3.12, asyncio, aiohttp, pytest, regex-based HTML parsing, uv

---

### Task 1: Add arXiv.org source detection and CLI dispatch coverage

**Files:**
- Modify: `src/url_to_csv/sources.py`
- Modify: `tests/test_url_sources.py`
- Modify: `tests/test_dispatch.py`

- [ ] **Step 1: Write the failing source-detection tests**

Add tests in `tests/test_url_sources.py` that prove:
- `https://arxiv.org/list/cs.CV/recent` is detected as a supported URL source
- `https://arxiv.org/list/cs.CV/new` is detected as a supported URL source
- `https://arxiv.org/search/?searchtype=all&query=reconstruction&abstracts=show&size=50&order=-submitted_date` is detected as a supported URL source
- a single-paper arXiv URL such as `https://arxiv.org/abs/2603.23502` is not detected as a supported collection source

- [ ] **Step 2: Run the source-detection tests to verify they fail**

Run: `uv run pytest tests/test_url_sources.py -q`
Expected: FAIL because `arxiv.org` collection URLs are not recognized yet.

- [ ] **Step 3: Write the failing dispatch tests**

Update `tests/test_dispatch.py` so `async_main()` routes supported arXiv collection URLs into `run_url_mode()` while preserving:
- no-arg Notion mode
- existing CSV mode
- existing arXiv Xplorer, Hugging Face Papers, and Semantic Scholar URL handling

- [ ] **Step 4: Run the dispatch tests to verify they fail**

Run: `uv run pytest tests/test_dispatch.py -q`
Expected: FAIL because supported arXiv collection URLs are still rejected.

- [ ] **Step 5: Write the minimal implementation**

Extend `src/url_to_csv/sources.py` with a new `ARXIV_ORG` source and the smallest possible detection helper that accepts arXiv collection pages but not single-paper pages.

- [ ] **Step 6: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_url_sources.py tests/test_dispatch.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/url_to_csv/sources.py tests/test_url_sources.py tests/test_dispatch.py
git commit -m "feat: detect arxiv collection urls"
```

### Task 2: Build the arXiv.org adapter for list pages

**Files:**
- Create: `src/url_to_csv/arxiv_org.py`
- Create: `tests/test_arxiv_org.py`
- Modify: `src/url_to_csv/pipeline.py`

- [ ] **Step 1: Write the failing list-page adapter tests**

Add tests in `tests/test_arxiv_org.py` for:
- supported `list/.../recent` and `list/.../new` URL detection at the adapter level
- output CSV naming for `https://arxiv.org/list/cs.CV/recent` -> `arxiv-cs.CV-recent.csv`
- output CSV naming for `https://arxiv.org/list/cs.CV/new` -> `arxiv-cs.CV-new.csv`
- extraction of `PaperSeed` entries from representative `dl#articles` HTML
- inclusion of all `new` page sections by collecting every valid `dt/dd` article pair

- [ ] **Step 2: Run the list-page adapter tests to verify they fail**

Run: `uv run pytest tests/test_arxiv_org.py -q`
Expected: FAIL because the adapter file does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement the smallest possible `src/url_to_csv/arxiv_org.py` surface that can:
- validate `list` collection URLs
- derive stable CSV output paths for list pages
- extract canonical `PaperSeed(name, url)` entries from `dl#articles`

- [ ] **Step 4: Run the adapter tests to verify they pass**

Run: `uv run pytest tests/test_arxiv_org.py -q`
Expected: PASS for the list-page cases.

- [ ] **Step 5: Commit**

```bash
git add src/url_to_csv/arxiv_org.py tests/test_arxiv_org.py src/url_to_csv/pipeline.py
git commit -m "feat: add arxiv list page adapter"
```

### Task 3: Add search-page parsing and full pagination coverage

**Files:**
- Modify: `src/url_to_csv/arxiv_org.py`
- Modify: `tests/test_arxiv_org.py`

- [ ] **Step 1: Write the failing search-page parsing tests**

Extend `tests/test_arxiv_org.py` with tests for:
- supported `search` URL detection
- output CSV naming for a representative `search` URL
- extraction of seeds from `li.arxiv-result`
- normalization of extracted `/abs/<id>` links to canonical versionless arXiv URLs

- [ ] **Step 2: Run the search-page parsing tests to verify they fail**

Run: `uv run pytest tests/test_arxiv_org.py -q`
Expected: FAIL because search-page parsing is not implemented yet.

- [ ] **Step 3: Write the failing pagination tests**

Add tests proving:
- `list` pagination walks `skip` using the current page size until the full `Total of N entries` is covered
- `search` pagination walks `start` using the current `size` until the full result count is covered
- duplicate canonical abs URLs across pages are removed
- standard `list` or `search` pages fail loudly if total-count parsing or page stepping is impossible

- [ ] **Step 4: Run the pagination tests to verify they fail**

Run: `uv run pytest tests/test_arxiv_org.py -q`
Expected: FAIL because only single-page parsing exists so far.

- [ ] **Step 5: Write the minimal implementation**

Extend `src/url_to_csv/arxiv_org.py` to:
- parse `search` result pages
- infer total counts and page sizes from standard arXiv `list` and `search` markup
- fetch all pages for standard `list` and `search` inputs
- deduplicate by canonical arXiv URL
- keep nonstandard fallback collection behavior limited to current-page extraction only

- [ ] **Step 6: Run the adapter tests to verify they pass**

Run: `uv run pytest tests/test_arxiv_org.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/url_to_csv/arxiv_org.py tests/test_arxiv_org.py
git commit -m "feat: support arxiv search pagination"
```

### Task 4: Integrate the arXiv.org adapter into the shared URL export flow

**Files:**
- Modify: `src/url_to_csv/pipeline.py`
- Modify: `src/url_to_csv/runner.py`
- Modify: `tests/test_url_to_csv.py`

- [ ] **Step 1: Write the failing end-to-end URL export tests**

Add tests in `tests/test_url_to_csv.py` showing:
- `fetch_paper_seeds_from_url()` dispatches arXiv collection URLs to the new adapter
- `export_url_to_csv()` writes an arXiv-derived CSV path in the requested output directory
- `run_url_mode()` prints fetch progress and paper-enrichment progress for arXiv collection URLs

- [ ] **Step 2: Run the end-to-end tests to verify they fail**

Run: `uv run pytest tests/test_url_to_csv.py -q`
Expected: FAIL because the runner and pipeline are not yet wired to the new adapter.

- [ ] **Step 3: Write the minimal implementation**

Wire the `ARXIV_ORG` adapter through the existing URL export path so it reuses:
- shared status callbacks
- shared arXiv normalization
- shared Github discovery and star lookup
- shared CSV writing and sorting

- [ ] **Step 4: Run the focused integration tests to verify they pass**

Run: `uv run pytest tests/test_url_to_csv.py tests/test_dispatch.py tests/test_url_sources.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/url_to_csv/pipeline.py src/url_to_csv/runner.py tests/test_url_to_csv.py
git commit -m "feat: support arxiv url export flow"
```

### Task 5: Document the mode and verify the full regression surface

**Files:**
- Modify: `README.md`
- Test: `tests/test_huggingface_papers.py`
- Test: `tests/test_semanticscholar.py`
- Test: `tests/test_csv_update.py`
- Test: `tests/test_notion_mode.py`
- Test: `tests/test_shared_services.py`

- [ ] **Step 1: Update the README**

Document the new supported `arxiv.org` collection URL forms, including representative `list` and `search` examples and the fact that standard `list/search` pagination is exported in full.

- [ ] **Step 2: Run the focused regression suite**

Run: `uv run pytest tests/test_arxiv_org.py tests/test_url_sources.py tests/test_dispatch.py tests/test_url_to_csv.py tests/test_huggingface_papers.py tests/test_semanticscholar.py -q`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Run one real arXiv export**

Run: `uv run main.py 'https://arxiv.org/list/cs.CV/recent'`

Verify:
- pagination progress is shown
- paper enrichment progress is shown
- a CSV is written in the current working directory
- the file name follows the documented `arxiv-...` convention

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/plans/2026-03-26-arxiv-org-url.md
git commit -m "docs: describe arxiv url export mode"
```
