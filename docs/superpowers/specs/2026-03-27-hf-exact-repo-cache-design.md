# HF Exact Repo Cache Design

**Goal**

Replace Hugging Face search fallback with a project-level persistent cache keyed by canonical arXiv URL, so repeated runs reuse confirmed GitHub repo mappings and negative evidence from exact HF checks.

**Design Decision**

- arXiv-backed repo discovery will use only Hugging Face exact API: `GET /api/papers/{arxiv_id}`
- a new SQLite cache at project root `cache.db` will be shared by URL, CSV, and Notion modes
- cache records both:
  - confirmed `arxiv_url -> github_url`
  - how many times Hugging Face exact returned success-without-repo for that arXiv URL

**Cache Semantics**

- cache key: canonical, versionless arXiv URL
- if cache has a non-empty `github_url`, discovery returns it immediately
- if cache has empty `github_url` and `hf_exact_no_repo_count` has reached the configured threshold, discovery returns no repo immediately
- otherwise discovery performs one HF exact request
- if HF exact succeeds and returns `githubRepo`, store the repo and reset the no-repo count
- if HF exact succeeds with no `githubRepo`, increment the no-repo count
- if HF exact fails transiently, do not increment the no-repo count

**Scope**

In scope:

- new SQLite-backed persistent repo cache at `cache.db`
- exact-only HF discovery for arXiv URLs
- shared cache wiring for URL, CSV, and Notion modes
- tests for cache hit, threshold skip, successful repo persistence, and no-repo counting
- ignore `cache.db` in git

Out of scope:

- caching GitHub stars
- TTL / expiration policy
- CLI flags for cache path or threshold
- Semantic Scholar discovery changes

**Testing**

- add focused discovery tests for cache hit and threshold behavior
- add repo-cache tests for storing found repos and incrementing successful no-repo exact checks
- update or remove old HF search fallback tests
- run targeted tests, then full `uv run pytest`
