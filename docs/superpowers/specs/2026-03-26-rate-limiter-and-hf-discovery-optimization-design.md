# Rate Limiter And Hugging Face Discovery Optimization Design

**Goal**

Improve request throughput and reduce unnecessary upstream calls without changing external behavior.

**Current State**

- `RateLimiter.acquire()` holds its internal lock while sleeping.
- This preserves spacing between request starts, but it also forces later callers to wait for earlier sleepers before they can reserve their own slot.
- Hugging Face discovery currently fetches `huggingface.co/papers/<arxiv_id>` first, and if that page has no GitHub repo but title search maps back to the same paper id, it fetches the same paper page again.

**Design Decision**

Apply two narrow optimizations:

1. Change `RateLimiter` so callers reserve a future slot under lock, then sleep outside the lock.
2. Skip the duplicate Hugging Face paper-page refetch when the first paper-page request already succeeded and simply did not contain a GitHub repo.

**Why this boundary**

- The rate-limiter change preserves existing min-interval semantics while removing avoidable lock contention.
- The Hugging Face change removes a redundant request without changing fallback order.
- Both optimizations are internal and do not change user-facing CLI behavior or output shape.

**Semantics**

- Rate limiter:
  - still enforces one reserved request-start slot per `min_interval`
  - still serializes slot assignment
  - no longer keeps other waiters out of the reservation path while one task sleeps
- Hugging Face discovery:
  - if direct paper-page fetch succeeds and no repo is found, title search may still run
  - if title search resolves to the same paper id, do not fetch the same paper page again
  - if the direct paper-page fetch failed, a later refetch after title search is still allowed

**Scope**

In scope:

- internal `RateLimiter` scheduling change
- one redundant Hugging Face discovery request removal
- regression tests for both behaviors

Out of scope:

- changing min-interval values
- adding burst-mode rate limiting
- changing discovery source order

**Testing**

- Add a concurrency-focused test proving multiple waiters can reserve slots without being blocked behind one sleeper holding the lock.
- Add a discovery test proving a successful-no-repo Hugging Face paper page is not fetched twice when title search resolves to the same arXiv id.
