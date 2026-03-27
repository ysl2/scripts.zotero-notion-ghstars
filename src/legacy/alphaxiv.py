import asyncio
import re

import aiohttp

from src.shared.github import normalize_github_url
from src.shared.http import MAX_RETRIES, RateLimiter


def find_github_url_in_alphaxiv_legacy_payload(payload) -> str | None:
    if not isinstance(payload, dict):
        return None

    paper = payload.get("paper", {}) if isinstance(payload.get("paper"), dict) else {}
    candidates = [
        paper.get("implementation"),
        paper.get("marimo_implementation"),
        paper.get("paper_group", {}).get("resources") if isinstance(paper.get("paper_group"), dict) else None,
        paper.get("resources"),
    ]

    for candidate in candidates:
        github_url = _find_github_url_in_json_payload(candidate)
        if github_url:
            return github_url

    return _find_github_url_in_json_payload(payload)


class AlphaXivLegacyClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        alphaxiv_token: str = "",
        max_concurrent: int = 5,
        min_interval: float = 0.2,
    ):
        self.session = session
        self.alphaxiv_token = alphaxiv_token
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(min_interval)

    async def get_paper_legacy(self, arxiv_id: str):
        if not self.alphaxiv_token:
            return None, "Missing ALPHAXIV_TOKEN"

        headers = {
            "Accept": "application/json",
            "User-Agent": "scripts.ghstars",
            "Authorization": f"Bearer {self.alphaxiv_token}",
        }

        for attempt in range(MAX_RETRIES + 1):
            async with self.semaphore:
                await self.rate_limiter.acquire()
                try:
                    async with self.session.get(
                        f"https://api.alphaxiv.org/papers/v3/legacy/{arxiv_id}",
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            return await response.json(), None
                        if response.status in {429, 500, 502, 503, 504} and attempt < MAX_RETRIES:
                            await asyncio.sleep(0.5 * (2**attempt))
                            continue
                        return None, f"AlphaXiv API error ({response.status})"
                except asyncio.TimeoutError:
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    return None, "AlphaXiv API timeout"
                except Exception as exc:
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                    return None, f"AlphaXiv API request failed: {exc}"

        return None, "AlphaXiv API error"


def _find_github_url_in_text(text: str) -> str | None:
    if not text or not isinstance(text, str):
        return None

    pattern = r"https?://(?:www\.)?github\.com/[\w.-]+/[\w.-]+(?:\.git)?/?[),.;:!?]*"
    for match in re.findall(pattern, text, flags=re.IGNORECASE):
        normalized = normalize_github_url(match.rstrip("),.;:!?"))
        if normalized:
            return normalized
    return None


def _find_github_url_in_json_payload(payload) -> str | None:
    if isinstance(payload, str):
        return _find_github_url_in_text(payload)
    if isinstance(payload, list):
        for item in payload:
            result = _find_github_url_in_json_payload(item)
            if result:
                return result
        return None
    if isinstance(payload, dict):
        for value in payload.values():
            result = _find_github_url_in_json_payload(value)
            if result:
                return result
        return None
    return None
