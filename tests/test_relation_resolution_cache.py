from datetime import datetime, timedelta, timezone

from src.shared.relation_resolution_cache import RelationResolutionCacheStore


def test_relation_resolution_cache_store_initializes_expected_schema(tmp_path):
    store = RelationResolutionCacheStore(tmp_path / "cache.db")
    columns = {
        row["name"]: row["pk"]
        for row in store.connection.execute(
            "PRAGMA table_info(relation_resolution_cache)"
        ).fetchall()
    }

    assert columns == {
        "key_type": 1,
        "key_value": 2,
        "arxiv_url": 0,
        "checked_at": 0,
    }


def test_relation_resolution_cache_store_records_and_reads_positive_mapping(tmp_path):
    store = RelationResolutionCacheStore(tmp_path / "cache.db")

    store.record_resolution(
        key_type="openalex_work",
        key_value="https://openalex.org/W123",
        arxiv_url="https://arxiv.org/abs/2501.12345",
    )

    entry = store.get("openalex_work", "https://openalex.org/W123")

    assert entry is not None
    assert entry.arxiv_url == "https://arxiv.org/abs/2501.12345"
    assert entry.checked_at is not None


def test_relation_resolution_cache_store_records_negative_mapping(tmp_path):
    store = RelationResolutionCacheStore(tmp_path / "cache.db")

    store.record_resolution(
        key_type="doi",
        key_value="https://doi.org/10.1000/example",
        arxiv_url=None,
    )

    entry = store.get("doi", "https://doi.org/10.1000/example")

    assert entry is not None
    assert entry.arxiv_url is None
    assert entry.checked_at is not None


def test_relation_resolution_cache_negative_freshness_uses_days_threshold():
    recent = datetime.now(timezone.utc).isoformat()
    stale = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()

    assert RelationResolutionCacheStore.is_negative_cache_fresh(recent, 30) is True
    assert RelationResolutionCacheStore.is_negative_cache_fresh(stale, 30) is False
