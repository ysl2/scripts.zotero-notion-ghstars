from pathlib import Path

from shared.paper_export import export_paper_seeds_to_csv
from url_to_csv.arxivxplorer import (
    FetchedSeedsResult,
    TooManyPagesError,
    output_csv_path_for_arxivxplorer_url,
    paper_seed_from_search_result,
    parse_arxivxplorer_url,
)


async def fetch_paper_seeds_from_url(
    input_url: str,
    *,
    search_client,
    output_dir: Path | None = None,
    status_callback=None,
) -> FetchedSeedsResult:
    query = parse_arxivxplorer_url(input_url)
    csv_path = output_csv_path_for_arxivxplorer_url(input_url, output_dir=output_dir)

    seeds = []
    seen_urls: set[str] = set()
    page = 1
    while True:
        if callable(status_callback):
            status_callback(f"🔎 Fetching arXiv Xplorer page {page}")

        try:
            results = await search_client.search(query, page)
        except TooManyPagesError:
            if callable(status_callback):
                status_callback(f"📄 Reached arXiv Xplorer page limit at page {page - 1}")
            break

        if callable(status_callback):
            status_callback(f"📄 Fetched page {page}: {len(results)} results")

        if not results:
            break

        for result in results:
            seed = paper_seed_from_search_result(result)
            if seed and seed.url not in seen_urls:
                seeds.append(seed)
                seen_urls.add(seed.url)

        page += 1

    return FetchedSeedsResult(seeds=seeds, csv_path=csv_path)


async def export_url_to_csv(
    input_url: str,
    *,
    search_client,
    discovery_client,
    github_client,
    output_dir: Path | None = None,
    status_callback=None,
    progress_callback=None,
):
    fetched = await fetch_paper_seeds_from_url(
        input_url,
        search_client=search_client,
        output_dir=output_dir,
        status_callback=status_callback,
    )
    return await export_paper_seeds_to_csv(
        fetched.seeds,
        fetched.csv_path,
        discovery_client=discovery_client,
        github_client=github_client,
        status_callback=status_callback,
        progress_callback=progress_callback,
    )
