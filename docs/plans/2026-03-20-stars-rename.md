# Stars Rename Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the runtime Notion star-count property and repository-facing terminology to `Stars` everywhere this repository actively depends on it.

**Architecture:** Keep the existing GitHub-resolution and Notion-update flow intact, but centralize the actual Notion property name in `main.py` and update every read/write/test/doc call site to use `Stars`. Validate the rename with a failing test first, then pass the same focused suite after implementation.

**Tech Stack:** Python 3.12, aiohttp, notion-client, python-dotenv, unittest

---

### Task 1: Write the failing test for the renamed Notion property

**Files:**
- Modify: `tests/test_config.py`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Update the page fixture and direct property assertions in `tests/test_config.py` so the number property key is `Stars`.

**Step 2: Run test to verify it fails**

Run: `uv run python -m unittest tests.test_config.TestNotionResilience.test_process_page_records_notion_update_failure_without_crashing_batch -v`
Expected: FAIL because production code still reads the pre-rename property name

**Step 3: Commit**

```bash
git add tests/test_config.py
git commit -m "test: cover Stars notion property rename"
```

### Task 2: Update runtime property access to `Stars`

**Files:**
- Modify: `main.py`
- Test: `tests/test_config.py`

**Step 1: Write minimal implementation**

Add shared Notion property-name constants near the top of `main.py`, then update:
- current stars lookup
- Notion page update payload construction
- related docstrings/comments

so runtime code only uses `Stars`.

**Step 2: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_config.TestNotionResilience.test_process_page_records_notion_update_failure_without_crashing_batch -v`
Expected: PASS

**Step 3: Commit**

```bash
git add main.py tests/test_config.py
git commit -m "refactor: rename notion Stars property"
```

### Task 3: Update repository docs and static references

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-13-alphaxiv-api-only-design.md`
- Modify: `docs/plans/2026-03-13-alphaxiv-api-only.md`
- Modify: `docs/plans/2026-03-13-github-fallback-discovery-design.md`
- Modify: `docs/plans/2026-03-13-github-fallback-discovery.md`
- Modify: `docs/plans/2026-03-20-stars-rename-design.md`
- Modify: `docs/plans/2026-03-20-stars-rename.md`

**Step 1: Update documentation**

Replace active references to the pre-rename star terminology with `Stars` so runtime docs, plan docs, and project naming all match the new schema.

**Step 2: Verify**

Run: `rg -n "Git(Hub)?\\sStars" -S .`
Expected: no output

**Step 3: Commit**

```bash
git add README.md docs/plans/*.md
git commit -m "docs: rename Stars terminology"
```

### Task 4: Run full local verification

**Files:**
- Modify: none
- Test: `tests/test_config.py`

**Step 1: Run tests**

Run: `uv run python -m unittest tests/test_config.py -v`
Expected: PASS

**Step 2: Run syntax check**

Run: `uv run python -m py_compile main.py`
Expected: PASS with no output

**Step 3: Commit**

```bash
git add main.py README.md tests/test_config.py docs/plans/*.md
git commit -m "chore: finish Stars rename"
```
