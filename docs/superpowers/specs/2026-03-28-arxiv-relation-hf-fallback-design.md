# ArXiv Relation HF JSON Fallback Design

**Goal**

Update the single-paper arXiv relation-resolution path so its second-layer fallback no longer scrapes the Hugging Face Papers HTML search page. Instead, the relation path should call the structured Hugging Face JSON search endpoint `GET /api/papers/search?q=...&limit=N`, while preserving the current low-blast-radius design, relation-local boundaries, and relation-resolution cache semantics.

**Scope**

In scope:

- keep the existing single-paper arXiv relation mode and output shape unchanged
- keep arXiv API title search as the first resolution layer
- replace only the relation-mode second layer from Hugging Face HTML `/papers?q=...` to Hugging Face JSON `/api/papers/search?q=...&limit=N`
- keep the same relation-local boundary: only the single-paper arXiv relation path should use this fallback
- keep the same positive-cache and negative-cache semantics for relation resolution
- keep the same rule that transient failures are not negative-cacheable
- keep the same canonical output identity: versionless arXiv `abs` URLs
- document the live validation evidence that motivated the change

Out of scope:

- changing URL mode, CSV mode, Notion mode, or GitHub repo discovery behavior
- redesigning `relation_resolution_cache` schema or key strategy
- adding OpenAlex as another relation fallback provider in this design
- changing relation CSV schema or output filenames
- revisiting whether Hugging Face fallback should be gated differently at runtime
- broadening shared title-resolution behavior outside relation mode

**Problem**

The current branch already introduced a relation-mode second layer after arXiv API title search, but that second layer is based on the HTML page `https://huggingface.co/papers?q=<title>`. Live investigation showed that this page is unreliable for programmatic title resolution:

- the HTML page returned a generic Daily Papers page shape rather than query-specific results
- the returned HTML did not contain the expected arXiv id `2312.00451`
- the returned HTML did not contain the target title `FSGS: Real-Time Few-Shot View Synthesis Using Gaussian Splatting`
- the current parser therefore produced no match for the real failing case

By contrast, live testing of `GET https://huggingface.co/api/papers/search?q=<title>&limit=N` returned structured query-specific JSON and resolved the exact mapping:

- title: `FSGS: Real-Time Few-Shot View Synthesis Using Gaussian Splatting`
- mapped result: `2312.00451`

This means the problem is not "Hugging Face has no usable search surface"; the problem is that the current relation path is using the wrong Hugging Face search surface.

**Design Summary**

Keep the relation-resolution flow unchanged except for the second layer:

1. relation mode first calls the relation-specific arXiv API title-search method
2. only if arXiv returns a definitive title-search miss does relation mode attempt Hugging Face fallback
3. relation mode then calls `GET /api/papers/search?q=<title>&limit=N`
4. relation mode scores the returned JSON entries using the same normalized title-matching rules already used for HTML parsing
5. if Hugging Face returns a usable match, relation mode resolves to that canonical arXiv `abs` URL
6. if Hugging Face returns a successful structured miss, relation mode keeps the row unresolved for this run and allows the existing negative-cache logic to record that miss

The provider does not change. The cache does not change. The output does not change. Only the Hugging Face request surface changes.

**Resolution Flow**

For each related work that does not already have a direct arXiv identity from OpenAlex and does not have a positive cache hit:

1. run the existing relation-specific arXiv API title search
2. if arXiv resolves:
   - normalize to canonical versionless `https://arxiv.org/abs/...`
   - return the matched arXiv title and URL
   - do not mark the row as negative-cacheable
3. if arXiv fails with anything other than the definitive no-match error:
   - stop resolution for this run
   - do not call Hugging Face
   - do not mark the row as negative-cacheable
4. if arXiv returns the definitive no-match error:
   - enter the relation-mode Hugging Face fallback branch
5. if the Hugging Face fallback branch is not available under the current runtime gate:
   - stop resolution for this run
   - do not mark the row as negative-cacheable
6. otherwise call:
   - `GET https://huggingface.co/api/papers/search?q=<title>&limit=N`
7. score returned JSON entries by normalized title match
8. if a usable result is found:
   - take the Hugging Face paper id
   - normalize it to canonical versionless arXiv `abs` URL
   - fetch the matched arXiv title through the existing arXiv title lookup path
   - return a resolved relation row
9. if the JSON request succeeds but no acceptable result exists:
   - return unresolved
   - mark the result as negative-cacheable
10. if the JSON request fails transiently or returns unusable payload:
   - return unresolved
   - do not mark the result as negative-cacheable

**Search Endpoint And Matching Rules**

Use the Hugging Face JSON endpoint:

- `GET /api/papers/search?q=<title>&limit=N`

Recommended request shape:

- pass the original related-work title as `q`
- request a small bounded result set such as `limit=3`

The result-selection rule should stay conservative and deterministic:

- normalize the query title and candidate title with the existing title-normalization logic
- accept matches using the same scoring ladder already used in current title matching:
  1. exact normalized-title equality
  2. query contained within candidate title
  3. candidate title contained within query
- choose the highest-scoring candidate rather than blindly trusting rank 1

This keeps the behavioral blast radius small while removing dependence on fragile HTML page structure.

**Cache Semantics**

This design does not change the relation-resolution cache model or meaning.

Keep all existing semantics:

- positive resolution still stores canonical arXiv `abs` URL by `openalex_work` and `doi`
- negative resolution still stores `arxiv_url = NULL`
- fresh negative cache entries still suppress repeated lookups
- positive cache hits still win over negative cache rows on other keys

Keep the current negative-cacheability rules:

- arXiv transient failure: not negative-cacheable
- missing relation-mode Hugging Face branch: not negative-cacheable
- Hugging Face request failure: not negative-cacheable
- Hugging Face successful structured no-match: negative-cacheable

This preserves the intended meaning of the cache: only confirmed misses should suppress later retries.

**Boundaries**

This design should not change:

- relation CSV schema
- relation CSV filename behavior
- non-relation title-resolution flows
- `repo_cache` behavior
- OpenAlex target-work search behavior
- shared GitHub/stars enrichment behavior

The only behavior change is within the existing single-paper relation normalization ladder, and only in the second search layer after arXiv API miss.

**Testing**

Add or update coverage for:

- relation-mode Hugging Face fallback success using JSON search results
- exact real-case mapping for the FSGS title to `2312.00451`
- relation-mode skip when the Hugging Face fallback branch is unavailable under the current runtime gate
- Hugging Face transient request failures remaining non-cacheable
- Hugging Face successful empty JSON result remaining negative-cacheable
- no regression in cache write-back behavior for positive results
- no regression in cache write-back behavior for confirmed misses

Live validation evidence to record in the implementation:

- HTML path `GET /papers?q=<full FSGS title>` returned a generic Daily Papers page and did not contain `2312.00451`
- JSON path `GET /api/papers/search?q=<full FSGS title>&limit=3` returned a structured result whose first item mapped to `2312.00451`

**Rationale**

This is the smallest credible design correction:

- same provider
- same fallback stage
- same cache semantics
- same relation-local boundary
- better structured data
- validated on the real failing FSGS case

An OpenAlex-side rescue path remains a possible later alternative, but it would add a second provider to the relation search ladder. Replacing the current unreliable Hugging Face HTML page scrape with the Hugging Face JSON search endpoint is the lower-blast-radius choice.
