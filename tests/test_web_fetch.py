import socket
import unittest
from unittest.mock import patch

from vibeagent.agent_approval import build_approval_request
from vibeagent.network_url_safety import UrlSafetyError, _ScopedRedirectHandler, validate_scoped_url
from vibeagent.tool_catalog_core import tool_category, tool_requires_approval
from vibeagent.types import WebFetchAction
from vibeagent.web_fetch import _extract_readable_text, fetch_public_document


def _address_info(*addresses: str):
    return [
        (socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
        for address in addresses
    ]


class _Headers:
    def __init__(self, content_type: str, charset: str | None = None) -> None:
        self.content_type = content_type
        self.charset = charset

    def get_content_type(self) -> str:
        return self.content_type

    def get_content_charset(self) -> str | None:
        return self.charset


class _Response:
    reason = "OK"

    def __init__(self, body: bytes, content_type: str = "text/html") -> None:
        self.body = body
        self.headers = _Headers(content_type)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def getcode(self) -> int:
        return 200

    def geturl(self) -> str:
        return "https://docs.example.com/guide"

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


class NetworkUrlSafetyTests(unittest.TestCase):
    def test_public_scope_accepts_only_global_addresses(self) -> None:
        with patch("vibeagent.network_url_safety.socket.getaddrinfo", return_value=_address_info("93.184.216.34")):
            validate_scoped_url("https://example.com/docs", "public")

        for address in ("127.0.0.1", "10.0.0.2", "169.254.1.2", "::1"):
            with self.subTest(address=address), patch(
                "vibeagent.network_url_safety.socket.getaddrinfo", return_value=_address_info(address)
            ):
                with self.assertRaisesRegex(UrlSafetyError, "public"):
                    validate_scoped_url("https://example.com/docs", "public")

    def test_public_scope_rejects_mixed_dns_and_url_credentials(self) -> None:
        with patch(
            "vibeagent.network_url_safety.socket.getaddrinfo",
            return_value=_address_info("93.184.216.34", "127.0.0.1"),
        ):
            with self.assertRaisesRegex(UrlSafetyError, "127.0.0.1"):
                validate_scoped_url("https://example.com", "public")
        with self.assertRaisesRegex(UrlSafetyError, "credentials"):
            validate_scoped_url("https://user:secret@example.com", "public")

    def test_local_scope_rejects_public_addresses(self) -> None:
        with patch("vibeagent.network_url_safety.socket.getaddrinfo", return_value=_address_info("93.184.216.34")):
            with self.assertRaisesRegex(UrlSafetyError, "local or private"):
                validate_scoped_url("https://example.com", "local")

    def test_redirect_handler_revalidates_destination(self) -> None:
        handler = _ScopedRedirectHandler("public")
        with patch("vibeagent.network_url_safety.socket.getaddrinfo", return_value=_address_info("127.0.0.1")):
            with self.assertRaisesRegex(UrlSafetyError, "public"):
                handler.redirect_request(None, None, 302, "Found", {}, "http://localhost/admin")

    def test_https_only_redirect_handler_rejects_public_http_downgrade(self) -> None:
        handler = _ScopedRedirectHandler("public", require_https=True)
        with patch("vibeagent.network_url_safety.socket.getaddrinfo", return_value=_address_info("93.184.216.34")):
            with self.assertRaisesRegex(UrlSafetyError, "must use HTTPS"):
                handler.redirect_request(None, None, 302, "Found", {}, "http://example.com/catalog.json")


class WebFetchTests(unittest.TestCase):
    def test_extracts_readable_html_without_script_or_style(self) -> None:
        title, text = _extract_readable_text(
            b"<html><head><title> API Guide </title><style>hidden</style></head>"
            b"<body><h1>Quick start</h1><script>secret()</script><p>Use the client.</p></body></html>",
            "text/html",
            "utf-8",
        )

        self.assertEqual(title, "API Guide")
        self.assertIn("Quick start", text)
        self.assertIn("Use the client.", text)
        self.assertNotIn("hidden", text)
        self.assertNotIn("secret", text)

    def test_fetch_returns_bounded_text_and_metadata(self) -> None:
        response = _Response(b"<title>Guide</title><p>abcdefghij</p>")
        with patch("vibeagent.web_fetch.open_scoped_url", return_value=response):
            observation = fetch_public_document("https://docs.example.com/guide", max_text_chars=5)

        self.assertTrue(observation.ok)
        self.assertEqual(observation.status, 200)
        self.assertEqual(observation.title, "Guide")
        self.assertEqual(len(observation.text), 5)
        self.assertTrue(observation.text_truncated)

    def test_fetch_rejects_binary_content(self) -> None:
        with patch(
            "vibeagent.web_fetch.open_scoped_url",
            return_value=_Response(b"binary", content_type="application/octet-stream"),
        ):
            observation = fetch_public_document("https://example.com/archive.bin")

        self.assertFalse(observation.ok)
        self.assertIn("Unsupported document content type", observation.error or "")

    def test_tool_is_project_scoped_and_requires_approval(self) -> None:
        action = WebFetchAction(type="web_fetch", url="https://docs.example.com")
        request = build_approval_request(action)

        self.assertIsNotNone(request)
        self.assertEqual(request.action_type, "web_fetch")
        self.assertEqual(request.target, action.url)
        self.assertEqual(tool_category("web_fetch"), "project")
        self.assertTrue(tool_requires_approval("web_fetch", ""))


if __name__ == "__main__":
    unittest.main()
