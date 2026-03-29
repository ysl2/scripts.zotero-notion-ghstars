# ArXiv Relation OpenAlex Preprint Crosswalk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a narrow OpenAlex published-version-to-preprint crosswalk step ahead of arXiv and Hugging Face title search in the single-paper arXiv relation-resolution ladder, while preserving current cache semantics, retained-row behavior, and CSV compatibility.

**Architecture:** Keep the change relation-local. Extend the OpenAlex client with one focused helper that can inspect alternate-version candidates for a current related work and return a canonical arXiv URL only when explicit OpenAlex evidence exists. Then update the relation title-resolution ladder to try this OpenAlex crosswalk before arXiv title search and Hugging Face fallback. Cache keys, retained-row URL priority, and non-relation code paths stay unchanged.

**Tech Stack:** Python 3.12, asyncio, aiohttp, pytest, OpenAlex API, arXiv metadata API, Hugging Face Papers API, uv

---

## File Map

- Modify: `src/shared/openalex.py`
  - Add a focused relation helper for finding an alternate OpenAlex work with explicit arXiv evidence.
  - Keep existing target-work search and reference/citation fetch behavior unchanged.
- Modify: `src/arxiv_relations/title_resolution.py`
  - Insert the OpenAlex crosswalk step ahead of arXiv and Hugging Face title search.
  - Preserve current negative-cache semantics and final resolved-title behavior.
- Modify: `tests/test_openalex.py`
  - Add focused tests for explicit-arXiv acceptance and weak-candidate rejection in the new helper.
- Modify: `tests/test_arxiv_relations.py`
  - Add ladder-order tests proving OpenAlex crosswalk now runs before arXiv/HF fallback and only accepts explicit arXiv evidence.

## Guardrails

- Do not broaden non-relation behavior.
- Do not add a new cache key type.
- Do not use title text as a persistent cache key.
- Do not remove arXiv or Hugging Face fallback from the ladder.
- Do not accept weak title similarity in the OpenAlex crosswalk step without explicit arXiv evidence.
- Do not change relation CSV schema or output filenames.

### Task 1: Lock down the OpenAlex crosswalk contract with tests

**Files:**
- Modify: `tests/test_openalex.py`

- [ ] **Step 1: Add a focused success case for explicit arXiv evidence**

Add a test proving the helper accepts an alternate OpenAlex work only when that work carries explicit arXiv identity:

```python
@pytest.mark.anyio
async def test_find_related_work_preprint_accepts_candidate_with_arxiv_location():
    client = OpenAlexClient(mailto="test@example.com")
    work = {
        "id": "https://openalex.org/W-published",
        "display_name": "Example Published Paper",
    }
    client._request = AsyncMock(
        return_value=(
            {
                "results": [
                    {
                        "id": "https://openalex.org/W-preprint",
                        "display_name": "Example Published Paper",
                        "locations": [{"landing_page_url": "https://arxiv.org/abs/2401.12345"}],
                    }
                ]
            },
            None,
        )
    )

    result = await client.find_related_work_preprint_arxiv_url(work, title="Example Published Paper")
    assert result == "https://arxiv.org/abs/2401.12345"
```

- [ ] **Step 2: Add rejection coverage for weak or publisher-only candidates**

Add tests proving the helper returns no result when:

- the candidate has only a publisher DOI
- the candidate title is similar but no explicit arXiv evidence exists
- the response payload is malformed or empty

This ensures the new step stays conservative and does not become a fuzzy matcher.

- [ ] **Step 3: Run the focused OpenAlex tests to verify they fail**

Run:

```bash
uv run pytest tests/test_openalex.py -q
```

Expected:

```text
FAIL
```

because the helper does not exist yet.

### Task 2: Implement the narrow OpenAlex crosswalk helper

**Files:**
- Modify: `src/shared/openalex.py`

- [ ] **Step 1: Add a relation-local helper that searches for alternate-version candidates**

Implement one focused helper in `src/shared/openalex.py`, for example:

```python
async def find_related_work_preprint_arxiv_url(
    self,
    work: dict[str, Any],
    *,
    title: str,
) -> str | None:
    ...
```

The helper may use a constrained OpenAlex search request seeded by the current work title, but it must only return a value when it can normalize explicit arXiv evidence from a returned candidate.

- [ ] **Step 2: Reuse existing canonical arXiv normalization helpers**

Do not invent a second arXiv-normalization path. Reuse the current OpenAlex-side arXiv URL normalization utilities so accepted results always become canonical versionless `https://arxiv.org/abs/...` URLs.

- [ ] **Step 3: Keep weak candidates non-fatal**

If OpenAlex returns:

- no results
- malformed payload
- only publisher-backed candidates
- multiple candidates but none with explicit arXiv evidence

the helper should return `None` rather than raise, so the relation ladder can continue to arXiv and Hugging Face fallback.

- [ ] **Step 4: Re-run the focused OpenAlex tests**

Run:

```bash
uv run pytest tests/test_openalex.py -q
```

Expected:

```text
PASS
```

for the new helper contract.

### Task 3: Change the relation ladder order

**Files:**
- Modify: `tests/test_arxiv_relations.py`
- Modify: `src/arxiv_relations/title_resolution.py`

- [ ] **Step 1: Add failing ladder-order tests**

Add focused tests proving:

- direct OpenAlex arXiv evidence still wins immediately
- OpenAlex crosswalk runs before arXiv title search
- arXiv title search runs only if OpenAlex crosswalk returns no explicit arXiv hit
- Hugging Face search runs only if both OpenAlex crosswalk and arXiv title search fail

One representative test should record events:

```python
events == [
    ("openalex_crosswalk", "Example Published Paper"),
    ("arxiv_title_search", "Example Published Paper"),
    ("hf_search_json", "Example Published Paper", 1),
]
```

for a full miss path.

- [ ] **Step 2: Add a success case where OpenAlex crosswalk prevents later fallbacks**

Add a test where:

- the current related work is DOI-backed
- `openalex_client.find_related_work_preprint_arxiv_url(...)` returns `https://arxiv.org/abs/2401.12345`

Assert that:

- the final resolved row uses that arXiv URL
- arXiv title search is not called
- Hugging Face search is not called
- positive cache write-back still hits both `openalex_work` and `doi`

- [ ] **Step 3: Run the focused relation tests to verify they fail**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q -k "openalex_crosswalk or hf_fallback or transient_hf_failures or both_miss"
```

Expected:

```text
FAIL
```

because the current ladder does not include the new OpenAlex step.

- [ ] **Step 4: Insert the new OpenAlex step into `resolve_related_work_title_to_arxiv()`**

Update `src/arxiv_relations/title_resolution.py` so the order becomes:

1. direct OpenAlex hit handled upstream as today
2. OpenAlex crosswalk helper
3. arXiv title search
4. Hugging Face JSON search

The function should:

- accept `openalex_client` as an optional dependency
- attempt the OpenAlex crosswalk before title-search fallbacks
- return a resolved canonical arXiv URL immediately on explicit OpenAlex evidence
- preserve the current resolved-title lookup behavior through `arxiv_client.get_title()`

- [ ] **Step 5: Preserve current negative-cache behavior**

Make sure the new OpenAlex step does not wrongly negative-cache transient upstream failures. Only a confirmed end-to-end miss after the whole ladder should remain negative-cacheable.

- [ ] **Step 6: Re-run the focused relation tests**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q -k "openalex_crosswalk or hf_fallback or transient_hf_failures or both_miss"
```

Expected:

```text
PASS
```

### Task 4: Wire the new dependency through the relation pipeline

**Files:**
- Modify: `src/arxiv_relations/pipeline.py`
- Modify: `tests/test_arxiv_relations.py`

- [ ] **Step 1: Update the pipeline call site**

Pass `openalex_client` into `resolve_related_work_title_to_arxiv()` from `_resolve_related_work_row()` while leaving existing cache key collection and retained-row fallback logic unchanged.

- [ ] **Step 2: Add a regression case covering the end-to-end pipeline path**

Add one pipeline-level test proving a DOI-backed related work can now resolve through:

- OpenAlex candidate extraction
- OpenAlex crosswalk hit
- cache write-back
- final `PaperSeed` conversion

without using the arXiv or Hugging Face search branches.

- [ ] **Step 3: Run the full relation test file**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q
```

Expected:

```text
PASS
```

### Task 5: Verify blast radius and real-path behavior

**Files:**
- Modify only if needed: `tests/test_main.py`

- [ ] **Step 1: Run the narrow regression suite**

Run:

```bash
uv run pytest tests/test_openalex.py tests/test_arxiv_relations.py tests/test_main.py -q
```

Expected:

- OpenAlex helper tests pass
- relation ladder tests pass
- main export wiring still passes

- [ ] **Step 2: Run the full test suite**

Run:

```bash
uv run pytest -q
```

Expected:

```text
PASS
```

- [ ] **Step 3: Re-run the real isolated `2312.03203` export**

Use the same isolated temp-directory pattern already validated on `master`, so stale repo-root `cache.db` cannot mask behavior. Compare the new citations and references CSVs against the current rerun pair and inspect whether DOI-heavy rows decrease, especially in citations.

- [ ] **Step 4: Summarize outcome against the benchmark**

Record:

- total arXiv vs DOI counts before and after
- representative rows that now crosswalk through OpenAlex before title-search fallback
- any remaining dominant DOI categories that still look like true non-arXiv outputs
