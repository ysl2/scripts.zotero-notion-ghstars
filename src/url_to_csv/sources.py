from enum import StrEnum

from src.url_to_csv.arxivxplorer import is_supported_arxivxplorer_url
from src.url_to_csv.huggingface_papers import is_supported_huggingface_papers_url


class UrlSource(StrEnum):
    ARXIVXPLORER = "arxivxplorer"
    HUGGINGFACE_PAPERS = "huggingface_papers"


def detect_url_source(raw_url: str) -> UrlSource | None:
    if is_supported_arxivxplorer_url(raw_url):
        return UrlSource.ARXIVXPLORER
    if is_supported_huggingface_papers_url(raw_url):
        return UrlSource.HUGGINGFACE_PAPERS
    return None


def is_supported_url_source(raw_url: str) -> bool:
    return detect_url_source(raw_url) is not None
