import csv
from pathlib import Path

import pytest

from csv_update.pipeline import update_csv_file
from csv_update.runner import run_csv_mode


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

    discovery_client = FakeDiscoveryClient()
    result = await update_csv_file(
        csv_path,
        discovery_client=discovery_client,
        github_client=FakeGitHubClient(),
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert result.csv_path == csv_path
    assert result.updated == 2
    assert len(result.skipped) == 1
    assert result.skipped[0]["title"] == "Invalid Url"
    assert result.skipped[0]["reason"] == "No valid arXiv URL found"
    assert reader.fieldnames == ["Name", "Url", "Notes", "Github", "Stars", "Tag"]
    assert discovery_client.urls == ["https://arxiv.org/abs/2603.10000"]
    assert rows == [
        {
            "Name": "Keep Github",
            "Url": "https://arxiv.org/abs/2603.20000",
            "Notes": "note-1",
            "Github": "https://github.com/foo/existing",
            "Stars": "99",
            "Tag": "A",
        },
        {
            "Name": "Discover Github",
            "Url": "https://arxiv.org/abs/2603.10000",
            "Notes": "note-2",
            "Github": "https://github.com/foo/discovered",
            "Stars": "42",
            "Tag": "B",
        },
        {
            "Name": "Invalid Url",
            "Url": "https://example.com/not-arxiv",
            "Notes": "note-3",
            "Github": "",
            "Stars": "9",
            "Tag": "C",
        },
    ]


@pytest.mark.anyio
async def test_update_csv_file_appends_missing_github_and_stars_columns(tmp_path: Path):
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
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert result.updated == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["title"] == "Paper B"
    assert result.skipped[0]["reason"] == "No valid arXiv URL found"
    assert reader.fieldnames == ["Name", "Url", "Notes", "Github", "Stars"]
    assert rows == [
        {
            "Name": "Paper A",
            "Url": "https://arxiv.org/abs/2603.30000",
            "Notes": "note-a",
            "Github": "https://github.com/foo/bar",
            "Stars": "7",
        },
        {
            "Name": "Paper B",
            "Url": "",
            "Notes": "note-b",
            "Github": "",
            "Stars": "",
        },
    ]


@pytest.mark.anyio
async def test_run_csv_mode_prints_progress_and_updates_file(tmp_path: Path, capsys):
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
        def __init__(self, session, *, huggingface_token="", alphaxiv_token="", max_concurrent=0, min_interval=0):
            self.session = session
            self.huggingface_token = huggingface_token
            self.alphaxiv_token = alphaxiv_token

        async def resolve_github_url(self, seed):
            return "https://github.com/foo/bar"

    class FakeGitHubClient:
        def __init__(self, session, github_token="", max_concurrent=0, min_interval=0):
            self.session = session
            self.github_token = github_token

        async def get_star_count(self, owner, repo):
            return 11, None

    exit_code = await run_csv_mode(
        csv_path,
        session_factory=lambda **kwargs: FakeSession(),
        discovery_client_cls=FakeDiscoveryClient,
        github_client_cls=FakeGitHubClient,
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
        }
    ]
