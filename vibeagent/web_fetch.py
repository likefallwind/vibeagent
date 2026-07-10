from __future__ import annotations

import re
import socket
import urllib.error
import urllib.request
from html.parser import HTMLParser

from .network_url_safety import UrlSafetyError, open_scoped_url
from .observation_runtime_types import WebFetchObservation


_TEXT_CONTENT_TYPES = {"application/json", "application/xml", "application/xhtml+xml"}


class _ReadableHtmlParser(HTMLParser):
    _IGNORED = {"script", "style", "svg", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._IGNORED:
            self._ignored_depth += 1
        elif tag == "title" and self._ignored_depth == 0:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._IGNORED and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)


def fetch_public_document(url: str, timeout_ms: int = 10_000, max_text_chars: int = 20_000) -> WebFetchObservation:
    request = urllib.request.Request(url, headers={"User-Agent": "vibeagent-web-fetch/0.1"})
    try:
        with open_scoped_url(request, timeout=timeout_ms / 1000, scope="public") as response:
            status = int(response.getcode())
            final_url = str(response.geturl())
            content_type = response.headers.get_content_type()
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read(max_text_chars * 4 + 1)
            title, text = _extract_readable_text(raw, content_type, charset)
            truncated = len(text) > max_text_chars or len(raw) > max_text_chars * 4
            text = text[:max_text_chars]
            return WebFetchObservation(
                kind="web_fetch",
                ok=True,
                url=url,
                final_url=final_url,
                status=status,
                content_type=content_type,
                title=title,
                text=text,
                text_truncated=truncated,
                max_text_chars=max_text_chars,
                error=None,
                message=f"Fetched public document {final_url} with HTTP {status}.",
            )
    except (UrlSafetyError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        return WebFetchObservation(
            kind="web_fetch",
            ok=False,
            url=url,
            final_url=None,
            status=None,
            content_type=None,
            title=None,
            text="",
            text_truncated=False,
            max_text_chars=max_text_chars,
            error=str(error),
            message=f"Could not fetch public document {url}: {error}.",
        )


def _extract_readable_text(raw: bytes, content_type: str, charset: str) -> tuple[str | None, str]:
    if not (content_type.startswith("text/") or content_type in _TEXT_CONTENT_TYPES):
        raise UrlSafetyError(f"Unsupported document content type: {content_type}.")
    try:
        decoded = raw.decode(charset, errors="replace")
    except LookupError:
        decoded = raw.decode("utf-8", errors="replace")
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = _ReadableHtmlParser()
        parser.feed(decoded)
        title = _normalize_text(" ".join(parser.title_parts)) or None
        return title, _normalize_text("\n".join(parser.text_parts))
    return None, _normalize_text(decoded)


def _normalize_text(value: str) -> str:
    lines = (re.sub(r"\s+", " ", line).strip() for line in value.splitlines())
    return "\n".join(line for line in lines if line)
