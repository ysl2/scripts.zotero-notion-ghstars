from src.shared.repo_cache import RepoCacheStore


def test_repo_cache_store_records_found_repo_and_resets_no_repo_count(tmp_path):
    store = RepoCacheStore(tmp_path / "cache.db")

    store.record_exact_no_repo("https://arxiv.org/abs/2603.18493")
    store.record_found_repo("https://arxiv.org/abs/2603.18493", "https://github.com/foo/bar")

    entry = store.get("https://arxiv.org/abs/2603.18493")

    assert entry is not None
    assert entry.github_url == "https://github.com/foo/bar"
    assert entry.hf_exact_no_repo_count == 0


def test_repo_cache_store_increments_successful_exact_no_repo_count(tmp_path):
    store = RepoCacheStore(tmp_path / "cache.db")

    store.record_exact_no_repo("https://arxiv.org/abs/2603.18493")
    store.record_exact_no_repo("https://arxiv.org/abs/2603.18493")

    entry = store.get("https://arxiv.org/abs/2603.18493")

    assert entry is not None
    assert entry.github_url is None
    assert entry.hf_exact_no_repo_count == 2
