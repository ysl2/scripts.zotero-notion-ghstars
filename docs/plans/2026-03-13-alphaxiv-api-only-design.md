# AlphaXiv API-Only GitHub Discovery Design

**Goal:** Replace the current fallback discovery chain so pages with empty or `WIP` `Github` values discover repository links only through AlphaXiv's API, not by scanning arXiv abstract text or scraping AlphaXiv HTML pages.

**Architecture:** Keep the single-entry per-page processing pipeline, but narrow the fallback resolution path. Existing valid GitHub URLs continue to use the same star refresh path. Empty/`WIP` rows will extract an arXiv id, call the AlphaXiv API using an API key from environment, inspect the API response for implementation/resource URLs, and if a valid GitHub repository is found, update both `Github` and `Stars`.

**Scope / Rules:**
- Existing valid GitHub repository URLs stay on the current direct star-update path.
- Empty or `WIP` `Github` values trigger AlphaXiv API lookup only.
- Do not scan paper abstracts for GitHub URLs anymore.
- Do not fetch `alphaxiv.org/resources/...` HTML anymore.
- Any other non-empty `Github` value remains untouched.
- AlphaXiv API key must come from environment, not hardcoded.

## Proposed Flow

1. Read current `Github` value and classify it.
2. If `valid_github`, use existing URL directly.
3. If `empty` or `wip`:
   - extract arXiv id from page properties
   - call AlphaXiv API using the arXiv id
   - inspect returned JSON for candidate GitHub URLs from implementation/resource fields
   - if found, normalize URL and continue
   - if not found, skip with a clear reason
4. Extract owner/repo from the final GitHub URL.
5. Query GitHub API for stars.
6. Update Notion:
   - existing GitHub URL → update `Stars` only
   - AlphaXiv-discovered GitHub URL → update `Github` + `Stars`

## Candidate API Sources

The AlphaXiv API documentation is available via:
- `https://api-dev.alphaxiv.org/api.json`

Observed useful endpoints:
- `GET /papers/v3/{unresolved}`
- `GET /v2/papers/{upid}/metadata`
- `GET /v2/papers/{upid}/ingest`

Primary candidate should be `GET /papers/v3/{arxiv_id}` because it returns top-level paper data plus `resources` and related identifiers in one request.

## Data Extraction Strategy

Look for GitHub URLs in a small ordered set of API payload locations, for example:
- `resources[*].url`
- nested implementation/resource URL fields if present
- as a final safety net, recursively scan returned JSON string values for GitHub repo URLs

The extraction helper should return the first normalized valid repository URL.

## Implementation Options

### Option A — Call one AlphaXiv endpoint and recursively scan JSON strings (recommended)
- Pros: resilient to response-shape drift, minimal endpoint count, simplest code path
- Cons: slightly less explicit than field-by-field parsing

### Option B — Parse only known explicit fields like `resources[*].url`
- Pros: very clean semantics
- Cons: brittle if AlphaXiv stores GitHub links in a different field for some papers

### Option C — Call multiple AlphaXiv endpoints and merge results
- Pros: highest possible recall
- Cons: more requests, more complexity, likely unnecessary initially

**Recommendation:** Option A, with `GET /papers/v3/{arxiv_id}` as the primary source and recursive JSON scanning for GitHub URLs.

## Error Handling / Reporting

Add or update reasons such as:
- `Missing ALPHAXIV_API_KEY`
- `No arXiv ID found for AlphaXiv API lookup`
- `AlphaXiv API error (<status>)`
- `No Github URL found in AlphaXiv API`

Rows skipped because the API has no GitHub should remain minor skips, not major failures.

## Security / Config

Add a new environment variable:
- `ALPHAXIV_API_KEY`

Do not print the key. README should document it as optional but required for AlphaXiv fallback discovery.
