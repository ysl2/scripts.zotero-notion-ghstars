# ArXiv Relation OpenAlex Preprint Crosswalk Design

**Goal**

Improve practical recall for single-paper arXiv citation/reference export by moving a narrow OpenAlex-based published-version-to-preprint resolution step ahead of the existing arXiv and Hugging Face title-search fallbacks. The new order should prefer direct OpenAlex evidence first, then attempt an OpenAlex sibling/preprint crosswalk, and only then fall through to arXiv and Hugging Face title search.

**Scope**

In scope:

- keep the existing single-paper arXiv relation export mode and CSV shape unchanged
- keep the current direct OpenAlex arXiv normalization behavior unchanged
- add one new relation-local OpenAlex crosswalk step after direct OpenAlex evidence and before title-search fallbacks
- keep the current arXiv API title-search fallback available after the new OpenAlex step
- keep the current Hugging Face JSON search fallback available after arXiv title search
- preserve the current cache schema and cache-key strategy
- preserve the current retained-row behavior when no arXiv mapping is found

Out of scope:

- broadening non-relation behavior
- redesigning `relation_resolution_cache`
- using title text as a persistent cache key
- adding new CSV columns or provenance fields
- introducing a new external provider beyond OpenAlex, arXiv, and Hugging Face
- adding fuzzy heuristic matching that accepts weak evidence without explicit arXiv signals

**Problem**

The current relation-resolution ladder already handles:

1. direct OpenAlex arXiv evidence
2. arXiv API title search
3. Hugging Face Papers JSON title search
4. retained DOI fallback

This fixed the FSGS case, but real rerun outputs still retain many DOI rows, especially in citations. Investigation so far indicates the remaining DOI-heavy cases are often not caused by title-search ranking alone. Instead, OpenAlex frequently returns a publisher-backed work record whose canonical URL is a DOI, while a separate preprint record may exist elsewhere for the same work.

In other words, many remaining misses are not "find this title on the open web" problems first. They are "start from a published OpenAlex work and crosswalk to its preprint sibling if one exists" problems.

Because relation rows already originate from OpenAlex, the next search layer should first exploit that existing identity graph before falling back to independent title-search providers.

**Design Summary**

The relation-resolution ladder becomes:

1. direct OpenAlex arXiv normalization
2. OpenAlex sibling/preprint crosswalk
3. arXiv API title search
4. Hugging Face Papers JSON search
5. retained DOI / landing page / OpenAlex fallback row

The new second step is intentionally narrow:

- it starts from the current related OpenAlex work
- it attempts to find a sibling or alternate-version OpenAlex work for the same paper
- it only accepts that alternate work if explicit arXiv evidence is present
- if explicit arXiv evidence is absent, the pipeline does not guess

This is not a general-purpose OpenAlex title search pass. It is a version-crosswalk pass that uses OpenAlex as the current source of truth for related works.

**Resolution Flow**

For each related work candidate:

1. if OpenAlex already exposes a direct arXiv-backed identifier, DOI, or location that can be normalized to a canonical versionless arXiv `abs` URL:
   - resolve immediately
   - do not enter any fallback branch
2. otherwise, if the relation-resolution cache has a positive hit on any current key:
   - resolve immediately from cache
3. otherwise, if a fresh negative-cache row exists on any current key:
   - skip further resolution for this run
   - keep the retained row
4. otherwise, attempt the new OpenAlex sibling/preprint crosswalk:
   - start from the current OpenAlex work identity and title
   - query OpenAlex for likely alternate-version candidates for the same work
   - inspect returned candidates for explicit arXiv evidence
5. if the OpenAlex crosswalk yields explicit arXiv evidence:
   - normalize to canonical versionless `https://arxiv.org/abs/...`
   - fetch the matched arXiv title through the existing arXiv-title lookup path if needed
   - write the positive resolution back to the current cache keys
   - stop
6. if the OpenAlex crosswalk produces no acceptable arXiv-backed candidate:
   - continue to arXiv API title search
7. if arXiv title search resolves:
   - normalize to canonical versionless `abs` URL
   - write the positive resolution back to the current cache keys
   - stop
8. if arXiv title search returns a transient failure or error:
   - continue to Hugging Face JSON search
9. if Hugging Face JSON search resolves:
   - normalize to canonical versionless `abs` URL
   - write the positive resolution back to the current cache keys
   - stop
10. if all resolution steps fail:
   - retain the row using the existing URL priority
   - negative-cache only if the final outcome is a confirmed miss rather than a transient upstream failure

**OpenAlex Crosswalk Acceptance Rules**

The new OpenAlex step must stay conservative.

Accept a candidate only when the alternate OpenAlex work exposes explicit arXiv evidence through one of these signals:

1. an OpenAlex `ids` entry that contains an arXiv identifier
2. a DOI of the form `10.48550/arXiv.<id>`
3. a landing page URL or PDF URL on `arxiv.org`

Reject the candidate if:

- it only has a non-arXiv DOI or publisher URL
- it is merely title-similar without explicit arXiv evidence
- multiple plausible alternate works are returned but none carries explicit arXiv evidence

This keeps the new step focused on true crosswalks, not loose inference.

**Matching Strategy Inside OpenAlex**

This design does not require a new global identity graph.

A relation-local implementation may use a narrow OpenAlex query surface such as:

- fetching related/neighboring works from the current OpenAlex identity when supported, or
- a constrained OpenAlex title search seeded by the current title and then filtered down to candidates with explicit arXiv evidence

The important rule is behavioral, not mechanical:

- the step is justified only if it is trying to locate an alternate version of the current OpenAlex work
- it must not behave like a broad independent search layer that accepts weak title similarity alone

**Cache Semantics**

Keep the current cache schema and key strategy:

- key types remain `openalex_work` and `doi`
- positive hits still store canonical versionless arXiv `abs` URLs
- negative hits still store `arxiv_url = NULL`

Keep the current negative-cache discipline:

- direct OpenAlex hit: positive cacheable
- OpenAlex crosswalk explicit hit: positive cacheable
- confirmed end-to-end miss after OpenAlex crosswalk plus title-search fallbacks: negative-cacheable
- transient OpenAlex, arXiv, or Hugging Face failure: not negative-cacheable

This preserves the existing meaning of the cache: only confirmed misses suppress later retries.

**Boundaries**

This design should not change:

- relation CSV schema
- relation CSV filename behavior
- URL mode, CSV mode, or Notion mode behavior
- shared non-relation title-resolution behavior
- `repo_cache` schema or semantics
- GitHub and stars enrichment behavior

The only intended behavior change is within the single-paper arXiv relation normalization ladder.

**Testing**

Add or update coverage for:

- direct OpenAlex arXiv rows still winning before any fallback
- publisher-backed OpenAlex work resolving through the new OpenAlex sibling/preprint crosswalk
- crosswalk candidates without explicit arXiv evidence being rejected
- ambiguous or weak OpenAlex candidate sets not being accepted
- arXiv API title-search fallback still working after OpenAlex crosswalk miss
- Hugging Face fallback still working after both OpenAlex crosswalk and arXiv title-search miss or transient error
- retained DOI fallback still preserving the existing URL priority
- no regression in positive and negative cache write-back behavior

The real rerun CSVs for `2312.03203` should remain the acceptance benchmark: the goal is to materially reduce DOI-heavy false negatives without broadening to weak guesses.

**Rationale**

This is the smallest next-step design that matches the observed failure shape:

- the related-work source already is OpenAlex
- many remaining DOI rows look like published-version records rather than raw title-search misses
- the new step stays inside the existing provider set
- the current arXiv and Hugging Face title-search fallbacks remain available as lower-priority rescue layers

So the design improves recall by exploiting source-local version crosswalks first, instead of immediately leaving OpenAlex and re-solving the same work by title.
