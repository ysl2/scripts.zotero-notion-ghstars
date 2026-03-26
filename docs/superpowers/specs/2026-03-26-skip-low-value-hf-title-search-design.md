# Skip Low-Value Hugging Face Title Search Design

**Goal**

Remove one low-value Hugging Face network request from GitHub-link discovery without changing successful outcomes.

**Current State**

- For arXiv-backed papers, discovery first fetches `https://huggingface.co/papers/<arxiv_id>`.
- If that page fetch succeeds but no GitHub repo is found, the code still performs a Hugging Face title search.
- The current title-search fallback only helps when it points back to the same arXiv id, which would just re-open the same paper page again.

**Design Decision**

If the direct Hugging Face paper page is fetched successfully and contains no GitHub repo, skip the Hugging Face title-search fallback and continue directly to AlphaXiv.

**Why this is safe**

- The direct paper page already represents the canonical Hugging Face paper endpoint for that arXiv id.
- The current title-search path does not accept an alternative paper id; it only uses the same arXiv id and then re-fetches the same page.
- So after a successful no-repo direct page fetch, the title-search step adds latency but not new information.

**Scope**

In scope:

- skip Hugging Face title search after successful no-repo direct paper-page fetch
- keep title search available when the direct paper-page request fails
- regression tests for both branches

Out of scope:

- changing discovery source order
- parsing GitHub URLs directly out of Hugging Face search results
- changing AlphaXiv fallback behavior

**Testing**

- Update the existing fallback-to-AlphaXiv test so it expects no Hugging Face title search after a successful no-repo paper-page fetch.
- Add a regression test proving title search still runs when the initial direct paper-page request fails.
