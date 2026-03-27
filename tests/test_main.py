import pytest

from src.shared.runtime import load_runtime_config, open_runtime_clients


def test_load_runtime_config_reads_only_optional_tokens():
    config = load_runtime_config(
        {
            "GITHUB_TOKEN": "gh_token",
            "HUGGINGFACE_TOKEN": "hf_token",
            "HF_EXACT_NO_REPO_RECHECK_DAYS": "7",
        }
    )

    assert config == {
        "github_token": "gh_token",
        "huggingface_token": "hf_token",
        "openalex_api_key": "",
        "hf_exact_no_repo_recheck_days": 7,
    }


def test_load_runtime_config_defaults_missing_values_to_empty_strings():
    assert load_runtime_config({}) == {
        "github_token": "",
        "huggingface_token": "",
        "openalex_api_key": "",
        "hf_exact_no_repo_recheck_days": 7,
    }


def test_load_runtime_config_falls_back_to_default_recheck_days_for_invalid_value():
    assert load_runtime_config({"HF_EXACT_NO_REPO_RECHECK_DAYS": "abc"})["hf_exact_no_repo_recheck_days"] == 7


def test_load_runtime_config_reads_optional_openalex_token():
    config = load_runtime_config(
        {
            "OPENALEX_API_KEY": "oa_key",
        }
    )

    assert config["openalex_api_key"] == "oa_key"


@pytest.mark.anyio
async def test_open_runtime_clients_builds_shared_clients_without_alphaxiv_token():
    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeDiscoveryClient:
        def __init__(
            self,
            session,
            *,
            huggingface_token="",
            repo_cache=None,
            hf_exact_no_repo_recheck_days=0,
            max_concurrent=0,
            min_interval=0,
        ):
            self.session = session
            self.huggingface_token = huggingface_token
            self.repo_cache = repo_cache
            self.hf_exact_no_repo_recheck_days = hf_exact_no_repo_recheck_days
            self.max_concurrent = max_concurrent
            self.min_interval = min_interval

    class FakeGitHubClient:
        def __init__(self, session, *, github_token="", max_concurrent=0, min_interval=0):
            self.session = session
            self.github_token = github_token
            self.max_concurrent = max_concurrent
            self.min_interval = min_interval

    config = load_runtime_config(
        {
            "GITHUB_TOKEN": "gh_token",
            "HUGGINGFACE_TOKEN": "hf_token",
            "HF_EXACT_NO_REPO_RECHECK_DAYS": "9",
        }
    )

    async with open_runtime_clients(
        config,
        session_factory=lambda **kwargs: FakeSession(),
        discovery_client_cls=FakeDiscoveryClient,
        github_client_cls=FakeGitHubClient,
        concurrent_limit=7,
        request_delay=0.3,
        github_min_interval=0.4,
    ) as runtime:
        assert runtime.discovery_client.huggingface_token == "hf_token"
        assert runtime.discovery_client.hf_exact_no_repo_recheck_days == 9
        assert runtime.discovery_client.max_concurrent == 7
        assert runtime.discovery_client.min_interval == 0.3
        assert runtime.github_client.github_token == "gh_token"
        assert runtime.github_client.max_concurrent == 7
        assert runtime.github_client.min_interval == 0.4
