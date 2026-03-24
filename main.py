import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from csv_update.runner import run_csv_mode
from html_to_csv.runner import run_html_mode
from notion_sync.runner import run_notion_mode


load_dotenv()


def _normalize_argv(argv: list[str] | None) -> list[str]:
    if argv is None:
        return sys.argv[1:]
    return list(argv)


def _validate_input_path(raw_path: str) -> Path | None:
    path = Path(raw_path).expanduser()
    if path.suffix.lower() not in {".html", ".csv"} or not path.exists() or not path.is_file():
        return None
    return path


async def async_main(argv: list[str] | None = None) -> int:
    args = _normalize_argv(argv)

    if len(args) > 1:
        print("Expected 0 or 1 positional arguments", file=sys.stderr)
        return 2

    if not args:
        return await run_notion_mode()

    input_path = _validate_input_path(args[0])
    if input_path is None:
        print(f"Input file not found or invalid: {Path(args[0]).expanduser()}", file=sys.stderr)
        return 1

    if input_path.suffix.lower() == ".html":
        return await run_html_mode(input_path)
    return await run_csv_mode(input_path)


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
