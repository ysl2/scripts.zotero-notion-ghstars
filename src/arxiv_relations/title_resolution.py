import html as html_lib
import json
import re
from dataclasses import dataclass

from src.shared.discovery import extract_best_huggingface_paper_id_from_search_html
from src.shared.paper_identity import build_arxiv_abs_url


NO_MATCH_TITLE_SEARCH_ERROR = "No arXiv ID found from title search"
HF_DAILYPAPERS_PATTERN = re.compile(r'data-target="DailyPapers"[^>]*data-props="([^"]*)"')


@dataclass(frozen=True)
class RelationTitleResolution:
    arxiv_url: str | None
    resolved_title: str | None
    negative_cacheable: bool


def _is_definitive_huggingface_no_match(search_html: str) -> bool:
    if not search_html or not isinstance(search_html, str):
        return False

    match = HF_DAILYPAPERS_PATTERN.search(search_html)
    if not match:
        return False

    try:
        payload = json.loads(html_lib.unescape(match.group(1)))
    except json.JSONDecodeError:
        return False

    items = payload.get("searchResults")
    if not isinstance(items, list):
        items = payload.get("dailyPapers")
    return isinstance(items, list)


async def resolve_related_work_title_to_arxiv(
    title: str,
    *,
    arxiv_client,
    discovery_client=None,
) -> RelationTitleResolution:
    arxiv_id, _source, arxiv_error = await arxiv_client.get_arxiv_id_by_title_from_api(title)
    if arxiv_id:
        matched_title, _ = await arxiv_client.get_title(arxiv_id)
        return RelationTitleResolution(
            arxiv_url=build_arxiv_abs_url(arxiv_id),
            resolved_title=matched_title or title,
            negative_cacheable=False,
        )

    if arxiv_error != NO_MATCH_TITLE_SEARCH_ERROR:
        return RelationTitleResolution(arxiv_url=None, resolved_title=None, negative_cacheable=False)

    hf_search = getattr(discovery_client, "get_huggingface_search_html", None)
    if not getattr(discovery_client, "huggingface_token", "") or not callable(hf_search):
        return RelationTitleResolution(arxiv_url=None, resolved_title=None, negative_cacheable=False)

    search_html, hf_error = await hf_search(title)
    if hf_error or not search_html:
        return RelationTitleResolution(arxiv_url=None, resolved_title=None, negative_cacheable=False)

    hf_arxiv_id, _hf_source = extract_best_huggingface_paper_id_from_search_html(search_html, title)
    if hf_arxiv_id:
        matched_title, _ = await arxiv_client.get_title(hf_arxiv_id)
        return RelationTitleResolution(
            arxiv_url=build_arxiv_abs_url(hf_arxiv_id),
            resolved_title=matched_title or title,
            negative_cacheable=False,
        )

    return RelationTitleResolution(
        arxiv_url=None,
        resolved_title=None,
        negative_cacheable=_is_definitive_huggingface_no_match(search_html),
    )
