import asyncio
import csv
import time
from pathlib import Path

import pytest

from src.csv_update.pipeline import build_csv_row_outcome, update_csv_file
from src.csv_update.runner import run_csv_mode
from src.shared.paper_content import PaperContentCache
from src.shared.paper_identity import extract_arxiv_id


class FakeContentCache:
    def __init__(self):
        self.overview_calls: list[tuple[str, Path]] = []
        self.abs_calls: list[tuple[str, Path]] = []

    async def ensure_overview_path(self, url: str, *, relative_to: Path) -> str:
        self.overview_calls.append((url, Path(relative_to)))
        arxiv_id = extract_arxiv_id(url)
        if not arxiv_id:
            return ""
        return f"cache/overview/{arxiv_id}.md"

    async def ensure_abs_path(self, url: str, *, relative_to: Path) -> str:
        self.abs_calls.append((url, Path(relative_to)))
        arxiv_id = extract_arxiv_id(url)
        if not arxiv_id:
            return ""
        return f"cache/abs/{arxiv_id}.md"


@pytest.mark.anyio
async def test_update_csv_file_updates_rows_in_place_preserving_columns_and_order(tmp_path: Path):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,Url,Notes,Github,Stars,Tag",
                "Keep Github,https://arxiv.org/abs/2603.20000v2,note-1,https://github.com/foo/existing,1,A",
                "Discover Github,https://arxiv.org/pdf/2603.10000v1.pdf,note-2,,,B",
                "Invalid Url,https://example.com/not-arxiv,note-3,,9,C",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeDiscoveryClient:
        def __init__(self):
            self.urls = []

        async def resolve_github_url(self, seed):
            self.urls.append(seed.url)
            if seed.url.endswith("2603.10000"):
                return "https://github.com/foo/discovered"
            raise AssertionError(f"unexpected discovery lookup for {seed.url}")

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            mapping = {
                ("foo", "existing"): (99, None),
                ("foo", "discovered"): (42, None),
            }
            return mapping[(owner, repo)]

    content_cache = FakeContentCache()
    discovery_client = FakeDiscoveryClient()
    result = await update_csv_file(
        csv_path,
        discovery_client=discovery_client,
        github_client=FakeGitHubClient(),
        content_cache=content_cache,
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert result.csv_path == csv_path
    assert result.updated == 2
    assert len(result.skipped) == 1
    assert result.skipped[0]["title"] == "Invalid Url"
    assert result.skipped[0]["reason"] == "No valid arXiv URL found"
    assert reader.fieldnames == ["Name", "Url", "Notes", "Github", "Stars", "Overview", "Abs", "Tag"]
    assert discovery_client.urls == ["https://arxiv.org/abs/2603.10000"]
    assert rows == [
        {
            "Name": "Keep Github",
            "Url": "https://arxiv.org/abs/2603.20000",
            "Notes": "note-1",
            "Github": "https://github.com/foo/existing",
            "Stars": "99",
            "Overview": "cache/overview/2603.20000.md",
            "Abs": "cache/abs/2603.20000.md",
            "Tag": "A",
        },
        {
            "Name": "Discover Github",
            "Url": "https://arxiv.org/abs/2603.10000",
            "Notes": "note-2",
            "Github": "https://github.com/foo/discovered",
            "Stars": "42",
            "Overview": "cache/overview/2603.10000.md",
            "Abs": "cache/abs/2603.10000.md",
            "Tag": "B",
        },
        {
            "Name": "Invalid Url",
            "Url": "https://example.com/not-arxiv",
            "Notes": "note-3",
            "Github": "",
            "Stars": "9",
            "Overview": "",
            "Abs": "",
            "Tag": "C",
        },
    ]
    assert [call[0] for call in content_cache.overview_calls] == [
        "https://arxiv.org/abs/2603.20000v2",
        "https://arxiv.org/pdf/2603.10000v1.pdf",
        "https://example.com/not-arxiv",
    ]
    assert [call[0] for call in content_cache.abs_calls] == [
        "https://arxiv.org/abs/2603.20000v2",
        "https://arxiv.org/pdf/2603.10000v1.pdf",
        "https://example.com/not-arxiv",
    ]


@pytest.mark.anyio
async def test_update_csv_file_appends_missing_content_columns_after_github_and_stars(tmp_path: Path):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,Url,Notes",
                "Paper A,https://arxiv.org/abs/2603.30000v1,note-a",
                "Paper B,,note-b",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeDiscoveryClient:
        async def resolve_github_url(self, seed):
            assert seed.url == "https://arxiv.org/abs/2603.30000"
            return "https://github.com/foo/bar"

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            assert (owner, repo) == ("foo", "bar")
            return 7, None

    result = await update_csv_file(
        csv_path,
        discovery_client=FakeDiscoveryClient(),
        github_client=FakeGitHubClient(),
        content_cache=FakeContentCache(),
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert result.updated == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["title"] == "Paper B"
    assert result.skipped[0]["reason"] == "No valid arXiv URL found"
    assert reader.fieldnames == ["Name", "Url", "Notes", "Github", "Stars", "Overview", "Abs"]
    assert rows == [
        {
            "Name": "Paper A",
            "Url": "https://arxiv.org/abs/2603.30000",
            "Notes": "note-a",
            "Github": "https://github.com/foo/bar",
            "Stars": "7",
            "Overview": "cache/overview/2603.30000.md",
            "Abs": "cache/abs/2603.30000.md",
        },
        {
            "Name": "Paper B",
            "Url": "",
            "Notes": "note-b",
            "Github": "",
            "Stars": "",
            "Overview": "",
            "Abs": "",
        },
    ]


@pytest.mark.anyio
async def test_update_csv_file_requires_url_column(tmp_path: Path):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,Github,Stars",
                "Paper A,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeDiscoveryClient:
        async def resolve_github_url(self, seed):
            raise AssertionError("discovery should not run when Url column is missing")

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            raise AssertionError("GitHub should not run when Url column is missing")

    with pytest.raises(ValueError, match="CSV file must include Url column"):
        await update_csv_file(
            csv_path,
            discovery_client=FakeDiscoveryClient(),
            github_client=FakeGitHubClient(),
            content_cache=FakeContentCache(),
        )


@pytest.mark.anyio
async def test_update_csv_file_allows_missing_name_column_when_url_exists(tmp_path: Path):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Url,Notes",
                "https://arxiv.org/abs/2603.30000v1,note-a",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeDiscoveryClient:
        async def resolve_github_url(self, seed):
            assert seed.name == "Row 1"
            assert seed.url == "https://arxiv.org/abs/2603.30000"
            return "https://github.com/foo/bar"

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            assert (owner, repo) == ("foo", "bar")
            return 7, None

    result = await update_csv_file(
        csv_path,
        discovery_client=FakeDiscoveryClient(),
        github_client=FakeGitHubClient(),
        content_cache=FakeContentCache(),
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert result.updated == 1
    assert rows == [
        {
            "Url": "https://arxiv.org/abs/2603.30000",
            "Notes": "note-a",
            "Github": "https://github.com/foo/bar",
            "Stars": "7",
            "Overview": "cache/overview/2603.30000.md",
            "Abs": "cache/abs/2603.30000.md",
        }
    ]
    assert reader.fieldnames == ["Url", "Notes", "Github", "Stars", "Overview", "Abs"]


@pytest.mark.anyio
async def test_update_csv_file_fills_blank_stars_for_existing_github_and_still_populates_content_paths(tmp_path: Path):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,Url,Github,Stars",
                "Paper A,https://arxiv.org/abs/2603.20000v2,https://github.com/foo/bar,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeDiscoveryClient:
        async def resolve_github_url(self, seed):
            raise AssertionError("discovery should not run when Github already exists")

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            assert (owner, repo) == ("foo", "bar")
            return 11, None

    result = await update_csv_file(
        csv_path,
        discovery_client=FakeDiscoveryClient(),
        github_client=FakeGitHubClient(),
        content_cache=FakeContentCache(),
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert result.updated == 1
    assert result.skipped == []
    assert rows == [
        {
            "Name": "Paper A",
            "Url": "https://arxiv.org/abs/2603.20000",
            "Github": "https://github.com/foo/bar",
            "Stars": "11",
            "Overview": "cache/overview/2603.20000.md",
            "Abs": "cache/abs/2603.20000.md",
        }
    ]


@pytest.mark.anyio
async def test_update_csv_file_keeps_overview_and_abs_updates_when_github_discovery_misses(tmp_path: Path):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,Url,Github,Stars",
                "Paper A,https://arxiv.org/abs/2603.20000v2,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeDiscoveryClient:
        async def resolve_github_url(self, seed):
            return None

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            raise AssertionError("GitHub should not run when discovery finds no repo")

    result = await update_csv_file(
        csv_path,
        discovery_client=FakeDiscoveryClient(),
        github_client=FakeGitHubClient(),
        content_cache=FakeContentCache(),
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert result.updated == 0
    assert len(result.skipped) == 1
    assert result.skipped[0]["reason"] == "No Github URL found from discovery"
    assert rows == [
        {
            "Name": "Paper A",
            "Url": "https://arxiv.org/abs/2603.20000",
            "Github": "",
            "Stars": "",
            "Overview": "cache/overview/2603.20000.md",
            "Abs": "cache/abs/2603.20000.md",
        }
    ]


@pytest.mark.anyio
async def test_build_csv_row_outcome_runs_github_overview_and_abs_work_in_parallel(tmp_path: Path):
    class FakeDiscoveryClient:
        async def resolve_github_url(self, seed):
            return "https://github.com/foo/bar"

    class FakeGitHubClient:
        async def get_star_count(self, owner, repo):
            await asyncio.sleep(0.2)
            return 5, None

    class SlowContentCache:
        async def ensure_overview_path(self, url: str, *, relative_to: Path) -> str:
            await asyncio.sleep(0.2)
            return "cache/overview/2603.30000.md"

        async def ensure_abs_path(self, url: str, *, relative_to: Path) -> str:
            await asyncio.sleep(0.2)
            return "cache/abs/2603.30000.md"

    started_at = time.perf_counter()
    _, updated_row, outcome = await build_csv_row_outcome(
        1,
        {
            "Name": "Paper A",
            "Url": "https://arxiv.org/abs/2603.30000v1",
            "Github": "",
            "Stars": "",
        },
        discovery_client=FakeDiscoveryClient(),
        github_client=FakeGitHubClient(),
        content_cache=SlowContentCache(),
        csv_dir=tmp_path,
    )
    elapsed = time.perf_counter() - started_at

    assert elapsed < 0.35
    assert outcome.reason is None
    assert updated_row["Overview"] == "cache/overview/2603.30000.md"
    assert updated_row["Abs"] == "cache/abs/2603.30000.md"


@pytest.mark.anyio
async def test_paper_content_cache_writes_files_once_and_returns_paths_relative_to_csv_directory(tmp_path: Path):
    cache_root = tmp_path / "cache"
    csv_dir = tmp_path / "output"
    csv_dir.mkdir()

    class FakeAlphaXivContentClient:
        def __init__(self):
            self.paper_calls = []
            self.overview_calls = []

        async def get_paper_payload_by_arxiv_id(self, arxiv_id: str):
            self.paper_calls.append(arxiv_id)
            return {
                "title": "Paper 2603.30000",
                "abstract": "Abstract for 2603.30000",
                "versionId": "version-2603.30000",
            }, None

        async def get_overview_payload_by_version_id(self, version_id: str, *, language: str = "en"):
            self.overview_calls.append((version_id, language))
            return {"overview": "## Overview\n\nOverview for 2603.30000"}, None

    client = FakeAlphaXivContentClient()
    content_cache = PaperContentCache(cache_root=cache_root, content_client=client)

    overview_path = await content_cache.ensure_overview_path(
        "https://arxiv.org/pdf/2603.30000v1.pdf",
        relative_to=csv_dir,
    )
    abs_path = await content_cache.ensure_abs_path(
        "https://arxiv.org/abs/2603.30000v2",
        relative_to=csv_dir,
    )
    overview_path_repeat = await content_cache.ensure_overview_path(
        "https://arxiv.org/abs/2603.30000",
        relative_to=csv_dir,
    )
    abs_path_repeat = await content_cache.ensure_abs_path(
        "https://arxiv.org/abs/2603.30000",
        relative_to=csv_dir,
    )

    assert overview_path == "../cache/overview/2603.30000.md"
    assert abs_path == "../cache/abs/2603.30000.md"
    assert overview_path_repeat == overview_path
    assert abs_path_repeat == abs_path
    assert client.paper_calls == ["2603.30000"]
    assert client.overview_calls == [("version-2603.30000", "en")]

    overview_file = cache_root / "overview" / "2603.30000.md"
    abs_file = cache_root / "abs" / "2603.30000.md"
    assert overview_file.read_text(encoding="utf-8").find("Overview for 2603.30000") != -1
    assert abs_file.read_text(encoding="utf-8").find("Abstract for 2603.30000") != -1


@pytest.mark.anyio
async def test_run_csv_mode_prints_progress_updates_file_and_writes_cached_markdown(tmp_path: Path, capsys):
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Name,Url,Github,Stars",
                "Paper A,https://arxiv.org/abs/2603.20000v2,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeDiscoveryClient:
        def __init__(self, session, *, huggingface_token="", max_concurrent=0, min_interval=0):
            self.session = session
            self.huggingface_token = huggingface_token

        async def resolve_github_url(self, seed):
            return "https://github.com/foo/bar"

    class FakeGitHubClient:
        def __init__(self, session, github_token="", max_concurrent=0, min_interval=0):
            self.session = session
            self.github_token = github_token

        async def get_star_count(self, owner, repo):
            return 11, None

    class FakeAlphaXivContentClient:
        def __init__(self, session, *, max_concurrent=0, min_interval=0):
            self.session = session

        async def get_paper_payload_by_arxiv_id(self, arxiv_id: str):
            assert arxiv_id == "2603.20000"
            return {
                "title": "Paper A",
                "abstract": "Abstract body",
                "versionId": "version-2603.20000",
            }, None

        async def get_overview_payload_by_version_id(self, version_id: str, *, language: str = "en"):
            assert (version_id, language) == ("version-2603.20000", "en")
            return {"overview": "## Overview\n\nOverview body"}, None

    exit_code = await run_csv_mode(
        csv_path,
        session_factory=lambda **kwargs: FakeSession(),
        discovery_client_cls=FakeDiscoveryClient,
        github_client_cls=FakeGitHubClient,
        content_client_cls=FakeAlphaXivContentClient,
        content_cache_root=tmp_path / "cache",
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Found 1 rows" in captured.out
    assert "[1/1] Paper A" in captured.out
    assert "foo/bar" in captured.out
    assert "Updated: N/A → 11" in captured.out
    assert "Updated: 1" in captured.out

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "Name": "Paper A",
            "Url": "https://arxiv.org/abs/2603.20000",
            "Github": "https://github.com/foo/bar",
            "Stars": "11",
            "Overview": "cache/overview/2603.20000.md",
            "Abs": "cache/abs/2603.20000.md",
        }
    ]
    assert (tmp_path / "cache" / "overview" / "2603.20000.md").read_text(encoding="utf-8").find("Overview body") != -1
    assert (tmp_path / "cache" / "abs" / "2603.20000.md").read_text(encoding="utf-8").find("Abstract body") != -1
