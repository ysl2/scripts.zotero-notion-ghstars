from dataclasses import dataclass
from types import SimpleNamespace

from src.shared.discovery import resolve_arxiv_id_by_title, resolve_github_url
from src.shared.github import extract_owner_repo, normalize_github_url
from src.shared.paper_identity import build_arxiv_abs_url, normalize_arxiv_url, normalize_semanticscholar_paper_url


@dataclass(frozen=True)
class PaperEnrichmentRequest:
    title: str
    raw_url: str
    existing_github_url: str | None
    allow_title_search: bool
    allow_github_discovery: bool


@dataclass(frozen=True)
class PaperEnrichmentResult:
    title: str
    raw_url: str
    normalized_url: str | None
    github_url: str | None
    github_source: str | None
    stars: int | None
    reason: str | None


async def process_single_paper(
    request: PaperEnrichmentRequest,
    *,
    discovery_client,
    github_client,
    arxiv_client=None,
    content_cache=None,
) -> PaperEnrichmentResult:
    title = (request.title or "").strip()
    raw_url = (request.raw_url or "").strip()

    normalized_url = _normalize_paper_url(raw_url)
    title_search_error = None
    if normalized_url is None and request.allow_title_search:
        arxiv_id, _source, title_search_error = await resolve_arxiv_id_by_title(
            title,
            discovery_client=discovery_client,
            arxiv_client=arxiv_client,
        )
        if arxiv_id:
            normalized_url = build_arxiv_abs_url(arxiv_id)

    github_url = None
    github_source = None
    existing_value = (request.existing_github_url or "").strip()
    if existing_value:
        github_source = "existing"
        github_url = normalize_github_url(existing_value)
        if not github_url:
            return PaperEnrichmentResult(
                title=title,
                raw_url=raw_url,
                normalized_url=normalized_url,
                github_url=existing_value,
                github_source=github_source,
                stars=None,
                reason="Existing Github URL is not a valid GitHub repository",
            )
    else:
        if normalized_url is None:
            return PaperEnrichmentResult(
                title=title,
                raw_url=raw_url,
                normalized_url=None,
                github_url=None,
                github_source=None,
                stars=None,
                reason=title_search_error or "No valid arXiv URL found",
            )

        if request.allow_github_discovery:
            github_url = await _resolve_github(title, normalized_url, discovery_client)

        if not github_url:
            return PaperEnrichmentResult(
                title=title,
                raw_url=raw_url,
                normalized_url=normalized_url,
                github_url=None,
                github_source=None,
                stars=None,
                reason="No Github URL found from discovery",
            )

        github_source = "discovered"
        normalized_github = normalize_github_url(github_url)
        if not normalized_github:
            return PaperEnrichmentResult(
                title=title,
                raw_url=raw_url,
                normalized_url=normalized_url,
                github_url=github_url,
                github_source=github_source,
                stars=None,
                reason="Discovered URL is not a valid GitHub repository",
            )
        github_url = normalized_github

    owner_repo = extract_owner_repo(github_url)
    if not owner_repo:
        reason = "Existing Github URL is not a valid GitHub repository"
        if github_source == "discovered":
            reason = "Discovered URL is not a valid GitHub repository"
        return PaperEnrichmentResult(
            title=title,
            raw_url=raw_url,
            normalized_url=normalized_url,
            github_url=github_url,
            github_source=github_source,
            stars=None,
            reason=reason,
        )

    await _warm_content_cache(normalized_url, content_cache)

    stars, error = await github_client.get_star_count(*owner_repo)
    if error:
        return PaperEnrichmentResult(
            title=title,
            raw_url=raw_url,
            normalized_url=normalized_url,
            github_url=github_url,
            github_source=github_source,
            stars=None,
            reason=error,
        )

    return PaperEnrichmentResult(
        title=title,
        raw_url=raw_url,
        normalized_url=normalized_url,
        github_url=github_url,
        github_source=github_source,
        stars=stars,
        reason=None,
    )


async def _resolve_github(name: str, url: str, discovery_client) -> str | None:
    if discovery_client is None:
        return None
    seed = SimpleNamespace(name=name, url=url)
    resolver = getattr(discovery_client, "resolve_github_url", None)
    if callable(resolver):
        return await resolver(seed)
    return await resolve_github_url(seed, discovery_client)


def _normalize_paper_url(url: str) -> str | None:
    return normalize_arxiv_url(url) or normalize_semanticscholar_paper_url(url)


async def _warm_content_cache(normalized_url: str | None, content_cache) -> None:
    arxiv_url = normalize_arxiv_url(normalized_url or "")
    if arxiv_url is None or content_cache is None:
        return

    warmer = getattr(content_cache, "ensure_local_content_cache", None)
    if not callable(warmer):
        return

    try:
        await warmer(arxiv_url)
    except Exception:
        return
