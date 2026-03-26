# URL Export Filename Timestamp Design

**Goal**

Make every `url -> csv` export write a timestamped filename in the form `<base>-YYYYMMDDHHMMSS.csv` so each run is traceable and does not overwrite an earlier export from the same source URL shape.

**Current State**

- Each URL source derives its own readable base filename:
  - `arxivxplorer-...`
  - `arxiv-...`
  - `huggingface-papers-...`
  - `semanticscholar-...`
- The shared pipeline reuses the source-provided `csv_path` and writes the final CSV through the common export path.
- Timestamp suffixing does not exist today.

**Design Decision**

Keep source-specific base-name semantics, but unify final filename assembly.

That means:

1. Each source still decides which URL-derived fields belong in the readable base stem.
2. A shared helper becomes responsible for:
   - sanitizing and joining filename parts consistently
   - appending the run timestamp
   - adding the `.csv` suffix
3. The timestamp is added once in the shared `url -> csv` flow, not duplicated in every source adapter.

**Why not fully unify base-name selection**

The sources expose different user-meaningful inputs:

- arXiv Xplorer uses `q`, `cats`, and `year`
- arXiv.org list pages use category + mode
- arXiv.org search pages use query + search type + order
- Hugging Face Papers uses collection path plus optional search text
- Semantic Scholar uses query + year/fos/venue filters

Using one no-branch naming rule for all of them would either:

- collapse to a lossy generic slug of the full URL, or
- force awkward source-independent filenames that are less readable than the current output.

So the right shared boundary is the filename assembly step, not the source metadata selection step.

**Proposed Architecture**

- Add a shared helper module under `src/url_to_csv/` for URL-export filenames.
- Move the common filename-building mechanics there.
- Have each source adapter ask that helper to build the final path from:
  - `output_dir`
  - source-specific base parts or stem
  - run timestamp

**Timestamp Semantics**

- Format: `YYYYMMDDHHMMSS`
- Time source: local process time at export start
- Scope: one timestamp per export invocation
- Placement: before `.csv`

Examples:

- `arxiv-cs.CV-new.csv`
  becomes
  `arxiv-cs.CV-new-20260326110530.csv`

- `semanticscholar-semantic-3d-reconstruction.csv`
  becomes
  `semanticscholar-semantic-3d-reconstruction-20260326110530.csv`

**Scope**

In scope:

- all `url -> csv` sources
- shared final filename assembly
- tests that currently assert exact output names for URL export

Out of scope:

- `csv_update` mode
- Notion sync outputs
- changing the meaning of source-specific base-name fields

**Testing**

Add focused tests for:

- shared timestamp suffix formatting
- stable source-specific base stems still being preserved
- `export_url_to_csv()` returning timestamped paths for each supported URL source

**Why this design**

- It removes duplicated filename mechanics without erasing source-specific readability.
- It keeps the change narrow: URL export behavior changes, update-in-place CSV flows do not.
- It gives the user the requested timestamped outputs while preserving current naming intent.
