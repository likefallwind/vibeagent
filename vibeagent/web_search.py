from __future__ import annotations

import socket
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from .network_url_safety import UrlSafetyError, open_scoped_url
from .observation_runtime_types import WebSearchObservation, WebSearchResult


_SEARCH_ENDPOINT = "https://html.duckduckgo.com/html/"
_MAX_RESPONSE_BYTES = 1_000_000


class _SearchHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[WebSearchResult] = []
        self._capture: str | None = None
        self._parts: list[str] = []
        self._href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._capture = "title"
            self._parts = []
            self._href = attributes.get("href") or ""
        elif "result__snippet" in classes and self.results:
            self._capture = "snippet"
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._capture == "title" and tag == "a":
            title = _normalize_inline_text(" ".join(self._parts))
            url = _result_url(self._href)
            if title and url:
                self.results.append(WebSearchResult(title=title, url=url, snippet=""))
            self._reset_capture()
        elif self._capture == "snippet" and tag in {"a", "div", "span"}:
            snippet = _normalize_inline_text(" ".join(self._parts))
            if snippet:
                latest = self.results[-1]
                self.results[-1] = WebSearchResult(title=latest.title, url=latest.url, snippet=snippet)
            self._reset_capture()

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._parts.append(data)

    def _reset_capture(self) -> None:
        self._capture = None
        self._parts = []
        self._href = ""


def search_public_web(
    query: str,
    *,
    timeout_ms: int = 10_000,
    max_results: int = 5,
    allowed_domains: tuple[str, ...] = (),
    blocked_domains: tuple[str, ...] = (),
) -> WebSearchObservation:
    search_url = f"{_SEARCH_ENDPOINT}?{urlencode({'q': query})}"
    request = urllib.request.Request(search_url, headers={"User-Agent": "vibeagent-web-search/1.0"})
    try:
        with open_scoped_url(request, timeout=timeout_ms / 1000, scope="public") as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                raise UrlSafetyError(f"Unsupported search response content type: {content_type}.")
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                raise UrlSafetyError("Search response exceeded the maximum supported size.")
            try:
                html = raw.decode(charset, errors="replace")
            except LookupError:
                html = raw.decode("utf-8", errors="replace")
            parsed = _parse_search_results(html)
            filtered = [
                result
                for result in parsed
                if _result_domain_allowed(result.url, allowed_domains, blocked_domains)
            ]
            results = filtered[:max_results]
            return WebSearchObservation(
                kind="web_search",
                ok=True,
                query=query,
                results=results,
                total_results=len(filtered),
                results_truncated=len(filtered) > len(results),
                allowed_domains=list(allowed_domains),
                blocked_domains=list(blocked_domains),
                error=None,
                message=f"Found {len(results)} public web search result(s) for {query!r}.",
            )
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        return WebSearchObservation(
            kind="web_search",
            ok=False,
            query=query,
            results=[],
            total_results=0,
            results_truncated=False,
            allowed_domains=list(allowed_domains),
            blocked_domains=list(blocked_domains),
            error=str(error),
            message=f"Could not search the public web for {query!r}: {error}.",
        )


def _parse_search_results(html: str) -> list[WebSearchResult]:
    parser = _SearchHtmlParser()
    parser.feed(html)
    return parser.results


def _result_url(href: str) -> str | None:
    if not href:
        return None
    absolute = urljoin(_SEARCH_ENDPOINT, href)
    parsed = urlparse(absolute)
    if (
        parsed.hostname
        and (parsed.hostname == "duckduckgo.com" or parsed.hostname.endswith(".duckduckgo.com"))
        and parsed.path == "/l/"
    ):
        redirected = parse_qs(parsed.query).get("uddg", [None])[0]
        if isinstance(redirected, str):
            absolute = redirected
            parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return absolute


def _result_domain_allowed(url: str, allowed_domains: tuple[str, ...], blocked_domains: tuple[str, ...]) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    if not hostname:
        return False
    if any(_domain_matches(hostname, domain) for domain in blocked_domains):
        return False
    return not allowed_domains or any(_domain_matches(hostname, domain) for domain in allowed_domains)


def _domain_matches(hostname: str, domain: str) -> bool:
    normalized = domain.lower().removeprefix("*.")
    return hostname == normalized or hostname.endswith(f".{normalized}")


def _normalize_inline_text(value: str) -> str:
    return " ".join(value.split())
