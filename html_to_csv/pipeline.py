import asyncio
from pathlib import Path

from html_to_csv.csv_writer import output_csv_path_for_html
from html_to_csv.models import ConversionResult, PaperSeed
from html_to_csv.html_parser import parse_paper_seeds_from_html
from shared.paper_export import build_paper_outcome, export_paper_seeds_to_csv


async def convert_html_to_csv(
    html_path: Path,
    *,
    discovery_client,
    github_client,
    status_callback=None,
    progress_callback=None,
) -> ConversionResult:
    html_path = Path(html_path)
    seeds = parse_paper_seeds_from_html(html_path.read_text(encoding="utf-8"))
    return await export_paper_seeds_to_csv(
        seeds,
        output_csv_path_for_html(html_path),
        discovery_client=discovery_client,
        github_client=github_client,
        status_callback=status_callback,
        progress_callback=progress_callback,
    )
