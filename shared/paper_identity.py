import re


ARXIV_URL_PATTERN = re.compile(
    r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(?:v\d+)?(?:\.pdf)?",
    re.IGNORECASE,
)


def extract_arxiv_id(url: str) -> str | None:
    if not url or not isinstance(url, str):
        return None

    match = ARXIV_URL_PATTERN.search(url.strip())
    if not match:
        return None
    return match.group(1)


def build_arxiv_abs_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{arxiv_id}"


def normalize_arxiv_url(url: str) -> str | None:
    arxiv_id = extract_arxiv_id(url)
    if not arxiv_id:
        return None
    return build_arxiv_abs_url(arxiv_id)


def arxiv_url_sort_key(url: str) -> tuple[int, int, str]:
    arxiv_id = extract_arxiv_id(url)
    if not arxiv_id:
        return (-1, -1, url or "")

    prefix, suffix = arxiv_id.split(".", maxsplit=1)
    return (int(prefix), int(suffix), build_arxiv_abs_url(arxiv_id))
