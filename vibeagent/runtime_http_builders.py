from __future__ import annotations

import re
from typing import Any

from .types import HttpCheckObservation, HttpFetchObservation


def build_http_check_observation(
    *,
    url: str,
    final_url: str,
    status: int,
    reason: str | None,
    timeout_ms: int,
    max_body_chars: int,
    contains: str | None,
    regex: bool,
    body_reader: Any,
    error: str | None,
) -> HttpCheckObservation:
    body, body_truncated = read_limited_text_body(body_reader, max_body_chars)
    matched = False
    if contains is not None:
        try:
            matched = re.search(contains, body) is not None if regex else contains in body
        except re.error as regex_error:
            return HttpCheckObservation(
                kind="http_check",
                ok=False,
                url=url,
                final_url=final_url,
                status=status,
                reason=reason,
                timeout_ms=timeout_ms,
                reachable=True,
                matched=False,
                matched_pattern=contains,
                body=body,
                body_truncated=body_truncated,
                max_body_chars=max_body_chars,
                error=str(regex_error),
                message=f"{url} returned HTTP {status}, but contains regex is invalid: {regex_error}.",
            )
    match_detail = ""
    if contains is not None:
        match_detail = " Body pattern matched." if matched else " Body pattern did not match."
    return HttpCheckObservation(
        kind="http_check",
        ok=True,
        url=url,
        final_url=final_url,
        status=status,
        reason=reason,
        timeout_ms=timeout_ms,
        reachable=True,
        matched=matched,
        matched_pattern=contains,
        body=body,
        body_truncated=body_truncated,
        max_body_chars=max_body_chars,
        error=error,
        message=f"{final_url} returned HTTP {status}.{match_detail}",
    )


def build_http_fetch_observation(
    *,
    url: str,
    final_url: str,
    status: int,
    reason: str | None,
    content_type: str | None,
    timeout_ms: int,
    max_body_chars: int,
    body_reader: Any,
    error: str | None,
) -> HttpFetchObservation:
    body, body_truncated = read_limited_text_body(body_reader, max_body_chars)
    return HttpFetchObservation(
        kind="http_fetch",
        ok=True,
        url=url,
        final_url=final_url,
        status=status,
        reason=reason,
        content_type=content_type,
        timeout_ms=timeout_ms,
        reachable=True,
        body=body,
        body_truncated=body_truncated,
        max_body_chars=max_body_chars,
        error=error,
        message=f"{final_url} returned HTTP {status}.",
    )


def read_limited_text_body(body_reader: Any, max_body_chars: int) -> tuple[str, bool]:
    raw = body_reader(max_body_chars + 1)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    elif not isinstance(raw, bytes):
        raw = bytes(raw)
    body_truncated = len(raw) > max_body_chars
    body = raw[:max_body_chars].decode("utf-8", errors="replace")
    return body, body_truncated


def response_content_type(response: Any) -> str | None:
    getheader = getattr(response, "getheader", None)
    if callable(getheader):
        value = getheader("Content-Type")
        return str(value) if value else None
    headers = getattr(response, "headers", None)
    if isinstance(headers, dict):
        value = headers.get("Content-Type") or headers.get("content-type")
        return str(value) if value else None
    return None
