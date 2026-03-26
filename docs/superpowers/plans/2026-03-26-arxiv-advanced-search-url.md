# arXiv Advanced Search URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add support for `https://arxiv.org/search/advanced?...` inputs while preserving the existing arXiv search export flow and readable CSV filenames.

**Architecture:** Reuse the current arXiv search-results pipeline instead of inventing a new source path. Accept `/search/advanced` in the arXiv URL classifier, derive its filename slug from ordered `terms-*-term` query parameters, and route fetching through the same search pagination logic already used by `/search`.

**Tech Stack:** Python 3.12, pathlib, urllib.parse, pytest, uv

---

### Task 1: Lock in advanced-search behavior with failing tests

**Files:**
- Modify: `tests/test_url_sources.py`
- Modify: `tests/test_dispatch.py`
- Modify: `tests/test_arxiv_org.py`

- [ ] **Step 1: Write the failing source-detection test**

Add a case in `tests/test_url_sources.py` proving `detect_url_source(...)` classifies an arXiv advanced-search URL as `UrlSource.ARXIV_ORG`.

- [ ] **Step 2: Write the failing dispatch test**

Add a case in `tests/test_dispatch.py` proving `async_main([...])` routes an advanced-search URL into `run_url_mode(...)`.

- [ ] **Step 3: Write the failing arXiv-org tests**

In `tests/test_arxiv_org.py`, add tests proving:
- `is_supported_arxiv_org_url(...)` accepts `/search/advanced`
- `output_csv_path_for_arxiv_org_url(...)` derives the filename slug from ordered `terms-*-term` values
- `fetch_paper_seeds_from_arxiv_org_url(...)` pages an advanced-search URL using `start=...`

- [ ] **Step 4: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_url_sources.py tests/test_dispatch.py tests/test_arxiv_org.py -q`
Expected: FAIL because `/search/advanced` is still rejected today.

- [ ] **Step 5: Commit**

```bash
git add tests/test_url_sources.py tests/test_dispatch.py tests/test_arxiv_org.py
git commit -m "test: cover arxiv advanced search urls"
```

### Task 2: Implement minimal arXiv advanced-search support

**Files:**
- Modify: `src/url_to_csv/arxiv_org.py`

- [ ] **Step 1: Extend supported URL detection**

Accept `/search/advanced` anywhere `is_supported_arxiv_org_url(...)` currently accepts `/search`.

- [ ] **Step 2: Extend output filename generation**

Build the search slug from ordered `terms-*-term` values for `/search/advanced`, falling back to `search` if none are present.

- [ ] **Step 3: Reuse existing search pagination**

Route `/search/advanced` through the same `_fetch_search_seeds(...)` path used by `/search`, so `start=...` pagination and completeness checks remain unchanged.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_url_sources.py tests/test_dispatch.py tests/test_arxiv_org.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/url_to_csv/arxiv_org.py
git commit -m "feat: support arxiv advanced search urls"
```

### Task 3: Verify end-to-end support and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-03-26-arxiv-advanced-search-url-design.md`
- Modify: `docs/superpowers/plans/2026-03-26-arxiv-advanced-search-url.md`

- [ ] **Step 1: Update README**

Add `https://arxiv.org/search/advanced?...` to the supported-source list and include one concrete example.

- [ ] **Step 2: Run the combined regression suite**

Run: `uv run pytest tests/test_url_sources.py tests/test_dispatch.py tests/test_arxiv_org.py tests/test_url_to_csv.py -q`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Commit docs if needed**

```bash
git add README.md docs/superpowers/specs/2026-03-26-arxiv-advanced-search-url-design.md docs/superpowers/plans/2026-03-26-arxiv-advanced-search-url.md
git commit -m "docs: describe arxiv advanced search support"
```
