# ArXiv Relation HF JSON Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-paper arXiv relation mode's Hugging Face HTML `/papers?q=...` fallback with the Hugging Face JSON search API `/api/papers/search?q=...&limit=N`, while keeping the same low-blast-radius scope, relation-local boundary, and relation-resolution cache semantics.

**Architecture:** Keep the existing relation-resolution flow, cache store, and runner wiring unchanged. The only behavioral change is inside the relation-mode Hugging Face fallback branch: instead of fetching HTML and parsing `DailyPapers`, the relation path should fetch structured JSON search results, score them with the same normalized title-matching rules, and preserve the same negative-cache rules for confirmed misses versus transient failures.

**Tech Stack:** Python 3.12, asyncio, aiohttp, pytest, Hugging Face Papers API, arXiv metadata API, uv

---

## File Map

- Modify: `src/shared/discovery.py`
  - Add a focused Hugging Face JSON search request method for `/api/papers/search`.
  - Keep existing HTML search helpers untouched for any non-relation callers.
- Modify: `src/arxiv_relations/title_resolution.py`
  - Replace HTML fallback parsing with JSON search-result selection.
  - Keep relation-local control flow, resolved-title behavior, and negative-cache rules unchanged.
- Modify: `tests/test_arxiv_relations.py`
  - Replace HTML-based fallback expectations with JSON search-result expectations.
  - Preserve the existing tests for skip, transient failure, and negative-cache behavior, updated to the new request method.

## Guardrails

- Do not broaden fallback behavior outside the single-paper arXiv relation path.
- Do not change `relation_resolution_cache` schema, TTL policy, or key types.
- Do not change URL mode, CSV mode, Notion mode, or GitHub repo discovery.
- Do not add OpenAlex as another fallback provider in this change.
- Do not change CLI flags, runtime config keys, or CSV schema.

### Task 1: Lock down the relation-mode JSON fallback behavior with tests

**Files:**
- Modify: `tests/test_arxiv_relations.py`

- [ ] **Step 1: Update the successful fallback test to use JSON search results**

Change the current Hugging Face fallback test so the fake discovery client exposes a JSON-search method instead of returning HTML:

```python
class FakeDiscoveryClient:
    huggingface_token = "hf-token"

    async def get_huggingface_paper_search_results(self, title: str, *, limit: int = 3):
        events.append(("hf_search_json", title, limit))
        return (
            [
                {
                    "paper": {"id": "2312.00451", "title": "FSGS: Real-Time Few-shot View Synthesis using Gaussian Splatting"}
                }
            ],
            None,
        )
```

Assert the relation row still resolves to:

- `https://arxiv.org/abs/2312.00451`
- matched arXiv title from `arxiv_client.get_title()`
- same cache write-back to both `openalex_work` and `doi`

- [ ] **Step 2: Update the skip and failure-path tests**

Keep the current coverage intent, but switch each fake discovery client to the JSON request method:

- skip fallback when the existing runtime gate is not satisfied
- do not negative-cache transient Hugging Face request failures
- negative-cache only after a successful structured JSON miss

Expected assertions should remain semantically unchanged:

- missing branch or transient request failure -> unresolved fallback row, no negative cache write
- successful empty JSON result -> unresolved fallback row, negative cache write

- [ ] **Step 3: Add a focused regression case for the real FSGS mapping**

Add one relation-mode test that encodes the investigated real mapping:

- query title: `FSGS: Real-Time Few-Shot View Synthesis Using Gaussian Splatting`
- returned JSON candidate: `2312.00451`
- expected resolved URL: `https://arxiv.org/abs/2312.00451`

This locks the approved design change to the real failing case that motivated it.

- [ ] **Step 4: Run focused tests to verify the old implementation fails**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q
```

Expected:

```text
FAIL
```

because the current relation path still calls the HTML search method and expects HTML parsing.

### Task 2: Replace relation-mode HTML fallback with JSON search

**Files:**
- Modify: `src/shared/discovery.py`
- Modify: `src/arxiv_relations/title_resolution.py`

- [ ] **Step 1: Add a focused Hugging Face JSON search request method**

In `src/shared/discovery.py`, add a small method alongside the current Hugging Face helpers:

```python
async def get_huggingface_paper_search_results(self, title: str, *, limit: int = 3):
    if not self.huggingface_token:
        return None, "Missing HUGGINGFACE_TOKEN"
    async with self._huggingface_search_semaphore:
        return await self._request(
            "https://huggingface.co/api/papers/search",
            headers=self._build_huggingface_headers("application/json"),
            params={"q": title, "limit": str(limit)},
            expect="json",
            retry_prefix="Hugging Face Papers API",
            gate=self._huggingface_gate,
        )
```

Do not remove `get_huggingface_search_html()` in this change. The approved scope is only to stop using it from relation mode.

- [ ] **Step 2: Add relation-local JSON result scoring helpers**

In `src/arxiv_relations/title_resolution.py`, replace the current HTML-specific extraction path with a relation-local JSON scorer that:

- reads `paper.id` and `paper.title`
- normalizes titles using the same existing matching rules
- prefers exact normalized-title equality over weaker containment matches
- returns the best arXiv id or no match

Keep this helper relation-local so the change does not broaden shared non-relation behavior.

- [ ] **Step 3: Switch the relation fallback branch to JSON search**

Update `resolve_related_work_title_to_arxiv()` so that after the definitive arXiv API miss it now:

1. looks for `get_huggingface_paper_search_results`
2. respects the same existing runtime gate before entering the Hugging Face branch
3. requests `limit=3`
4. resolves via the best JSON candidate
5. uses `arxiv_client.get_title()` to populate the final resolved title exactly as before

This should preserve the external behavior of a successful relation resolution while changing only the underlying Hugging Face request surface.

- [ ] **Step 4: Keep negative-cache rules unchanged**

Ensure the return values preserve current cache semantics:

- arXiv transient failure -> `negative_cacheable=False`
- missing Hugging Face branch under current gate -> `negative_cacheable=False`
- Hugging Face request failure -> `negative_cacheable=False`
- successful JSON response with no acceptable result -> `negative_cacheable=True`

Do not broaden negative caching beyond confirmed misses.

- [ ] **Step 5: Re-run focused tests**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q
```

Expected:

```text
PASS
```

with the successful JSON fallback case, skip case, transient-failure case, and negative-cache case all passing.

### Task 3: Verify no unintended blast-radius changes

**Files:**
- Modify only if needed: `tests/test_shared_services.py`

- [ ] **Step 1: Decide whether shared-services tests need adjustment**

If the new JSON request method is purely additive and only relation-mode tests changed, leave `tests/test_shared_services.py` untouched.

Only update shared-services tests if:

- the new request helper changes shared interfaces directly relied on elsewhere, or
- a focused regression proves a shared test should exercise the new helper.

- [ ] **Step 2: Run a narrow regression suite**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py tests/test_main.py -q
```

If shared discovery tests were touched, include them:

```bash
uv run pytest tests/test_arxiv_relations.py tests/test_shared_services.py tests/test_main.py -q
```

Expected:

- relation-mode tests pass
- runtime and cache wiring tests still pass
- no non-relation behavior regresses as part of this change

- [ ] **Step 3: Optional live spot-check after tests**

Run one live probe mirroring the design evidence:

```bash
uv run python - <<'PY'
import asyncio
import aiohttp
from src.shared.discovery import DiscoveryClient

async def main():
    async with aiohttp.ClientSession() as session:
        client = DiscoveryClient(session, huggingface_token="dummy")
        payload, error = await client.get_huggingface_paper_search_results(
            "FSGS: Real-Time Few-Shot View Synthesis Using Gaussian Splatting",
            limit=3,
        )
        print(error)
        print(payload[0]["paper"]["id"] if payload else None)

asyncio.run(main())
PY
```

Expected live confirmation:

- no request error
- first matching candidate resolves to `2312.00451`

### Completion Criteria

- relation mode no longer depends on Hugging Face HTML `/papers?q=...` for its second layer
- relation mode uses Hugging Face JSON `/api/papers/search?q=...&limit=N`
- cache semantics and negative-cache rules are unchanged
- the real investigated FSGS mapping is captured in tests
- no non-relation modes are broadened or redesigned as part of this change
