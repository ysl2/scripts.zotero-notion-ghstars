import asyncio
import os
import tempfile
from pathlib import Path

from src.shared.paper_identity import build_arxiv_abs_url, extract_arxiv_id, normalize_arxiv_url
from src.shared.settings import ABS_CACHE_SUBDIR, ALPHAXIV_OVERVIEW_LANGUAGE, OVERVIEW_CACHE_SUBDIR


class PaperContentCache:
    def __init__(
        self,
        *,
        cache_root: Path,
        content_client,
        overview_language: str = ALPHAXIV_OVERVIEW_LANGUAGE,
    ):
        self.cache_root = Path(cache_root)
        self.content_client = content_client
        self.overview_language = overview_language
        self._file_tasks: dict[tuple[str, str], asyncio.Task[Path | None]] = {}
        self._paper_cache: dict[str, tuple[dict | None, str | None]] = {}
        self._paper_tasks: dict[str, asyncio.Task[tuple[dict | None, str | None]]] = {}
        self._task_lock = asyncio.Lock()

    async def ensure_overview_path(self, url: str, *, relative_to: Path) -> str:
        return await self._ensure_path("overview", url, relative_to=relative_to)

    async def ensure_abs_path(self, url: str, *, relative_to: Path) -> str:
        return await self._ensure_path("abs", url, relative_to=relative_to)

    async def _ensure_path(self, kind: str, url: str, *, relative_to: Path) -> str:
        arxiv_url = normalize_arxiv_url(url)
        arxiv_id = extract_arxiv_id(arxiv_url or "")
        if not arxiv_id:
            return ""

        target_path = self._target_path(kind, arxiv_id)
        if not target_path.exists():
            target_path = await self._ensure_file(kind, arxiv_id)
            if target_path is None:
                return ""

        return self._relative_path(target_path, start=relative_to)

    async def _ensure_file(self, kind: str, arxiv_id: str) -> Path | None:
        target_path = self._target_path(kind, arxiv_id)
        if target_path.exists():
            return target_path

        cache_key = (kind, arxiv_id)
        async with self._task_lock:
            task = self._file_tasks.get(cache_key)
            if task is None:
                task = asyncio.create_task(self._build_file(kind, arxiv_id))
                self._file_tasks[cache_key] = task

        try:
            return await task
        finally:
            async with self._task_lock:
                if self._file_tasks.get(cache_key) is task:
                    self._file_tasks.pop(cache_key, None)

    async def _build_file(self, kind: str, arxiv_id: str) -> Path | None:
        target_path = self._target_path(kind, arxiv_id)
        if target_path.exists():
            return target_path

        paper_payload, error = await self._get_paper_payload(arxiv_id)
        if error or not isinstance(paper_payload, dict):
            return None

        title = str(paper_payload.get("title") or "").strip()
        abstract = str(paper_payload.get("abstract") or "").strip()
        arxiv_url = normalize_arxiv_url(str(paper_payload.get("sourceUrl") or "")) or build_arxiv_abs_url(arxiv_id)

        if kind == "overview":
            version_id = str(paper_payload.get("versionId") or "").strip()
            if not version_id:
                return None
            overview_payload, overview_error = await self.content_client.get_overview_payload_by_version_id(
                version_id,
                language=self.overview_language,
            )
            if overview_error or not isinstance(overview_payload, dict):
                return None
            overview = str(overview_payload.get("overview") or "").strip()
            if not overview:
                return None
            content = _render_overview_markdown(title=title, arxiv_url=arxiv_url, overview=overview)
        else:
            if not abstract:
                return None
            content = _render_abs_markdown(title=title, arxiv_url=arxiv_url, abstract=abstract)

        _write_text_atomic(target_path, content)
        return target_path

    def _target_path(self, kind: str, arxiv_id: str) -> Path:
        subdir = OVERVIEW_CACHE_SUBDIR if kind == "overview" else ABS_CACHE_SUBDIR
        return self.cache_root / subdir / f"{arxiv_id}.md"

    @staticmethod
    def _relative_path(path: Path, *, start: Path) -> str:
        return Path(os.path.relpath(path, start=start)).as_posix()

    async def _get_paper_payload(self, arxiv_id: str) -> tuple[dict | None, str | None]:
        async with self._task_lock:
            cached = self._paper_cache.get(arxiv_id)
            if cached is not None:
                return cached

            task = self._paper_tasks.get(arxiv_id)
            if task is None:
                task = asyncio.create_task(self.content_client.get_paper_payload_by_arxiv_id(arxiv_id))
                self._paper_tasks[arxiv_id] = task

        try:
            result = await task
        finally:
            async with self._task_lock:
                if self._paper_tasks.get(arxiv_id) is task:
                    self._paper_tasks.pop(arxiv_id, None)

        if result[1] is None:
            async with self._task_lock:
                self._paper_cache[arxiv_id] = result

        return result


def _render_overview_markdown(*, title: str, arxiv_url: str, overview: str) -> str:
    parts = []
    if title:
        parts.append(f"# {title}")
        parts.append("")
    parts.append(f"Source: {arxiv_url}")
    parts.append("")
    parts.append(overview.strip())
    return "\n".join(parts).strip() + "\n"


def _render_abs_markdown(*, title: str, arxiv_url: str, abstract: str) -> str:
    parts = []
    if title:
        parts.append(f"# {title}")
        parts.append("")
    parts.append(f"Source: {arxiv_url}")
    parts.append("")
    parts.append("## Abstract")
    parts.append("")
    parts.append(abstract.strip())
    return "\n".join(parts).strip() + "\n"


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)
