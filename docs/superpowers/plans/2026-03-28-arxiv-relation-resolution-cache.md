# ArXiv Relation Resolution Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global cache for single-paper arXiv relation resolution so repeated citation/reference exports reuse cached `related work -> arxiv_url` results, skip fresh known misses, and use arXiv API title search on cache misses.

**Architecture:** Keep the existing `repo_cache` untouched and add one new sqlite-backed cache store dedicated to relation resolution. Wire the new store and the new `ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS` setting through shared runtime, then use them only inside the single-paper arXiv relation pipeline. To minimize blast radius, add a relation-specific arXiv API title-search method instead of changing broader Hugging Face or HTML-search title-resolution behavior used by other modes.

**Tech Stack:** Python, sqlite3, aiohttp, pytest

---

**File Structure**

- Create: `src/shared/relation_resolution_cache.py`
  Responsibility: own the new `relation_resolution_cache` table schema, row model, read/write helpers, and negative-cache freshness checks.
- Modify: `src/shared/settings.py`
  Responsibility: define `ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS = 30` next to `HF_EXACT_NO_REPO_RECHECK_DAYS`.
- Modify: `src/shared/runtime.py`
  Responsibility: parse the new env var, open the new cache store, and expose it in `RuntimeClients`.
- Modify: `src/shared/arxiv.py`
  Responsibility: add a relation-specific arXiv API title-search method that uses `extract_best_arxiv_id_from_feed`.
- Modify: `src/arxiv_relations/pipeline.py`
  Responsibility: consult the new cache, apply hit-vs-negative precedence, call the new arXiv API title-search method on misses, and backfill all available keys.
- Modify: `src/arxiv_relations/runner.py`
  Responsibility: pass the new runtime cache/config into the relation export entrypoint.
- Modify: `README.md`
  Responsibility: document the new env var and explain what it controls.
- Modify: `.env.example`
  Responsibility: expose the new env var with the default `30`.
- Create: `tests/test_relation_resolution_cache.py`
  Responsibility: unit-test cache schema, hit storage, miss storage, and freshness checks.
- Modify: `tests/test_main.py`
  Responsibility: verify runtime config parsing and runtime client wiring for the new setting/store.
- Modify: `tests/test_shared_arxiv.py`
  Responsibility: verify the new arXiv API title-search method uses `https://export.arxiv.org/api/query`.
- Modify: `tests/test_arxiv_relations.py`
  Responsibility: verify cache-aware relation resolution, positive-hit precedence, negative-cache skipping, stale miss rechecks, and write-back behavior.

### Task 1: Add Relation-Resolution Cache Store And Runtime Tests

**Files:**
- Create: `tests/test_relation_resolution_cache.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write the failing cache-store tests**

```python
from datetime import datetime, timedelta, timezone

from src.shared.relation_resolution_cache import RelationResolutionCacheStore


def test_relation_resolution_cache_store_records_and_reads_positive_mapping(tmp_path):
    store = RelationResolutionCacheStore(tmp_path / "cache.db")

    store.record_resolution(
        key_type="openalex_work",
        key_value="https://openalex.org/W123",
        arxiv_url="https://arxiv.org/abs/2501.12345",
    )

    entry = store.get("openalex_work", "https://openalex.org/W123")

    assert entry is not None
    assert entry.arxiv_url == "https://arxiv.org/abs/2501.12345"
    assert entry.checked_at is not None


def test_relation_resolution_cache_store_records_negative_mapping(tmp_path):
    store = RelationResolutionCacheStore(tmp_path / "cache.db")

    store.record_resolution(
        key_type="doi",
        key_value="https://doi.org/10.1000/example",
        arxiv_url=None,
    )

    entry = store.get("doi", "https://doi.org/10.1000/example")

    assert entry is not None
    assert entry.arxiv_url is None
    assert entry.checked_at is not None


def test_relation_resolution_cache_negative_freshness_uses_days_threshold():
    recent = datetime.now(timezone.utc).isoformat()
    stale = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()

    assert RelationResolutionCacheStore.is_negative_cache_fresh(recent, 30) is True
    assert RelationResolutionCacheStore.is_negative_cache_fresh(stale, 30) is False
```

- [ ] **Step 2: Write the failing runtime-config tests**

```python
from src.shared.runtime import load_runtime_config


def test_load_runtime_config_reads_relation_resolution_recheck_days():
    config = load_runtime_config(
        {
            "ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS": "30",
        }
    )

    assert config["arxiv_relation_no_arxiv_recheck_days"] == 30


def test_load_runtime_config_defaults_relation_resolution_recheck_days():
    config = load_runtime_config({})

    assert config["arxiv_relation_no_arxiv_recheck_days"] == 30
```

- [ ] **Step 3: Run focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_relation_resolution_cache.py tests/test_main.py -q
```

Expected:

```text
FAIL
```

with import or key errors because `RelationResolutionCacheStore` and `arxiv_relation_no_arxiv_recheck_days` do not exist yet.

- [ ] **Step 4: Implement the new cache store and runtime parsing**

```python
# src/shared/relation_resolution_cache.py
@dataclass(frozen=True)
class RelationResolutionCacheEntry:
    key_type: str
    key_value: str
    arxiv_url: str | None
    checked_at: str


class RelationResolutionCacheStore:
    def get(self, key_type: str, key_value: str) -> RelationResolutionCacheEntry | None:
        row = self.connection.execute(
            """
            SELECT key_type, key_value, arxiv_url, checked_at
            FROM relation_resolution_cache
            WHERE key_type = ? AND key_value = ?
            """,
            (key_type, key_value),
        ).fetchone()
        if row is None:
            return None
        return RelationResolutionCacheEntry(
            key_type=row["key_type"],
            key_value=row["key_value"],
            arxiv_url=row["arxiv_url"],
            checked_at=row["checked_at"],
        )

    def record_resolution(
        self,
        *,
        key_type: str,
        key_value: str,
        arxiv_url: str | None,
    ) -> None:
        checked_at = _utc_now()
        self.connection.execute(
            """
            INSERT INTO relation_resolution_cache (key_type, key_value, arxiv_url, checked_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key_type, key_value) DO UPDATE SET
                arxiv_url = excluded.arxiv_url,
                checked_at = excluded.checked_at
            """,
            (key_type, key_value, arxiv_url, checked_at),
        )
        self.connection.commit()

    @staticmethod
    def is_negative_cache_fresh(checked_at: str | None, recheck_days: int) -> bool:
        if not checked_at:
            return False
        parsed = datetime.fromisoformat(checked_at)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < parsed + timedelta(days=recheck_days)
```

```python
# src/shared/settings.py
DEFAULT_CONCURRENT_LIMIT = 10
HF_EXACT_NO_REPO_RECHECK_DAYS = 7
ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS = 30
REPO_CACHE_DB_PATH = "cache.db"
```

```python
# src/shared/runtime.py
from src.shared.relation_resolution_cache import RelationResolutionCacheStore
from src.shared.settings import (
    ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS,
    HF_EXACT_NO_REPO_RECHECK_DAYS,
    REPO_CACHE_DB_PATH,
)


@dataclass(frozen=True)
class RuntimeClients:
    session: object
    repo_cache: RepoCacheStore
    relation_resolution_cache: RelationResolutionCacheStore
    discovery_client: object
    github_client: object
```

- [ ] **Step 5: Re-run focused tests to verify they pass**

Run:

```bash
uv run pytest tests/test_relation_resolution_cache.py tests/test_main.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_relation_resolution_cache.py tests/test_main.py src/shared/relation_resolution_cache.py src/shared/settings.py src/shared/runtime.py
git commit -m "feat: add relation resolution cache store"
```

### Task 2: Add Relation-Specific arXiv API Title Search

**Files:**
- Modify: `src/shared/arxiv.py`
- Modify: `tests/test_shared_arxiv.py`

- [ ] **Step 1: Write the failing arXiv API title-search test**

```python
@pytest.mark.anyio
async def test_get_arxiv_id_by_title_from_api_uses_feed_results():
    class FakeResponse:
        def __init__(self, status: int, text: str):
            self.status = status
            self._text = text

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return self._text

    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None):
            self.calls.append((url, params))
            assert url == "https://export.arxiv.org/api/query"
            return FakeResponse(
                200,
                \"\"\"
                <feed xmlns="http://www.w3.org/2005/Atom">
                  <entry>
                    <id>http://arxiv.org/abs/2312.00451v1</id>
                    <title>FSGS: Real-Time Few-shot View Synthesis using Gaussian Splatting</title>
                  </entry>
                </feed>
                \"\"\",
            )

    client = ArxivClient(FakeSession(), max_concurrent=1, min_interval=0)

    arxiv_id, source, error = await client.get_arxiv_id_by_title_from_api(
        "FSGS: Real-Time Few-Shot View Synthesis Using Gaussian Splatting"
    )

    assert (arxiv_id, source, error) == ("2312.00451", "title_search_exact", None)
```

- [ ] **Step 2: Run the focused arXiv test to verify it fails**

Run:

```bash
uv run pytest tests/test_shared_arxiv.py -q
```

Expected:

```text
FAIL
```

with `AttributeError` because `get_arxiv_id_by_title_from_api` does not exist yet.

- [ ] **Step 3: Implement the new API-based title-search method without changing the existing HTML-search method**

```python
class ArxivClient:
    async def get_arxiv_id_by_title_from_api(
        self,
        title: str,
    ) -> tuple[str | None, str | None, str | None]:
        if not title:
            return None, None, "Missing title"

        feed_xml, error = await self._request_text(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": f'ti:"{title}"',
                "start": "0",
                "max_results": "10",
            },
            retry_prefix="arXiv metadata query",
        )
        if error:
            return None, None, error

        arxiv_id, source = extract_best_arxiv_id_from_feed(feed_xml, title)
        if not arxiv_id:
            return None, None, "No arXiv ID found from title search"
        return arxiv_id, source, None
```

- [ ] **Step 4: Re-run the focused arXiv test to verify it passes**

Run:

```bash
uv run pytest tests/test_shared_arxiv.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit**

```bash
git add src/shared/arxiv.py tests/test_shared_arxiv.py
git commit -m "feat: add arxiv api title search for relations"
```

### Task 3: Integrate Cache-Aware Resolution Into The Relation Pipeline

**Files:**
- Modify: `src/arxiv_relations/pipeline.py`
- Modify: `src/arxiv_relations/runner.py`
- Modify: `tests/test_arxiv_relations.py`

- [ ] **Step 1: Write the failing pipeline tests for cache hits, fresh misses, and write-back**

```python
@pytest.mark.anyio
async def test_normalize_related_works_uses_positive_cache_before_title_search():
    cache = FakeRelationResolutionCache(
        {
            ("openalex_work", "https://openalex.org/W9"): SimpleNamespace(
                key_type="openalex_work",
                key_value="https://openalex.org/W9",
                arxiv_url="https://arxiv.org/abs/2312.00451",
                checked_at="2026-03-28T00:00:00+00:00",
            )
        }
    )

    seeds = await normalize_related_works_to_seeds(
        [{"id": "R9"}],
        openalex_client=FakeOpenAlexClient(),
        arxiv_client=FakeArxivClientThatMustNotSearch(),
        relation_resolution_cache=cache,
        arxiv_relation_no_arxiv_recheck_days=30,
    )

    assert seeds == [
        PaperSeed(
            name="Cached Arxiv Title",
            url="https://arxiv.org/abs/2312.00451",
        )
    ]


@pytest.mark.anyio
async def test_normalize_related_works_skips_api_when_negative_cache_is_fresh():
    recent = datetime.now(timezone.utc).isoformat()
    cache = FakeRelationResolutionCache(
        {
            ("doi", "https://doi.org/10.1007/978-3-031-72933-1_9"): SimpleNamespace(
                key_type="doi",
                key_value="https://doi.org/10.1007/978-3-031-72933-1_9",
                arxiv_url=None,
                checked_at=recent,
            )
        }
    )

    seeds = await normalize_related_works_to_seeds(
        [{"id": "R10"}],
        openalex_client=FakeOpenAlexClient(),
        arxiv_client=FakeArxivClientThatMustNotSearch(),
        relation_resolution_cache=cache,
        arxiv_relation_no_arxiv_recheck_days=30,
    )

    assert seeds == [
        PaperSeed(
            name="Fallback Only",
            url="https://doi.org/10.1007/978-3-031-72933-1_9",
        )
    ]


@pytest.mark.anyio
async def test_normalize_related_works_rechecks_stale_negative_and_backfills_all_keys():
    stale = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    cache = FakeRelationResolutionCache(
        {
            ("openalex_work", "https://openalex.org/W11"): SimpleNamespace(
                key_type="openalex_work",
                key_value="https://openalex.org/W11",
                arxiv_url=None,
                checked_at=stale,
            )
        }
    )

    seeds = await normalize_related_works_to_seeds(
        [{"id": "R11"}],
        openalex_client=FakeOpenAlexClient(),
        arxiv_client=FakeArxivClientReturning231200451(),
        relation_resolution_cache=cache,
        arxiv_relation_no_arxiv_recheck_days=30,
    )

    assert seeds == [
        PaperSeed(
            name="Mapped Arxiv Title",
            url="https://arxiv.org/abs/2312.00451",
        )
    ]
    assert cache.record_calls == [
        ("openalex_work", "https://openalex.org/W11", "https://arxiv.org/abs/2312.00451"),
        ("doi", "https://doi.org/10.1007/978-3-031-72933-1_9", "https://arxiv.org/abs/2312.00451"),
    ]
```

- [ ] **Step 2: Run the focused relation tests to verify they fail**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q
```

Expected:

```text
FAIL
```

with signature errors because the relation pipeline does not accept `relation_resolution_cache` or `arxiv_relation_no_arxiv_recheck_days` yet.

- [ ] **Step 3: Implement cache-aware resolution in the relation pipeline**

```python
def _relation_cache_keys(candidate) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if candidate.openalex_url:
        keys.append(("openalex_work", candidate.openalex_url))
    if candidate.doi_url:
        keys.append(("doi", candidate.doi_url))
    return keys


async def _resolve_related_work_row(
    candidate,
    *,
    arxiv_client,
    relation_resolution_cache,
    arxiv_relation_no_arxiv_recheck_days: int,
) -> NormalizedRelatedRow:
    if candidate.direct_arxiv_url:
        resolved_title = candidate.title or candidate.direct_arxiv_url
        return NormalizedRelatedRow(
            title=resolved_title,
            url=candidate.direct_arxiv_url,
            strength=NormalizationStrength.DIRECT_ARXIV,
            original_title=resolved_title,
        )

    cache_keys = _relation_cache_keys(candidate)
    cached_entries = [
        relation_resolution_cache.get(key_type, key_value)
        for key_type, key_value in cache_keys
    ] if relation_resolution_cache is not None else []

    positive_entry = next((entry for entry in cached_entries if entry and entry.arxiv_url), None)
    if positive_entry is not None:
        cached_title, _ = await arxiv_client.get_title(positive_entry.arxiv_url)
        return NormalizedRelatedRow(
            title=cached_title or candidate.title or positive_entry.arxiv_url,
            url=positive_entry.arxiv_url,
            strength=NormalizationStrength.TITLE_SEARCH,
            original_title=candidate.title or cached_title or positive_entry.arxiv_url,
        )

    has_fresh_negative = any(
        entry is not None
        and entry.arxiv_url is None
        and relation_resolution_cache.is_negative_cache_fresh(
            entry.checked_at,
            arxiv_relation_no_arxiv_recheck_days,
        )
        for entry in cached_entries
    )
    if has_fresh_negative:
        fallback_url = _fallback_related_work_url(candidate)
        original_title = candidate.title or fallback_url
        return NormalizedRelatedRow(
            title=original_title,
            url=fallback_url,
            strength=NormalizationStrength.RETAINED_NON_ARXIV,
            original_title=original_title,
        )

    matched_arxiv_id, _, _ = await arxiv_client.get_arxiv_id_by_title_from_api(candidate.title)
    if matched_arxiv_id:
        matched_url = build_arxiv_abs_url(matched_arxiv_id)
        matched_title, _ = await arxiv_client.get_title(matched_arxiv_id)
        if relation_resolution_cache is not None:
            for key_type, key_value in cache_keys:
                relation_resolution_cache.record_resolution(
                    key_type=key_type,
                    key_value=key_value,
                    arxiv_url=matched_url,
                )
        return NormalizedRelatedRow(
            title=matched_title or candidate.title or matched_url,
            url=matched_url,
            strength=NormalizationStrength.TITLE_SEARCH,
            original_title=candidate.title or matched_title or matched_url,
        )

    fallback_url = _fallback_related_work_url(candidate)
    if relation_resolution_cache is not None:
        for key_type, key_value in cache_keys:
            relation_resolution_cache.record_resolution(
                key_type=key_type,
                key_value=key_value,
                arxiv_url=None,
            )
    original_title = candidate.title or fallback_url
    return NormalizedRelatedRow(
        title=original_title,
        url=fallback_url,
        strength=NormalizationStrength.RETAINED_NON_ARXIV,
        original_title=original_title,
    )
```

```python
async def normalize_related_works_to_seeds(
    related_works: list[dict],
    *,
    openalex_client,
    arxiv_client,
    relation_resolution_cache=None,
    arxiv_relation_no_arxiv_recheck_days: int = 30,
) -> list[PaperSeed]:
    candidates = [openalex_client.build_related_work_candidate(work) for work in related_works]
    normalized_rows = await _resolve_related_work_rows(
        candidates,
        arxiv_client=arxiv_client,
        relation_resolution_cache=relation_resolution_cache,
        arxiv_relation_no_arxiv_recheck_days=arxiv_relation_no_arxiv_recheck_days,
    )
    deduped_rows = _dedupe_normalized_rows(normalized_rows)
    return [PaperSeed(name=row.title, url=row.url) for row in deduped_rows]
```

```python
async def export_arxiv_relations_to_csv(
    arxiv_input: str,
    *,
    arxiv_client,
    openalex_client,
    discovery_client,
    github_client,
    relation_resolution_cache=None,
    arxiv_relation_no_arxiv_recheck_days: int = 30,
    output_dir: Path | None = None,
    status_callback=None,
    progress_callback=None,
) -> ArxivRelationsExportResult:
    reference_seeds = await normalize_related_works_to_seeds(
        referenced_works,
        openalex_client=openalex_client,
        arxiv_client=arxiv_client,
        relation_resolution_cache=relation_resolution_cache,
        arxiv_relation_no_arxiv_recheck_days=arxiv_relation_no_arxiv_recheck_days,
    )
    citation_seeds = await normalize_related_works_to_seeds(
        citation_works,
        openalex_client=openalex_client,
        arxiv_client=arxiv_client,
        relation_resolution_cache=relation_resolution_cache,
        arxiv_relation_no_arxiv_recheck_days=arxiv_relation_no_arxiv_recheck_days,
    )
    return ArxivRelationsExportResult(
        arxiv_url=arxiv_url,
        title=title,
        references=references_result,
        citations=citations_result,
    )
```

```python
# src/arxiv_relations/runner.py
result = await export_arxiv_relations_to_csv(
    arxiv_input,
    output_dir=output_dir,
    arxiv_client=arxiv_client,
    openalex_client=openalex_client,
    discovery_client=runtime.discovery_client,
    github_client=runtime.github_client,
    relation_resolution_cache=runtime.relation_resolution_cache,
    arxiv_relation_no_arxiv_recheck_days=config["arxiv_relation_no_arxiv_recheck_days"],
    status_callback=lambda message: print(message, flush=True),
    progress_callback=lambda outcome, total: print_paper_progress(
        outcome,
        total,
        is_minor_reason=is_minor_skip_reason,
    ),
)
```

- [ ] **Step 4: Re-run the focused relation tests to verify they pass**

Run:

```bash
uv run pytest tests/test_arxiv_relations.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 5: Run an integration smoke for the target paper**

Run:

```bash
uv run main.py https://arxiv.org/abs/2312.03203
```

Expected:

```text
Wrote references CSV:
Wrote citations CSV:
```

and no `ArXiv relation export failed` message.

- [ ] **Step 6: Commit**

```bash
git add src/arxiv_relations/pipeline.py src/arxiv_relations/runner.py tests/test_arxiv_relations.py
git commit -m "feat: cache relation arxiv resolution"
```

### Task 4: Document The New Config And Verify No Regression

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Write the failing docs expectations as grep checks**

Run:

```bash
rg -n "ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS" .env.example README.md
```

Expected:

```text
no matches
```

before the doc update.

- [ ] **Step 2: Update `.env.example` and `README.md`**

```dotenv
# .env.example
HF_EXACT_NO_REPO_RECHECK_DAYS=7
ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS=30
OPENALEX_API_KEY=
```

```md
`ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS` controls how many days a cached
"no arXiv match found" relation-resolution result remains fresh before the
single-paper arXiv citation/reference export retries arXiv title search.
```

- [ ] **Step 3: Re-run the grep check to verify the docs now mention the new setting**

Run:

```bash
rg -n "ARXIV_RELATION_NO_ARXIV_RECHECK_DAYS" .env.example README.md
```

Expected:

```text
.env.example
README.md
```

- [ ] **Step 4: Run focused regression tests for runtime, arXiv, relation pipeline, and existing repo cache**

Run:

```bash
uv run pytest tests/test_main.py tests/test_relation_resolution_cache.py tests/test_shared_arxiv.py tests/test_arxiv_relations.py tests/test_repo_cache.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 5: Run the full suite**

Run:

```bash
uv run pytest -q
```

Expected:

```text
PASS
```

- [ ] **Step 6: Commit**

```bash
git add .env.example README.md
git commit -m "docs: document relation resolution cache ttl"
```

- [ ] **Step 7: Final diff hygiene**

Run:

```bash
git diff --check
git status --short
```

Expected:

```text
no diff-check output
working tree clean
```
