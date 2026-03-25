# Hugging Face Papers URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Hugging Face Papers collection URL mode that exports collection results to CSV while preserving clean separation between source adapters and shared enrichment/export logic.

**Architecture:** Keep `arxivxplorer` and `huggingface papers` as separate URL adapters under `url_to_csv`. Move URL dispatch into an adapter-selection layer so source-specific parsing stays isolated while seed enrichment and CSV generation remain shared.

**Tech Stack:** Python, asyncio, aiohttp, pytest, uv, HTML parsing, public Hugging Face Papers endpoints

---

### Task 1: Introduce source adapter selection for URL export

**Files:**
- Modify: `main.py`
- Modify: `url_to_csv/pipeline.py`
- Modify: `url_to_csv/runner.py`
- Test: `tests/test_dispatch.py`

- [ ] **Step 1: Write the failing test**

Update dispatch tests so URL mode is selected for both arXiv Xplorer URLs and Hugging Face Papers URLs.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dispatch.py -q`
Expected: FAIL because Hugging Face Papers URLs are currently rejected

- [ ] **Step 3: Write minimal implementation**

Add a URL-source selection layer that recognizes supported sites and routes URL input into the shared URL runner without mixing source-specific logic into `main.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dispatch.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add main.py url_to_csv/pipeline.py url_to_csv/runner.py tests/test_dispatch.py
git commit -m "refactor: add url source dispatch layer"
```

### Task 2: Add Hugging Face Papers URL adapter

**Files:**
- Create: `url_to_csv/huggingface_papers.py`
- Modify: `url_to_csv/pipeline.py`
- Test: `tests/test_huggingface_papers.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- supported Hugging Face collection URLs
- unsupported Hugging Face single-paper URLs
- output CSV naming
- extraction of `PaperSeed` items from a Hugging Face collection response

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_huggingface_papers.py -q`
Expected: FAIL because adapter does not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement a Hugging Face adapter that:
- validates collection URLs under `huggingface.co/papers/...`
- derives a stable CSV output filename
- fetches collection data from the public endpoint and/or frontend page
- converts displayed entries to `PaperSeed`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_huggingface_papers.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add url_to_csv/huggingface_papers.py tests/test_huggingface_papers.py url_to_csv/pipeline.py
git commit -m "feat: add huggingface papers url adapter"
```

### Task 3: Integrate shared export flow and progress output

**Files:**
- Modify: `url_to_csv/runner.py`
- Modify: `tests/test_url_to_csv.py`

- [ ] **Step 1: Write the failing test**

Add an end-to-end runner test showing a Hugging Face Papers URL flows through fetch, shared export, and progress printing.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_url_to_csv.py -q`
Expected: FAIL because Hugging Face URL mode is not wired through the runner yet

- [ ] **Step 3: Write minimal implementation**

Wire the new adapter into the existing URL runner so Hugging Face URL export reuses:
- shared status/progress callbacks
- shared enrichment
- shared CSV writing

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_url_to_csv.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add url_to_csv/runner.py tests/test_url_to_csv.py
git commit -m "feat: support huggingface papers url export"
```

### Task 4: Verify full regression surface

**Files:**
- Modify: `README.md`
- Test: `tests/test_csv_update.py`
- Test: `tests/test_notion_mode.py`
- Test: `tests/test_shared_services.py`

- [ ] **Step 1: Update README**

Document the supported Hugging Face Papers collection URL input mode.

- [ ] **Step 2: Run focused regression tests**

Run: `uv run pytest tests/test_dispatch.py tests/test_huggingface_papers.py tests/test_url_to_csv.py tests/test_csv_update.py tests/test_notion_mode.py -q`
Expected: PASS

- [ ] **Step 3: Run full suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe huggingface papers url mode"
```
