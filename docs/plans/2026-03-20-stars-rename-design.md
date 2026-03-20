# Stars Rename Design

**Goal:** Rename the runtime and repository-facing star-count terminology to `Stars`, including the actual Notion number property name.

**Architecture:** Keep the current single-pass page processing pipeline unchanged, but switch the shared star-property constant to `Stars` and update every user-facing reference to match. After the change, the script should only read from and write to `Stars`, and repository docs should stop describing the tool as a “Stars updater” with any older star-property phrasing left behind.

**Scope / Rules:**
- Change the runtime Notion property name to `Stars`.
- Preserve existing `Github` property behavior and AlphaXiv fallback logic.
- Update tests so fixtures and assertions reflect the new property name.
- Update README and design/plan docs so repository terminology is consistently `Stars`.
- Do not add backward compatibility for the previous property name in this change.

## Proposed Flow

1. Query pages from Notion as before.
2. Read the current star count from the `Stars` property.
3. Resolve the GitHub repository URL using the existing `Github` / AlphaXiv logic.
4. Fetch the latest star count from GitHub.
5. Update Notion:
   - existing GitHub URL: update `Stars` only
   - AlphaXiv-discovered GitHub URL: update both `Github` and `Stars`

## Implementation Options

### Option A — Direct string replacement everywhere
- Pros: fastest possible change
- Cons: keeps property names duplicated across code and docs, making future renames error-prone

### Option B — Introduce shared property-name constants and update all call sites (recommended)
- Pros: one source of truth for Notion property names, lower risk of future drift, still small in scope
- Cons: slightly larger patch than pure string replacement

### Option C — Add config-driven property names
- Pros: flexible for multiple database schemas
- Cons: unnecessary complexity for a single explicit rename

**Recommendation:** Option B. The repository is small, so a shared constant keeps the actual property rename localized while the rest of the repository can be updated with straightforward text replacements.

## Testing

- Update unit tests to use `Stars` fixtures before changing production code.
- Run the focused unittest suite to verify the failing test first.
- Re-run the same suite after the code change and confirm it passes.
- Search the repository for lingering old property-name references and remove them from active repository files.

## Migration Note

This change assumes the Notion database column is renamed to `Stars` before or alongside script execution. Until the database schema matches, runtime star reads/writes will not hit the intended property.
