import os
import sys
import tempfile
import textwrap
import types
import unittest
from unittest.mock import AsyncMock


# Stub third-party modules so tests can import main.py without installing deps.
aiohttp_stub = types.ModuleType("aiohttp")
aiohttp_stub.ClientSession = object
sys.modules.setdefault("aiohttp", aiohttp_stub)

notion_client_stub = types.ModuleType("notion_client")

class _DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

notion_client_stub.AsyncClient = _DummyAsyncClient
sys.modules.setdefault("notion_client", notion_client_stub)

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)

# Prevent interactive prompt on import for legacy code path.
os.environ.setdefault("NOTION_TOKEN", "test-notion-token")

import main  # noqa: E402


class TestConfigLoading(unittest.TestCase):
    def test_load_config_requires_notion_token_and_database_id(self):
        env = {}
        with self.assertRaises(ValueError):
            main.load_config_from_env(env)

    def test_load_config_accepts_env_values(self):
        env = {
            "NOTION_TOKEN": "notion_xxx",
            "GITHUB_TOKEN": "ghp_xxx",
            "DATABASE_ID": "db_123",
            "ALPHAXIV_TOKEN": "axv1_test",
            "HUGGINGFACE_TOKEN": "hf_test",
        }
        cfg = main.load_config_from_env(env)
        self.assertEqual(cfg["notion_token"], "notion_xxx")
        self.assertEqual(cfg["github_token"], "ghp_xxx")
        self.assertEqual(cfg["database_id"], "db_123")
        self.assertEqual(cfg["alphaxiv_token"], "axv1_test")
        self.assertEqual(cfg["huggingface_token"], "hf_test")


class TestGithubFallbackHelpers(unittest.TestCase):
    def test_classify_github_value(self):
        self.assertEqual(main.classify_github_value(None), "empty")
        self.assertEqual(main.classify_github_value("   "), "empty")
        self.assertEqual(main.classify_github_value("WIP"), "wip")
        self.assertEqual(main.classify_github_value(" wIp "), "wip")
        self.assertEqual(main.classify_github_value(" https://github.com/owner/repo "), "valid_github")
        self.assertEqual(main.classify_github_value("https://example.com/project"), "other")

    def test_find_github_url_in_text(self):
        text = "paper page, code: https://github.com/foo/bar and more text"
        self.assertEqual(main.find_github_url_in_text(text), "https://github.com/foo/bar")

    def test_find_github_url_in_text_strips_trailing_punctuation(self):
        text = "official code (https://github.com/foo/bar.), mirror https://github.com/baz/qux,"
        self.assertEqual(main.find_github_url_in_text(text), "https://github.com/foo/bar")

    def test_minor_skip_reason_includes_unsupported_and_alphaxiv_failures(self):
        self.assertTrue(main.is_minor_skip_reason("Unsupported Github field content"))
        self.assertTrue(main.is_minor_skip_reason("AlphaXiv API error (500)"))
        self.assertTrue(main.is_minor_skip_reason("arXiv API error (429)"))
        self.assertTrue(main.is_minor_skip_reason("Hugging Face Papers error (500)"))

    def test_extract_arxiv_id_from_url(self):
        self.assertEqual(main.extract_arxiv_id_from_url("https://arxiv.org/abs/2601.22135"), "2601.22135")
        self.assertEqual(main.extract_arxiv_id_from_url("https://arxiv.org/pdf/2601.22135"), "2601.22135")
        self.assertIsNone(main.extract_arxiv_id_from_url("https://example.com/paper"))

    def test_extract_best_arxiv_id_from_feed(self):
        feed = textwrap.dedent(
            """
            <?xml version="1.0" encoding="UTF-8"?>
            <feed xmlns="http://www.w3.org/2005/Atom">
              <entry>
                <id>https://arxiv.org/abs/2603.99999v1</id>
                <title>Another Paper</title>
              </entry>
              <entry>
                <id>https://arxiv.org/abs/2603.05078v1</id>
                <title>MoRe: Motion-aware Feed-forward 4D Reconstruction Transformer</title>
              </entry>
            </feed>
            """
        ).strip()
        arxiv_id, source = main.extract_best_arxiv_id_from_feed(
            feed,
            "MoRe: Motion-aware Feed-forward 4D Reconstruction Transformer",
        )
        self.assertEqual(arxiv_id, "2603.05078")
        self.assertEqual(source, "title_search_exact")

    def test_get_text_from_property(self):
        rich_text_property = {
            "type": "rich_text",
            "rich_text": [{"plain_text": "summary text"}],
        }
        title_property = {
            "type": "title",
            "title": [{"plain_text": "title text"}],
        }
        formula_property = {
            "type": "formula",
            "formula": {"type": "string", "string": "formula text"},
        }
        url_property = {
            "type": "url",
            "url": "https://arxiv.org/abs/2601.22135",
        }

        self.assertEqual(main.get_text_from_property(rich_text_property), "summary text")
        self.assertEqual(main.get_text_from_property(title_property), "title text")
        self.assertEqual(main.get_text_from_property(formula_property), "formula text")
        self.assertEqual(main.get_text_from_property(url_property), "https://arxiv.org/abs/2601.22135")

    def test_get_abstract_text_from_page_prefers_known_fields(self):
        page = {
            "properties": {
                "Notes": {"type": "rich_text", "rich_text": [{"plain_text": "notes text"}]},
                "Abstract": {"type": "rich_text", "rich_text": [{"plain_text": "abstract text"}]},
            }
        }
        self.assertEqual(main.get_abstract_text_from_page(page), "abstract text")

    def test_get_page_title_falls_back_to_title_property(self):
        page = {
            "properties": {
                "Title": {"type": "title", "title": [{"plain_text": "Fallback Title"}]},
            }
        }
        self.assertEqual(main.get_page_title(page), "Fallback Title")

    def test_get_current_stars_from_page_reads_stars_property(self):
        page = {
            "properties": {
                "Stars": {"type": "number", "number": 17},
            }
        }
        self.assertEqual(main.get_current_stars_from_page(page), 17)

    def test_find_github_url_in_json_payload(self):
        payload = {
            "resources": [
                {"name": "homepage", "url": "https://example.com/project"},
                {"name": "code", "url": "https://github.com/foo/bar"},
            ]
        }
        self.assertEqual(main.find_github_url_in_json_payload(payload), "https://github.com/foo/bar")

    def test_find_github_url_in_json_payload_nested(self):
        payload = {
            "data": {
                "paper": {
                    "implementation": {
                        "links": [
                            "https://example.com",
                            "https://github.com/baz/qux."
                        ]
                    }
                }
            }
        }
        self.assertEqual(main.find_github_url_in_json_payload(payload), "https://github.com/baz/qux")

    def test_find_github_url_in_json_payload_returns_none_when_missing(self):
        payload = {"resources": [{"url": "https://example.com/project"}], "title": "paper"}
        self.assertIsNone(main.find_github_url_in_json_payload(payload))

    def test_find_github_url_in_huggingface_paper_html_prefers_github_repo_field(self):
        html = '<script>window.__DATA__={"githubRepo":"https://github.com/foo/bar"}</script>'
        self.assertEqual(
            main.find_github_url_in_huggingface_paper_html(html),
            "https://github.com/foo/bar",
        )

    def test_find_huggingface_paper_id_in_search_html(self):
        html = '<a href="/papers/2603.05078">MoRe</a>'
        self.assertEqual(main.find_huggingface_paper_id_in_search_html(html), "2603.05078")

    def test_find_github_url_in_alphaxiv_legacy_payload_prefers_known_fields(self):
        payload = {
            "paper": {
                "implementation": "https://github.com/foo/bar",
                "marimo_implementation": None,
                "paper_group": {"resources": []},
                "resources": [],
            }
        }
        self.assertEqual(
            main.find_github_url_in_alphaxiv_legacy_payload(payload),
            "https://github.com/foo/bar",
        )

    def test_find_github_url_in_alphaxiv_legacy_payload_falls_back_to_recursive_scan(self):
        payload = {
            "paper": {
                "implementation": None,
                "marimo_implementation": None,
                "paper_group": {"resources": []},
                "resources": [],
            },
            "misc": {
                "links": ["https://github.com/baz/qux."]
            }
        }
        self.assertEqual(
            main.find_github_url_in_alphaxiv_legacy_payload(payload),
            "https://github.com/baz/qux",
        )


class TestNotionResilience(unittest.IsolatedAsyncioTestCase):
    async def test_update_page_properties_writes_stars_property(self):
        client = main.NotionClient("token", 1)
        client.client = types.SimpleNamespace(
            pages=types.SimpleNamespace(
                update=AsyncMock(return_value={"ok": True})
            )
        )

        await client.update_page_properties("page-1", stars_count=42)

        client.client.pages.update.assert_awaited_once_with(
            page_id="page-1",
            properties={"Stars": {"number": 42}},
        )

    async def test_update_page_properties_retries_after_connect_error(self):
        client = main.NotionClient("token", 1)
        client.client = types.SimpleNamespace(
            pages=types.SimpleNamespace(
                update=AsyncMock(side_effect=[Exception("boom"), {"ok": True}])
            )
        )

        await client.update_page_properties("page-1", stars_count=42)

        self.assertEqual(client.client.pages.update.await_count, 2)

    async def test_process_page_records_notion_update_failure_without_crashing_batch(self):
        page = {
            "id": "page-1",
            "url": "https://notion.so/page-1",
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "url", "url": "https://github.com/foo/bar"},
                "Stars": {"type": "number", "number": 10},
            },
        }
        github_client = types.SimpleNamespace(get_star_count=AsyncMock(return_value=(12, None)))
        notion_client = types.SimpleNamespace(
            update_page_properties=AsyncMock(side_effect=Exception("network down"))
        )
        results = {"updated": 0, "skipped": []}
        lock = main.asyncio.Lock()

        await main.process_page(page, 1, 1, github_client, notion_client, results, lock)

        self.assertEqual(results["updated"], 0)
        self.assertEqual(len(results["skipped"]), 1)
        self.assertEqual(results["skipped"][0]["reason"], "Notion update failed: network down")


class TestFallbackResolution(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_repo_prefers_huggingface_when_token_is_configured(self):
        page = {
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "rich_text", "rich_text": []},
            }
        }
        github_client = types.SimpleNamespace(
            huggingface_token="hf_test",
            alphaxiv_token="axv1_test",
        )
        github_client.get_huggingface_paper_html_by_arxiv_id = AsyncMock(
            return_value=('<a href="https://github.com/hf/repo">GitHub</a>', None)
        )
        github_client.get_huggingface_search_html = AsyncMock()
        github_client.get_alphaxiv_paper_legacy = AsyncMock()

        with unittest.mock.patch.object(
            main,
            "resolve_arxiv_id_for_page",
            AsyncMock(return_value=("2603.05078", "url_field", None)),
        ):
            resolution = await main.resolve_repo_for_page(page, github_client)

        self.assertEqual(resolution["source"], "huggingface")
        self.assertEqual(resolution["github_url"], "https://github.com/hf/repo")
        github_client.get_alphaxiv_paper_legacy.assert_not_called()

    async def test_resolve_repo_falls_back_to_alphaxiv_when_huggingface_misses(self):
        page = {
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "rich_text", "rich_text": []},
            }
        }
        github_client = types.SimpleNamespace(
            huggingface_token="hf_test",
            alphaxiv_token="axv1_test",
        )
        github_client.get_huggingface_paper_html_by_arxiv_id = AsyncMock(return_value=("<html></html>", None))
        github_client.get_huggingface_search_html = AsyncMock(return_value=("<html></html>", None))
        github_client.get_alphaxiv_paper_legacy = AsyncMock(
            return_value=({"paper": {"implementation": "https://github.com/ax/repo"}}, None)
        )

        with unittest.mock.patch.object(
            main,
            "resolve_arxiv_id_for_page",
            AsyncMock(return_value=("2603.05078", "url_field", None)),
        ):
            resolution = await main.resolve_repo_for_page(page, github_client)

        self.assertEqual(resolution["source"], "alphaxiv_api")
        self.assertEqual(resolution["github_url"], "https://github.com/ax/repo")
        github_client.get_alphaxiv_paper_legacy.assert_awaited_once()

    async def test_resolve_repo_retries_huggingface_via_title_search_after_direct_page_error(self):
        page = {
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "rich_text", "rich_text": []},
            }
        }
        github_client = types.SimpleNamespace(
            huggingface_token="hf_test",
            alphaxiv_token="axv1_test",
        )
        github_client.get_huggingface_paper_html_by_arxiv_id = AsyncMock(
            side_effect=[
                (None, "Hugging Face Papers error (404)"),
                ('<a href="https://github.com/hf/repo">GitHub</a>', None),
            ]
        )
        github_client.get_huggingface_search_html = AsyncMock(
            return_value=('<a href="/papers/2603.05079">Test Paper</a>', None)
        )
        github_client.get_alphaxiv_paper_legacy = AsyncMock()

        with unittest.mock.patch.object(
            main,
            "resolve_arxiv_id_for_page",
            AsyncMock(return_value=("2603.05078", "url_field", None)),
        ):
            resolution = await main.resolve_repo_for_page(page, github_client)

        self.assertEqual(resolution["source"], "huggingface")
        self.assertEqual(resolution["arxiv_source"], "hf_search")
        self.assertEqual(resolution["github_url"], "https://github.com/hf/repo")
        github_client.get_huggingface_search_html.assert_awaited_once()
        github_client.get_alphaxiv_paper_legacy.assert_not_called()

    async def test_resolve_repo_does_not_fall_back_to_alphaxiv_without_token(self):
        page = {
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "rich_text", "rich_text": []},
            }
        }
        github_client = types.SimpleNamespace(
            huggingface_token="hf_test",
            alphaxiv_token="",
        )
        github_client.get_huggingface_paper_html_by_arxiv_id = AsyncMock(return_value=("<html></html>", None))
        github_client.get_huggingface_search_html = AsyncMock(return_value=("<html></html>", None))
        github_client.get_alphaxiv_paper_legacy = AsyncMock()

        with unittest.mock.patch.object(
            main,
            "resolve_arxiv_id_for_page",
            AsyncMock(return_value=("2603.05078", "url_field", None)),
        ):
            resolution = await main.resolve_repo_for_page(page, github_client)

        self.assertEqual(resolution["github_url"], None)
        self.assertEqual(resolution["reason"], "No Github URL found in Hugging Face Papers")
        github_client.get_alphaxiv_paper_legacy.assert_not_called()

    async def test_resolve_repo_uses_alphaxiv_when_only_alphaxiv_is_configured(self):
        page = {
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "rich_text", "rich_text": []},
            }
        }
        github_client = types.SimpleNamespace(
            huggingface_token="",
            alphaxiv_token="axv1_test",
        )
        github_client.get_huggingface_paper_html_by_arxiv_id = AsyncMock()
        github_client.get_huggingface_search_html = AsyncMock()
        github_client.get_alphaxiv_paper_legacy = AsyncMock(
            return_value=({"paper": {"implementation": "https://github.com/ax/repo"}}, None)
        )

        with unittest.mock.patch.object(
            main,
            "resolve_arxiv_id_for_page",
            AsyncMock(return_value=("2603.05078", "url_field", None)),
        ):
            resolution = await main.resolve_repo_for_page(page, github_client)

        self.assertEqual(resolution["source"], "alphaxiv_api")
        self.assertEqual(resolution["github_url"], "https://github.com/ax/repo")
        github_client.get_huggingface_paper_html_by_arxiv_id.assert_not_called()

    async def test_resolve_repo_skips_fallback_when_no_tokens_are_configured(self):
        page = {
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Test Paper"}]},
                "Github": {"type": "rich_text", "rich_text": []},
            }
        }
        github_client = types.SimpleNamespace(
            huggingface_token="",
            alphaxiv_token="",
        )
        github_client.get_huggingface_paper_html_by_arxiv_id = AsyncMock()
        github_client.get_huggingface_search_html = AsyncMock()
        github_client.get_alphaxiv_paper_legacy = AsyncMock()

        resolution = await main.resolve_repo_for_page(page, github_client)

        self.assertEqual(resolution["github_url"], None)
        self.assertEqual(resolution["reason"], "No fallback discovery token configured")
        github_client.get_huggingface_paper_html_by_arxiv_id.assert_not_called()
        github_client.get_alphaxiv_paper_legacy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
