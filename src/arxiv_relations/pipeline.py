from dataclasses import dataclass
from pathlib import Path

from src.shared.paper_export import export_paper_seeds_to_csv
from src.shared.paper_identity import build_arxiv_abs_url, extract_arxiv_id, extract_arxiv_id_from_single_paper_url
from src.shared.papers import ConversionResult, PaperSeed
from src.url_to_csv import filenames as url_export_filenames


@dataclass(frozen=True)
class ArxivRelationsExportResult:
    arxiv_url: str
    title: str
    references: ConversionResult
    citations: ConversionResult


def normalize_single_arxiv_input(arxiv_input: str) -> str:
    arxiv_id = extract_arxiv_id_from_single_paper_url(arxiv_input)
    if not arxiv_id:
        raise ValueError(f"Invalid single-paper arXiv URL: {arxiv_input}")
    return build_arxiv_abs_url(arxiv_id)


def build_relations_csv_paths(
    arxiv_url: str,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    arxiv_id = extract_arxiv_id(arxiv_url)
    if not arxiv_id:
        raise ValueError(f"Invalid arXiv URL: {arxiv_url}")

    timestamp = url_export_filenames.current_run_timestamp()
    references_csv_path = url_export_filenames.build_url_export_csv_path(
        ["arxiv", arxiv_id, "references"],
        output_dir=output_dir,
        timestamp=timestamp,
    )
    citations_csv_path = url_export_filenames.build_url_export_csv_path(
        ["arxiv", arxiv_id, "citations"],
        output_dir=output_dir,
        timestamp=timestamp,
    )
    return references_csv_path, citations_csv_path


def normalize_related_works_to_seeds(related_works: list[dict], *, openalex_client) -> list[PaperSeed]:
    seeds: list[PaperSeed] = []
    seen_urls: set[str] = set()
    for related_work in related_works:
        seed = openalex_client.normalize_related_work(related_work)
        if seed is None or seed.url in seen_urls:
            continue
        seen_urls.add(seed.url)
        seeds.append(seed)
    return seeds


async def export_arxiv_relations_to_csv(
    arxiv_input: str,
    *,
    arxiv_client,
    openalex_client,
    discovery_client,
    github_client,
    output_dir: Path | None = None,
    status_callback=None,
    progress_callback=None,
) -> ArxivRelationsExportResult:
    arxiv_url = normalize_single_arxiv_input(arxiv_input)
    if callable(status_callback):
        status_callback(f"🎯 Resolving arXiv paper: {arxiv_url}")

    title, error = await arxiv_client.get_title(arxiv_url)
    if error or not title:
        raise ValueError(f"Failed to resolve arXiv title: {error or 'No title found'}")
    if callable(status_callback):
        status_callback(f"📄 Resolved title: {title}")

    target_work = await openalex_client.search_first_work(title)
    if not target_work:
        raise ValueError(f"No OpenAlex work found for title: {title}")
    if callable(status_callback):
        status_callback("🔎 Fetching OpenAlex referenced works")
    referenced_works = await openalex_client.fetch_referenced_works(target_work)
    if callable(status_callback):
        status_callback(f"📚 Retrieved {len(referenced_works)} referenced works")
        status_callback("🔎 Fetching OpenAlex citations")
    citation_works = await openalex_client.fetch_citations(target_work)
    if callable(status_callback):
        status_callback(f"📚 Retrieved {len(citation_works)} citation works")

    reference_seeds = normalize_related_works_to_seeds(referenced_works, openalex_client=openalex_client)
    citation_seeds = normalize_related_works_to_seeds(citation_works, openalex_client=openalex_client)

    references_csv_path, citations_csv_path = build_relations_csv_paths(arxiv_url, output_dir=output_dir)

    references_result = await export_paper_seeds_to_csv(
        reference_seeds,
        references_csv_path,
        discovery_client=discovery_client,
        github_client=github_client,
        status_callback=status_callback,
        progress_callback=progress_callback,
    )
    citations_result = await export_paper_seeds_to_csv(
        citation_seeds,
        citations_csv_path,
        discovery_client=discovery_client,
        github_client=github_client,
        status_callback=status_callback,
        progress_callback=progress_callback,
    )

    return ArxivRelationsExportResult(
        arxiv_url=arxiv_url,
        title=title,
        references=references_result,
        citations=citations_result,
    )
