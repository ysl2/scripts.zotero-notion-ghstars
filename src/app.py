import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from src.csv_update.runner import run_csv_mode
from src.notion_sync.runner import run_notion_mode
from src.url_to_csv.runner import run_url_mode
from src.url_to_csv.sources import is_supported_url_source

try:
    from src.arxiv_relations.runner import run_arxiv_relations_mode
except ModuleNotFoundError:  # pragma: no cover - placeholder until runner exists
    async def run_arxiv_relations_mode(*args, **kwargs):
        raise NotImplementedError("run_arxiv_relations_mode is not implemented")


load_dotenv()


def _normalize_argv(argv: list[str] | None) -> list[str]:
    if argv is None:
        return sys.argv[1:]
    return list(argv)


def _validate_input_path(raw_path: str) -> Path | None:
    path = Path(raw_path).expanduser()
    if path.suffix.lower() != ".csv" or not path.exists() or not path.is_file():
        return None
    return path


def _is_url(raw_value: str) -> bool:
    parsed = urlparse(raw_value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


ARXIV_ORG_HOSTS = {"arxiv.org", "www.arxiv.org"}


def _is_arxiv_single_paper_url(raw_value: str) -> bool:
    parsed = urlparse(raw_value)
    if parsed.scheme not in {"http", "https"}:
        return False

    host = (parsed.hostname or "").lower()
    if host not in ARXIV_ORG_HOSTS:
        return False

    path_parts = [part for part in parsed.path.rstrip("/").split("/") if part]
    if not path_parts:
        return False

    if path_parts[0] == "abs":
        return len(path_parts) >= 2 and bool(path_parts[1])

    if path_parts[0] == "pdf" and len(path_parts) >= 2:
        pdf_name = path_parts[1]
        return pdf_name.lower().endswith(".pdf") and len(pdf_name) > 4

    return False


async def async_main(argv: list[str] | None = None) -> int:
    args = _normalize_argv(argv)

    if len(args) > 1:
        print("Expected 0 or 1 positional arguments", file=sys.stderr)
        return 2

    if not args:
        return await run_notion_mode()

    raw_input = args[0]
    if _is_arxiv_single_paper_url(raw_input):
        return await run_arxiv_relations_mode(raw_input)

    if _is_url(raw_input):
        if not is_supported_url_source(raw_input):
            print(f"Input file or URL not supported: {raw_input}", file=sys.stderr)
            return 1
        return await run_url_mode(raw_input)

    input_path = _validate_input_path(raw_input)
    if input_path is None:
        print(f"Input file not found or invalid: {Path(raw_input).expanduser()}", file=sys.stderr)
        return 1

    return await run_csv_mode(input_path)


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
