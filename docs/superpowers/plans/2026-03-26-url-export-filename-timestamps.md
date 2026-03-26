# URL Export Filename Timestamps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every `url -> csv` export write `<base>-YYYYMMDDHHMMSS.csv` while preserving each source's readable base filename semantics.

**Architecture:** Introduce a shared filename helper for URL-export CSV outputs and route existing source adapters through it. Keep source-specific metadata selection in each adapter, but centralize assembly, timestamp suffixing, and final `.csv` path creation in one place.

**Tech Stack:** Python 3.12, pathlib, datetime, pytest, uv

---

### Task 1: Add a shared URL-export filename helper

**Files:**
- Create: `src/url_to_csv/filenames.py`
- Test: `tests/test_url_export_filenames.py`

- [ ] **Step 1: Write the failing helper tests**

Add tests proving:
- joining readable parts still produces the same untimestamped base stem as today
- the helper appends `-YYYYMMDDHHMMSS.csv`
- the timestamp can be injected in tests so assertions stay deterministic

- [ ] **Step 2: Run the helper tests to verify they fail**

Run: `uv run pytest tests/test_url_export_filenames.py -q`
Expected: FAIL because the helper module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement a helper that:
- accepts `output_dir`
- accepts either filename parts or a prebuilt base stem
- appends a run timestamp in `YYYYMMDDHHMMSS`
- returns a `Path`

- [ ] **Step 4: Run the helper tests to verify they pass**

Run: `uv run pytest tests/test_url_export_filenames.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/url_to_csv/filenames.py tests/test_url_export_filenames.py
git commit -m "feat: add timestamped url export filename helper"
```

### Task 2: Route all URL sources through the shared helper

**Files:**
- Modify: `src/url_to_csv/arxivxplorer.py`
- Modify: `src/url_to_csv/arxiv_org.py`
- Modify: `src/url_to_csv/huggingface_papers.py`
- Modify: `src/url_to_csv/semanticscholar.py`

- [ ] **Step 1: Write the failing adapter-path tests**

Update existing adapter tests so their expected output names become timestamped while preserving their readable source-specific base prefixes.

- [ ] **Step 2: Run the focused adapter tests to verify they fail**

Run: `uv run pytest tests/test_arxiv_org.py tests/test_huggingface_papers.py tests/test_semanticscholar.py tests/test_url_to_csv.py -q`
Expected: FAIL because the adapters still return untimestamped paths.

- [ ] **Step 3: Write the minimal implementation**

Change the adapters so they delegate final path assembly to the shared helper instead of hand-building `f"{stem}.csv"` locally.

- [ ] **Step 4: Run the focused adapter tests to verify they pass**

Run: `uv run pytest tests/test_arxiv_org.py tests/test_huggingface_papers.py tests/test_semanticscholar.py tests/test_url_to_csv.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/url_to_csv/arxivxplorer.py src/url_to_csv/arxiv_org.py src/url_to_csv/huggingface_papers.py src/url_to_csv/semanticscholar.py
git commit -m "feat: timestamp url export csv outputs"
```

### Task 3: Verify shared URL export behavior end to end

**Files:**
- Modify: `README.md`
- Test: `tests/test_dispatch.py`
- Test: `tests/test_url_sources.py`

- [ ] **Step 1: Update user-facing docs if filenames are documented**

Adjust README examples where URL export filenames are mentioned so they show the new timestamp suffix shape.

- [ ] **Step 2: Run the targeted URL export regression suite**

Run: `uv run pytest tests/test_url_export_filenames.py tests/test_arxiv_org.py tests/test_huggingface_papers.py tests/test_semanticscholar.py tests/test_url_to_csv.py tests/test_dispatch.py tests/test_url_sources.py -q`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Run one real export**

Run: `uv run main.py 'https://arxiv.org/list/cs.CV/new'`

Verify:
- the export completes
- the written file includes `-YYYYMMDDHHMMSS.csv`
- the readable base name is still source-specific

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/specs/2026-03-26-url-export-filename-timestamps-design.md docs/superpowers/plans/2026-03-26-url-export-filename-timestamps.md
git commit -m "docs: describe timestamped url export filenames"
```
