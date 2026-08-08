import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from vibeagent.action_parsing import parse_tool_action
from vibeagent.actions import execute_action
from vibeagent.agent_approval import build_approval_request
from vibeagent.prompts import format_observations
from vibeagent.tool_catalog_core import tool_category, tool_requires_approval
from vibeagent.tool_catalog_search import get_tool_search_report
from vibeagent.types import WebSearchAction
from vibeagent.web_search import _parse_search_results, search_public_web
from vibeagent.workspace import create_run_workspace


class _Headers:
    def __init__(self, content_type: str = "text/html", charset: str | None = None) -> None:
        self.content_type = content_type
        self.charset = charset

    def get_content_type(self) -> str:
        return self.content_type

    def get_content_charset(self) -> str | None:
        return self.charset


class _Response:
    def __init__(self, body: bytes, content_type: str = "text/html") -> None:
        self.body = body
        self.headers = _Headers(content_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


SEARCH_HTML = b"""
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2Flibrary%2Fasyncio.html">Python asyncio docs</a>
  <a class="result__snippet">Official <b>asyncio</b> documentation.</a>
</div>
<div class="result">
  <a class="result__a" href="https://blog.example.com/asyncio">Asyncio article</a>
  <div class="result__snippet">A third-party article.</div>
</div>
"""


class WebSearchTests(unittest.TestCase):
    def test_parses_redirect_urls_titles_and_snippets(self) -> None:
        results = _parse_search_results(SEARCH_HTML.decode())

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Python asyncio docs")
        self.assertEqual(results[0].url, "https://docs.python.org/3/library/asyncio.html")
        self.assertEqual(results[0].snippet, "Official asyncio documentation.")

    def test_search_filters_allowed_and_blocked_domains(self) -> None:
        with patch("vibeagent.web_search.open_scoped_url", return_value=_Response(SEARCH_HTML)):
            observation = search_public_web(
                "python asyncio",
                max_results=5,
                allowed_domains=("python.org", "example.com"),
                blocked_domains=("blog.example.com",),
            )

        self.assertTrue(observation.ok)
        self.assertEqual([result.url for result in observation.results], ["https://docs.python.org/3/library/asyncio.html"])
        self.assertEqual(observation.total_results, 1)
        self.assertFalse(observation.results_truncated)

    def test_search_rejects_unsupported_response_content(self) -> None:
        with patch(
            "vibeagent.web_search.open_scoped_url",
            return_value=_Response(b"binary", content_type="application/octet-stream"),
        ):
            observation = search_public_web("python docs")

        self.assertFalse(observation.ok)
        self.assertIn("Unsupported search response content type", observation.error or "")

    def test_claude_alias_parses_executes_and_formats_results(self) -> None:
        action = parse_tool_action(
            "WebSearch",
            {
                "query": " python asyncio ",
                "allowed_domains": ["python.org", "*.python.org", "python.org"],
                "blocked_domains": ["discuss.python.org"],
                "max_results": 3,
                "timeout_ms": 1500,
            },
        )
        self.assertEqual(
            action,
            WebSearchAction(
                type="web_search",
                query="python asyncio",
                timeout_ms=1500,
                max_results=3,
                allowed_domains=("python.org", "*.python.org"),
                blocked_domains=("discuss.python.org",),
            ),
        )

        with TemporaryDirectory(prefix="vibeagent-web-search-") as base, patch(
            "vibeagent.runtime_action_executor.search_public_web",
            side_effect=lambda query, **options: search_public_web(query, **options),
        ), patch("vibeagent.web_search.open_scoped_url", return_value=_Response(SEARCH_HTML)):
            observation = execute_action(create_run_workspace(Path(base)), action)

        rendered = format_observations([observation])
        self.assertIn("web_search python asyncio", rendered)
        self.assertIn("Python asyncio docs", rendered)
        self.assertIn("https://docs.python.org/3/library/asyncio.html", rendered)

    def test_search_requires_approval_and_rejects_invalid_domain_filters(self) -> None:
        action = WebSearchAction(type="web_search", query="python docs", allowed_domains=("python.org",))
        request = build_approval_request(action)

        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "web_search")
        self.assertIn("python docs", request.target)
        self.assertEqual(tool_category("WebSearch"), "project")
        self.assertTrue(tool_requires_approval("web_search", ""))
        with self.assertRaisesRegex(ValueError, "domain names"):
            parse_tool_action("WebSearch", {"query": "python", "allowed_domains": ["https://python.org"]})

    def test_native_search_tool_is_discoverable_on_demand(self) -> None:
        report = get_tool_search_report("web search")
        names = [match["name"] for match in report["matches"]]

        self.assertIn("web_search", names)
        self.assertIn("WebSearch", names)


if __name__ == "__main__":
    unittest.main()
