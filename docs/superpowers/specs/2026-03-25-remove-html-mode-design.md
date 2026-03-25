# Remove HTML Mode Design

**Goal**

Remove the legacy `html -> csv` execution path so the repository only supports three operational modes:
- no input -> Notion sync
- arXiv Xplorer URL input -> CSV export
- CSV input -> in-place CSV update

**Current Problem**

The `html_to_csv` package is no longer just an old mode. It also contains shared models, CSV writing, and the arXiv client used by other paths. That makes the dependency graph misleading: active workflows still depend on a supposedly deprecated feature package.

**Design**

1. Move reusable types and helpers out of `html_to_csv` into `shared`.
   - paper dataclasses and sort helper move to `shared/papers.py`
   - CSV writing moves to `shared/csv_io.py`
   - arXiv API client moves to `shared/arxiv.py`

2. Keep URL-specific behavior in `url_to_csv`.
   - arXiv Xplorer URL parsing
   - paging through the search API
   - mapping search results into paper seeds
   - delegating enrichment and CSV writing to shared export code

3. Keep CSV-specific behavior in `csv_update`.
   - preserve unrelated columns
   - use canonical arXiv URL semantics
   - if `Github` exists, skip discovery and update `Stars`
   - if `Github` is missing, discover repo by arXiv URL and update both

4. Keep Notion-specific behavior in `notion_sync`.
   - page lookup and updates remain Notion-owned
   - repo/stars discovery still keys off arXiv URL
   - title-to-arXiv fallback uses `shared/arxiv.py`

5. Delete the HTML mode itself.
   - `main.py` no longer accepts `.html`
   - remove HTML runner/pipeline/parser
   - remove HTML-specific tests

**Resulting Structure**

- `shared/`: reusable clients, paper models, CSV IO, enrichment, progress, identity
- `url_to_csv/`: arXiv Xplorer ingestion only
- `csv_update/`: CSV in-place update only
- `notion_sync/`: Notion sync only

**Testing**

- update dispatch tests to cover only Notion, URL, and CSV
- update concurrency tests to assert only remaining modes
- add shared tests for moved helpers where coverage would otherwise be lost
- run full pytest suite after cleanup
