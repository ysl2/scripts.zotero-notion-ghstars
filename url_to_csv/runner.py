import os
import sys
from pathlib import Path

import aiohttp

from shared.discovery import DiscoveryClient
from shared.github import GitHubClient
from shared.http import build_timeout
from shared.progress import print_paper_progress, print_summary
from shared.runtime import build_client, load_runtime_config
from shared.settings import DEFAULT_CONCURRENT_LIMIT
from shared.skip_reasons import is_minor_skip_reason
from url_to_csv.arxivxplorer import ArxivXplorerSearchClient, is_supported_arxivxplorer_url
from url_to_csv.pipeline import export_url_to_csv


CONCURRENT_LIMIT = DEFAULT_CONCURRENT_LIMIT
REQUEST_DELAY = 0.2


async def run_url_mode(
    input_url: str,
    *,
    output_dir: Path | None = None,
    session_factory=aiohttp.ClientSession,
    search_client_cls=ArxivXplorerSearchClient,
    discovery_client_cls=DiscoveryClient,
    github_client_cls=GitHubClient,
) -> int:
    if not is_supported_arxivxplorer_url(input_url):
        print(f"Unsupported URL: {input_url}", file=sys.stderr)
        return 1

    config = load_runtime_config(dict(os.environ))

    async with session_factory(timeout=build_timeout()) as session:
        search_client = build_client(
            search_client_cls,
            session,
            max_concurrent=CONCURRENT_LIMIT,
            min_interval=REQUEST_DELAY,
        )
        discovery_client = build_client(
            discovery_client_cls,
            session,
            huggingface_token=config["huggingface_token"],
            alphaxiv_token=config["alphaxiv_token"],
            max_concurrent=CONCURRENT_LIMIT,
            min_interval=REQUEST_DELAY,
        )
        github_client = build_client(
            github_client_cls,
            session,
            github_token=config["github_token"],
            max_concurrent=CONCURRENT_LIMIT,
            min_interval=REQUEST_DELAY,
        )

        result = await export_url_to_csv(
            input_url,
            output_dir=output_dir,
            search_client=search_client,
            discovery_client=discovery_client,
            github_client=github_client,
            status_callback=lambda message: print(message, flush=True),
            progress_callback=lambda outcome, total: print_paper_progress(
                outcome,
                total,
                is_minor_reason=is_minor_skip_reason,
            ),
        )

    print_summary(
        "Resolved",
        result.resolved,
        result.skipped,
        is_minor_reason=is_minor_skip_reason,
        detail_label="Paper URL",
        minor_header="Skipped rows (CSV rows still written):",
    )
    print(f"Wrote CSV: {result.csv_path}", flush=True)
    return 0
