# AlphaXiv API-Only GitHub Discovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace abstract/HTML fallback discovery with AlphaXiv API-only discovery for rows whose `Github` field is empty or `WIP`.

**Architecture:** Preserve the unified page pipeline, but narrow the fallback resolver to one external source: AlphaXiv API. Add config for `ALPHAXIV_TOKEN`, use one primary API endpoint per arXiv id, recursively search the JSON payload for GitHub repository URLs, and then reuse the existing GitHub star update and Notion update logic.

**Tech Stack:** Python 3.12, aiohttp, notion-client, python-dotenv, unittest

---

### Task 1: Add failing tests for AlphaXiv API helper behavior

**Files:**
- Modify: `tests/test_config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing tests**

Add tests for:
- `load_config_from_env` returns `alphaxiv_token`
- recursive JSON GitHub extraction finds URLs inside nested dict/list payloads
- recursive JSON GitHub extraction returns `None` when no GitHub URL exists

**Step 2: Run test to verify it fails**

Run: `cd /Users/songliyu/Documents/scripts.zotero-notion-ghstars && uv run python -m unittest tests/test_config.py -v`
Expected: FAIL because helper/config fields do not exist yet

**Step 3: Commit**

```bash
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars add tests/test_config.py
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars commit -m "test: cover alphaxiv api discovery helpers"
```

### Task 2: Implement AlphaXiv API config and payload scanning helpers

**Files:**
- Modify: `main.py`
- Test: `tests/test_config.py`

**Step 1: Write minimal implementation**

Add:
- `alphaxiv_token` to config loading
- helper to recursively scan JSON-like payloads for GitHub repo URLs
- helper to build AlphaXiv API headers

**Step 2: Run tests to verify they pass**

Run: `cd /Users/songliyu/Documents/scripts.zotero-notion-ghstars && uv run python -m unittest tests/test_config.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars add main.py tests/test_config.py
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars commit -m "refactor: add alphaxiv api config and payload scanning"
```

### Task 3: Replace fallback discovery with AlphaXiv API-only lookup

**Files:**
- Modify: `main.py`

**Step 1: Implement AlphaXiv API client method**

Add an async method that calls:
- `GET https://api-dev.alphaxiv.org/papers/v3/{arxiv_id}`
with `X-API-Key` header when configured.

**Step 2: Replace old fallback chain**

Remove use of:
- abstract GitHub scanning
- AlphaXiv HTML page fetching

For empty/`WIP` rows, use only:
- arXiv id extraction
- AlphaXiv API request
- recursive payload GitHub scan

**Step 3: Run tests and syntax check**

Run: `cd /Users/songliyu/Documents/scripts.zotero-notion-ghstars && uv run python -m unittest tests/test_config.py -v && uv run python -m py_compile main.py`
Expected: PASS and no output

**Step 4: Commit**

```bash
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars add main.py
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars commit -m "feat: use alphaxiv api for github fallback discovery"
```

### Task 4: Update docs and environment guidance

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml` (only if dependency/config docs need matching metadata changes)

**Step 1: Update README**

Document:
- fallback is now AlphaXiv API only
- `ALPHAXIV_TOKEN` environment variable
- abstract scanning and HTML scraping are no longer used

**Step 2: Verify**

Run: `cd /Users/songliyu/Documents/scripts.zotero-notion-ghstars && uv run python -m unittest tests/test_config.py -v && uv run python -m py_compile main.py`
Expected: PASS and no output

**Step 3: Commit**

```bash
git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars add README.md main.py tests/test_config.py
        git -C /Users/songliyu/Documents/scripts.zotero-notion-ghstars commit -m "docs: describe alphaxiv api fallback configuration"
```
