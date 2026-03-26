# arXiv Advanced Search URL Design

**Goal**

Support `https://arxiv.org/search/advanced?...` as a valid `url -> csv` input so advanced arXiv search result pages can be exported the same way as existing `https://arxiv.org/search/?...` pages.

**Current State**

- arXiv list, catchup, archive month, and plain `/search` URLs are supported.
- `arxiv.org/search/advanced` is rejected at URL detection time.
- The existing arXiv search flow already knows how to:
  - fetch search-result HTML
  - paginate with `start=...`
  - extract arXiv-backed paper links and titles
  - validate completeness against the total result count

**Design Decision**

Treat `/search/advanced` as another arXiv search-results URL shape, not as a separate source type.

That means:

1. URL detection accepts `/search/advanced`.
2. Fetching reuses the existing arXiv search pagination and extraction path.
3. Output filenames derive a readable slug from ordered `terms-*-term` values instead of the plain-search `query=` field.

**Filename Semantics**

- Base prefix remains `arxiv-search-...`
- Query slug for advanced search comes from `terms-0-term`, `terms-1-term`, `terms-2-term`, ... in numeric order
- Empty or missing terms are ignored
- If no terms are present, fall back to `search`
- Search type and ordering keep the existing behavior:
  - `searchtype` defaults to `all`
  - `order` defaults to `relevance`

Example:

- `https://arxiv.org/search/advanced?...terms-0-term=reconstruction&terms-1-term=semantic&terms-2-term=streaming&order=-submitted_date`
  becomes
  `arxiv-search-reconstruction-semantic-streaming-all-submitted-date-<timestamp>.csv`

**Proposed Changes**

- Extend arXiv URL support checks to accept `/search/advanced`.
- Extend arXiv output filename generation to read advanced-search terms.
- Route `/search/advanced` through the existing `_fetch_search_seeds(...)` flow.
- Add regression tests at the source-detection, dispatch, filename, and fetch layers.
- Update README examples to show the new supported URL shape.

**Scope**

In scope:

- `https://arxiv.org/search/advanced?...`
- ordered filename slugs from advanced search terms
- reuse of existing arXiv search HTML parsing and pagination

Out of scope:

- normalizing advanced search URLs into plain `/search`
- supporting arbitrary non-result arXiv advanced search pages
- changing search result parsing rules

**Testing**

- Add source-detection coverage for advanced search URLs.
- Add dispatch coverage proving `main.py` routes advanced search URLs into URL mode.
- Add arXiv-org filename coverage for advanced-search term slugs.
- Add arXiv-org fetch coverage proving advanced URLs page with `start=...` and export a CSV path.
