from pathlib import Path

import pytest

from src.shared.papers import ConversionResult, PaperSeed


@pytest.mark.anyio
async def test_export_arxiv_relations_to_csv_resolves_title_filters_and_exports_both_sets(
    tmp_path: Path, monkeypatch
):
    from src.arxiv_relations.pipeline import export_arxiv_relations_to_csv

    class FakeArxivClient:
        def __init__(self):
            self.calls: list[str] = []

        async def get_title(self, arxiv_identifier: str):
            self.calls.append(arxiv_identifier)
            return "Target Paper", None

    class FakeOpenAlexClient:
        def __init__(self):
            self.title_queries: list[str] = []
            self.reference_work_queries: list[dict] = []
            self.citation_work_queries: list[dict] = []

        async def search_first_work(self, title: str):
            self.title_queries.append(title)
            return {"id": "https://openalex.org/W0"}

        async def fetch_referenced_works(self, work: dict):
            self.reference_work_queries.append(work)
            return [
                {"id": "R1"},
                {"id": "R2"},
                {"id": "R3"},
            ]

        async def fetch_citations(self, work: dict):
            self.citation_work_queries.append(work)
            return [
                {"id": "C1"},
                {"id": "C2"},
            ]

        def normalize_related_work(self, work: dict):
            mapping = {
                "R1": PaperSeed(name="Reference A", url="https://arxiv.org/abs/2501.00001"),
                "R2": None,
                "R3": PaperSeed(name="Reference A Duplicate", url="https://arxiv.org/abs/2501.00001"),
                "C1": PaperSeed(name="Citation A", url="https://arxiv.org/abs/2502.00002"),
                "C2": PaperSeed(name="Citation A Duplicate", url="https://arxiv.org/abs/2502.00002"),
            }
            return mapping[work["id"]]

    arxiv_client = FakeArxivClient()
    openalex_client = FakeOpenAlexClient()
    discovery_client = object()
    github_client = object()
    export_calls = []

    async def fake_export(
        seeds: list[PaperSeed],
        csv_path: Path,
        *,
        discovery_client,
        github_client,
        status_callback=None,
        progress_callback=None,
    ):
        export_calls.append(
            {
                "seeds": seeds,
                "csv_path": csv_path,
                "discovery_client": discovery_client,
                "github_client": github_client,
            }
        )
        return ConversionResult(csv_path=csv_path, resolved=len(seeds), skipped=[])

    monkeypatch.setattr("src.arxiv_relations.pipeline.export_paper_seeds_to_csv", fake_export)

    result = await export_arxiv_relations_to_csv(
        "https://arxiv.org/pdf/2603.23502v4.pdf?download=1",
        arxiv_client=arxiv_client,
        openalex_client=openalex_client,
        discovery_client=discovery_client,
        github_client=github_client,
        output_dir=tmp_path,
    )

    assert arxiv_client.calls == ["https://arxiv.org/abs/2603.23502"]
    assert openalex_client.title_queries == ["Target Paper"]
    assert openalex_client.reference_work_queries == [{"id": "https://openalex.org/W0"}]
    assert openalex_client.citation_work_queries == [{"id": "https://openalex.org/W0"}]

    assert len(export_calls) == 2
    assert [call["csv_path"].name for call in export_calls] == [
        "arxiv-2603.23502-references-20260326113045.csv",
        "arxiv-2603.23502-citations-20260326113045.csv",
    ]

    reference_seeds = export_calls[0]["seeds"]
    citation_seeds = export_calls[1]["seeds"]
    assert reference_seeds == [PaperSeed(name="Reference A", url="https://arxiv.org/abs/2501.00001")]
    assert citation_seeds == [PaperSeed(name="Citation A", url="https://arxiv.org/abs/2502.00002")]
    assert all(isinstance(seed, PaperSeed) for seed in reference_seeds + citation_seeds)

    assert export_calls[0]["discovery_client"] is discovery_client
    assert export_calls[0]["github_client"] is github_client
    assert export_calls[1]["discovery_client"] is discovery_client
    assert export_calls[1]["github_client"] is github_client

    assert result.references.csv_path.name == "arxiv-2603.23502-references-20260326113045.csv"
    assert result.citations.csv_path.name == "arxiv-2603.23502-citations-20260326113045.csv"
