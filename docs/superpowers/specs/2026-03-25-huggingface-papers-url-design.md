# Hugging Face Papers URL Mode Design

**Goal**

Add a new `huggingface.co/papers/...` URL input mode that exports the corresponding paper collection to CSV while reusing the existing enrichment and CSV-writing pipeline.

**User Input Contract**

The input will always be a Hugging Face Papers collection URL copied from the frontend, for example:

- `https://huggingface.co/papers/trending`
- `https://huggingface.co/papers/trending?q=semantic`
- `https://huggingface.co/papers/month/2026-03?q=semantic`

The input will not be a single-paper page such as `/papers/<arxiv_id>`.

**Design Principles**

1. Keep source-specific logic separate.
   - arXiv Xplorer URL ingestion stays in its own adapter
   - Hugging Face Papers URL ingestion gets its own adapter
   - the two should not be merged into one file full of conditionals

2. Reuse the existing shared pipeline wherever behavior is actually shared.
   - paper seed model
   - repo discovery
   - stars lookup
   - progress output
   - CSV writing

3. Preserve expansion-friendly structure.
   - the repository should have a generic “URL collection export” layer
   - each site contributes only parsing/fetching logic for turning its URL into `PaperSeed[]`

**Architecture**

Create a site-adapter layer under the URL export flow:

- `url_to_csv/runner.py`
  - stays as the single URL export runner
  - dispatches to a source adapter based on the input URL

- `url_to_csv/pipeline.py`
  - becomes source-agnostic
  - asks a selected adapter for `FetchedSeedsResult`
  - passes seeds into shared export logic

- `url_to_csv/arxivxplorer.py`
  - remains the arXiv Xplorer adapter only

- `url_to_csv/huggingface_papers.py`
  - new Hugging Face Papers adapter
  - validates supported Hugging Face Papers collection URLs
  - derives output CSV filename from the source URL
  - fetches the collection page and/or official public JSON endpoint as appropriate
  - extracts the displayed paper list into `PaperSeed`

**Data Strategy**

For Hugging Face Papers:

1. Treat the frontend URL as the source of truth.
2. Prefer official public JSON endpoints where they clearly match the page behavior.
   - `/api/papers/search?q=...` is public and can support search-style pages
3. For page types without a matching public listing endpoint, parse the collection page HTML to recover the displayed paper links.
4. Normalize every paper to:
   - `name`
   - canonical versionless `https://arxiv.org/abs/<id>`

**Scope**

This feature adds support for Hugging Face collection pages only.
It does not add:

- plain keyword input mode
- single-paper Hugging Face page input
- a new CSV schema
- a new enrichment policy

**Testing**

- add adapter tests for supported and unsupported Hugging Face collection URLs
- add fetch/parse tests for Hugging Face collection extraction
- add dispatch tests showing:
  - arXiv Xplorer URL still routes correctly
  - Hugging Face Papers URL routes correctly
  - CSV path still routes correctly
- run full suite after integration
