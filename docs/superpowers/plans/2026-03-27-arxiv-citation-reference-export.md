# ArXiv Citation Reference Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new CLI mode that accepts one single-paper arXiv URL, finds that paper's references and citations via OpenAlex, filters the related works down to arXiv-backed papers, and writes two standard `Name, Url, Github, Stars` CSV files under `./output`.

**Architecture:** Keep the new feature separate from the existing collection-URL adapters. Add one OpenAlex client under `src/shared/` for title search and relationship fetching, add one small single-paper relation pipeline under a new feature package, and reuse the existing shared `PaperSeed -> Github/Stars -> CSV` export path so the new mode inherits the current schema, sorting, and enrichment behavior.

**Tech Stack:** Python 3.12, asyncio, aiohttp, pytest, arXiv metadata fetching, OpenAlex API, uv

---

### Task 1: Lock CLI dispatch and runtime config with tests

**Files:**
- Modify: `src/app.py`
- Modify: `src/shared/runtime.py`
- Modify: `tests/test_dispatch.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write the failing dispatch tests**

Update `tests/test_dispatch.py` with cases proving:
- `https://arxiv.org/abs/2603.23502` routes to the new single-paper relation runner
- `https://arxiv.org/pdf/2603.23502.pdf` also routes to the new single-paper relation runner
- supported collection URLs such as `https://arxiv.org/list/cs.CV/recent` still route to `run_url_mode()`
- unsupported non-collection URLs still fail as before

- [ ] **Step 2: Write the failing runtime-config test**

Update `tests/test_main.py` so `load_runtime_config()` is expected to read `OPENALEX_API_KEY` as another optional credential.

- [ ] **Step 3: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_dispatch.py tests/test_main.py -q`
Expected: FAIL because `app.async_main()` has no single-paper arXiv branch and `load_runtime_config()` does not expose `OPENALEX_API_KEY`.

- [ ] **Step 4: Write the minimal implementation**

Make the smallest app/runtime changes needed to:
- import a new `run_arxiv_relations_mode`
- detect single-paper arXiv URLs before falling through to the collection URL check
- include `openalex_api_key` in the shared runtime config

- [ ] **Step 5: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_dispatch.py tests/test_main.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/app.py src/shared/runtime.py tests/test_dispatch.py tests/test_main.py
git commit -m "feat: route single arxiv urls to relation export mode"
```

### Task 2: Add single-paper arXiv helpers and title lookup

**Files:**
- Modify: `src/shared/paper_identity.py`
- Modify: `src/shared/arxiv.py`
- Modify: `tests/test_shared_arxiv.py`
- Create if needed: `tests/test_paper_identity.py`

- [ ] **Step 1: Write the failing URL-normalization tests**

Add tests proving:
- single-paper `abs` URLs normalize successfully
- single-paper `pdf` URLs normalize successfully
- collection URLs such as `list/...`, `search/...`, and `catchup/...` are rejected as single-paper inputs
- malformed arXiv URLs are rejected

- [ ] **Step 2: Write the failing title-lookup tests**

Extend `tests/test_shared_arxiv.py` with a focused test for a new arXiv client method that resolves a paper title from a single arXiv paper id or URL.

- [ ] **Step 3: Run the focused tests to verify they fail**

Run: `uv run pytest tests/test_shared_arxiv.py tests/test_paper_identity.py -q`
Expected: FAIL because the helper and title lookup surface do not exist yet.

- [ ] **Step 4: Write the minimal implementation**

Implement:
- one helper in `src/shared/paper_identity.py` that recognizes single-paper arXiv URLs
- one new arXiv client method in `src/shared/arxiv.py` that fetches the input paper title from arXiv metadata

- [ ] **Step 5: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_shared_arxiv.py tests/test_paper_identity.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shared/paper_identity.py src/shared/arxiv.py tests/test_shared_arxiv.py tests/test_paper_identity.py
git commit -m "feat: add single paper arxiv helpers"
```

### Task 3: Add the shared OpenAlex client and parsing coverage

**Files:**
- Create: `src/shared/openalex.py`
- Modify: `src/shared/runtime.py`
- Create: `tests/test_openalex.py`

- [ ] **Step 1: Write the failing OpenAlex client tests**

Create `tests/test_openalex.py` with tests for:
- title search returning the first result by relevance
- extracting a canonical arXiv URL from an OpenAlex work that includes arXiv-backed metadata
- ignoring related works that do not expose arXiv-backed metadata
- references hydration from referenced-work identifiers
- citations pagination across multiple pages
- request headers including the configured `OPENALEX_API_KEY` when present

- [ ] **Step 2: Run the OpenAlex tests to verify they fail**

Run: `uv run pytest tests/test_openalex.py -q`
Expected: FAIL because `src/shared/openalex.py` does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement an `OpenAlexClient` in `src/shared/openalex.py` that can:
- search works by title
- return the first work from the result list
- fetch referenced work details
- paginate through cited-by results
- normalize any arXiv-backed related work into `PaperSeed(name, url)`

- [ ] **Step 4: Wire the new credential into client construction**

Extend `src/shared/runtime.py` only as needed so the new runner can pass `openalex_api_key` into `OpenAlexClient` via the existing `build_client()` pattern.

- [ ] **Step 5: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_openalex.py tests/test_main.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shared/openalex.py src/shared/runtime.py tests/test_openalex.py tests/test_main.py
git commit -m "feat: add openalex relation client"
```

### Task 4: Build the single-paper relation pipeline

**Files:**
- Create: `src/arxiv_relations/__init__.py`
- Create: `src/arxiv_relations/pipeline.py`
- Create: `src/arxiv_relations/runner.py`
- Modify: `src/shared/papers.py`
- Modify if needed: `src/shared/progress.py`
- Create: `tests/test_arxiv_relations.py`

- [ ] **Step 1: Write the failing pipeline tests**

Create `tests/test_arxiv_relations.py` with tests showing:
- the pipeline resolves the input arXiv title, searches OpenAlex, and exports both references and citations
- non-arXiv related works are dropped
- duplicate related works collapse to one canonical arXiv URL
- the two output CSV paths use timestamped names ending in `references` and `citations`
- the shared enrichment/export path is called with `PaperSeed` rows for both CSVs

- [ ] **Step 2: Run the pipeline tests to verify they fail**

Run: `uv run pytest tests/test_arxiv_relations.py -q`
Expected: FAIL because the new feature package does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement a focused pipeline that:
- validates and normalizes the single-paper arXiv input
- asks the arXiv client for the paper title
- asks the OpenAlex client for the target work
- fetches reference and citation seeds
- drops non-arXiv works
- writes two CSVs by reusing `export_paper_seeds_to_csv()`

- [ ] **Step 4: Keep the output shape aligned with current exports**

Reuse `src/url_to_csv/filenames.py` rather than inventing a second timestamp helper, and keep the final CSV schema on the current shared `Name, Url, Github, Stars` path.

- [ ] **Step 5: Run the focused tests to verify they pass**

Run: `uv run pytest tests/test_arxiv_relations.py tests/test_openalex.py tests/test_shared_arxiv.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/arxiv_relations/__init__.py src/arxiv_relations/pipeline.py src/arxiv_relations/runner.py src/shared/papers.py tests/test_arxiv_relations.py
git commit -m "feat: export arxiv citations and references"
```

### Task 5: Wire the runner through the app and document the mode

**Files:**
- Modify: `src/app.py`
- Modify: `README.md`
- Modify: `.env.example`
- Modify if needed: `src/shared/settings.py`
- Modify if needed: `tests/test_url_export_filenames.py`

- [ ] **Step 1: Write the failing documentation-facing tests if needed**

If any filename or settings helpers need extension, add the smallest failing tests first.

- [ ] **Step 2: Wire the runner fully**

Finish the runner integration so the new mode:
- constructs `ArxivClient`, `OpenAlexClient`, `DiscoveryClient`, and `GitHubClient`
- prints status/progress consistently with current long-running modes
- returns a nonzero exit code on any hard failure before writing CSVs

- [ ] **Step 3: Update docs and config examples**

Document:
- accepted single-paper arXiv URL forms
- `OPENALEX_API_KEY`
- the fact that the mode writes two CSV files under `./output`
- the current first-version rule that only arXiv-backed related works are kept

- [ ] **Step 4: Run the focused integration tests**

Run: `uv run pytest tests/test_dispatch.py tests/test_arxiv_relations.py tests/test_openalex.py tests/test_main.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app.py README.md .env.example src/shared/settings.py tests/test_dispatch.py tests/test_arxiv_relations.py tests/test_openalex.py tests/test_main.py
git commit -m "docs: describe arxiv relation export mode"
```

### Task 6: Verify the full regression surface

**Files:**
- No new files expected

- [ ] **Step 1: Run the new-mode focused suite**

Run: `uv run pytest tests/test_arxiv_relations.py tests/test_openalex.py tests/test_shared_arxiv.py tests/test_dispatch.py tests/test_main.py -q`
Expected: PASS

- [ ] **Step 2: Run the existing URL/export regression suite**

Run: `uv run pytest tests/test_url_to_csv.py tests/test_url_sources.py tests/test_shared_services.py tests/test_shared_papers.py -q`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Run one real single-paper export**

Run: `uv run main.py 'https://arxiv.org/abs/2501.12345'`

Verify:
- relation-fetch progress is printed
- both `references` and `citations` CSVs are written under `./output`
- both CSVs use the standard headers
- both CSVs contain only arXiv-backed rows

- [ ] **Step 5: Inspect the final diff**

Run: `git diff --stat HEAD~6..HEAD`
Expected: only the planned mode, tests, and docs are changed.
