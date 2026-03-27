# ArXiv Citation Reference Export Design

**Goal**

Add a new CLI mode that accepts one single-paper arXiv URL, finds that paper's references and citations via OpenAlex, keeps only arXiv-backed related papers, and writes two CSV files using the existing standard export shape: `Name`, `Url`, `Github`, `Stars`.

**Scope**

In scope:

- one new CLI mode for a single arXiv paper URL
- resolve the input paper title from arXiv metadata
- search OpenAlex by that title and select the first result by relevance
- fetch both:
  - references
  - citations
- keep only related works that can be normalized to canonical arXiv URLs
- reuse the existing Github / Stars enrichment and CSV writing pipeline
- write one CSV for references and one CSV for citations under `./output`
- tests for dispatch, OpenAlex parsing, filtering, and output wiring

Out of scope:

- support for non-arXiv input papers
- keeping non-arXiv related works in the CSV
- a separate script or separate top-level command
- custom CLI flags for OpenAlex query strategy or output naming
- fallback to a second citations data source

**CLI Shape**

The existing single-argument CLI stays in place, but adds a new single-paper arXiv branch:

1. no positional argument:
   - Notion mode
2. one existing `.csv` path:
   - CSV update mode
3. one single-paper arXiv URL:
   - citation/reference export mode
4. one supported collection URL:
   - collection URL to CSV mode

This keeps the user's preferred interface: no new script, no new command family.

**Input Rules**

- accept one single-paper arXiv URL
- normalize it to the project's canonical, versionless arXiv URL form
- reject collection pages such as `list/...`, `search/...`, or `catchup/...`
- reject inputs that do not resolve to one arXiv paper id

The implementation should not overfit to only `/abs/...`; it should recognize any single-paper arXiv URL shape that can be normalized to one paper id.

**OpenAlex Resolution Strategy**

The input URL is not used as the OpenAlex lookup key. Instead:

1. resolve the input paper title from arXiv metadata
2. send that title to OpenAlex work search
3. accept the first returned work as the target work

This follows the user preference for title-based lookup and for taking the first search result rather than failing conservatively when multiple matches are returned.

**Relationship Fetching**

Once the target OpenAlex work is selected:

- references:
  - read the target work's referenced-work identifiers
  - fetch the referenced work objects needed to extract titles and arXiv URLs
- citations:
  - follow the target work's cited-by endpoint and crawl all pages

Both relationship sets should be deduplicated by canonical arXiv URL after normalization.

**ArXiv-Only Filtering**

This first version exports only related works that can be mapped to arXiv papers.

Filtering rules:

1. inspect each related OpenAlex work for an arXiv-backed location or identifier
2. normalize the related paper to the canonical arXiv URL form
3. drop any related work that cannot be normalized to an arXiv URL
4. deduplicate by normalized arXiv URL

This preserves compatibility with the existing arXiv-keyed enrichment pipeline and leaves room for later expansion if non-arXiv works need to be retained.

**Export Reuse**

After filtering, the new mode should convert each related paper into the existing `PaperSeed` shape and then reuse the shared export pipeline:

- shared enrichment:
  - discover Github repo
  - fetch GitHub stars
- shared CSV output:
  - `Name`
  - `Url`
  - `Github`
  - `Stars`
- shared sorting:
  - canonical arXiv URL sort order, same as current URL export behavior

This means the new mode should not introduce a second CSV schema.

**Output Naming**

The new mode writes two CSV files under `./output` in the current working directory, using timestamped names consistent with the existing URL export behavior.

Representative shape:

- `./output/arxiv-2501.12345-references-YYYYMMDDHHMMSS.csv`
- `./output/arxiv-2501.12345-citations-YYYYMMDDHHMMSS.csv`

If the input normalizes to a different canonical id form, the filename should use that normalized arXiv id.

**Code Boundaries**

Recommended module split:

- `openalex/` or equivalent shared module:
  - OpenAlex client
  - title search
  - citations pagination
  - referenced-work detail fetching
- new single-paper pipeline module:
  - input validation
  - arXiv title lookup
  - OpenAlex target-work resolution
  - references/citations collection
  - arXiv-only normalization
  - two CSV export calls
- existing shared export modules remain unchanged where possible

This keeps OpenAlex-specific logic isolated and avoids overloading the current collection-URL adapters with single-paper relationship behavior.

**Configuration**

Add OpenAlex API key support via environment variable.

Recommended variable:

- `OPENALEX_API_KEY`

If the key is absent, the mode may still run without authentication if the API allows it, but the config and client should support the key explicitly so the user's available credential can be used.

**Failure Behavior**

Fail the run explicitly when:

- the input is not a single-paper arXiv URL
- the arXiv title cannot be resolved
- OpenAlex returns no matching work
- OpenAlex references fetch fails
- OpenAlex citations fetch fails

Do not fail the whole run just because some related works are non-arXiv or cannot be normalized; those rows should be skipped.

The mode should only report success after both CSV files are written.

**Testing**

- dispatch tests for the new single-paper arXiv branch
- normalization tests for accepted and rejected arXiv input URLs
- OpenAlex title-search tests proving the first result is selected
- relationship-fetch tests for:
  - references
  - citations pagination
- filtering tests proving non-arXiv works are dropped
- export tests proving:
  - two CSV files are written
  - both use the standard CSV headers
  - shared Github / Stars enrichment is reused
- full `uv run pytest`
