# HF Exact Repo Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-level persistent cache in `cache.db` for arXiv URL to GitHub repo discovery, and remove Hugging Face search fallback so arXiv discovery uses only HF exact plus cache state.

**Architecture:** Introduce a small SQLite-backed `RepoCacheStore` that owns persistence and threshold semantics. `DiscoveryClient` will consult the cache before HF exact, update cache after successful exact responses, and skip exact calls once a no-repo threshold is reached. GitHub stars lookup stays unchanged and uncached.

**Tech Stack:** Python, sqlite3, aiohttp, pytest

---

### Task 1: Lock Discovery Behavior With Tests

**Files:**
- Modify: `tests/test_shared_services.py`

- [ ] Add failing tests proving cache hits bypass HF exact.
- [ ] Add failing tests proving cached no-repo rows below threshold still call HF exact.
- [ ] Add failing tests proving cached no-repo rows at threshold skip HF exact.
- [ ] Update old tests so HF search fallback is no longer expected.
- [ ] Run focused tests and confirm the new expectations fail first.

### Task 2: Add Persistent Repo Cache

**Files:**
- Create: `src/shared/repo_cache.py`
- Modify: `src/shared/settings.py`

- [ ] Write failing tests for storing found repos and incrementing successful no-repo exact checks.
- [ ] Implement SQLite schema creation for `cache.db`.
- [ ] Implement cache read, repo-write, and no-repo-count increment helpers.
- [ ] Add shared settings constants for cache path and no-repo threshold.
- [ ] Run focused tests and confirm they pass.

### Task 3: Wire Cache Into Discovery

**Files:**
- Modify: `src/shared/discovery.py`
- Modify if needed: `src/shared/paper_enrichment.py`

- [ ] Inject `RepoCacheStore` into `DiscoveryClient`.
- [ ] Make arXiv repo discovery check cache before HF exact.
- [ ] Persist found repos and successful no-repo exact outcomes into the cache.
- [ ] Remove HF search fallback from arXiv repo discovery.
- [ ] Keep Semantic Scholar behavior unchanged.

### Task 4: Wire Shared Cache Into Runners And Docs

**Files:**
- Modify: `src/url_to_csv/runner.py`
- Modify: `src/csv_update/runner.py`
- Modify: `src/notion_sync/runner.py`
- Modify: `README.md`
- Modify: `.gitignore`

- [ ] Construct one shared cache store per run and pass it into the discovery client.
- [ ] Document `cache.db` behavior and exact-only HF discovery in the README.
- [ ] Ignore `cache.db` in git.

### Task 5: Verify End-To-End

**Files:**
- No new files expected

- [ ] Run focused discovery/cache tests.
- [ ] Run full `uv run pytest`.
- [ ] Inspect git diff for only intended behavior changes.
