from __future__ import annotations

from typing import Any

from .redaction import redact_sensitive_text
from .types import McpResourceInfo


def normalize_mcp_resource(item: dict[str, Any]) -> McpResourceInfo:
    uri = item.get("uri")
    if (
        not isinstance(uri, str)
        or not uri
        or len(uri) > 4_096
        or any(ord(character) < 32 for character in uri)
    ):
        raise ValueError("MCP resource metadata requires a valid bounded URI.")
    size = item.get("size")
    normalized_size = (
        size
        if isinstance(size, int) and not isinstance(size, bool) and size >= 0
        else None
    )
    return McpResourceInfo(
        uri=uri,
        name=_bounded_metadata_text(item.get("name"), 500),
        title=_bounded_metadata_text(item.get("title"), 500),
        description=_bounded_metadata_text(item.get("description"), 2_000),
        mime_type=_bounded_metadata_text(item.get("mimeType"), 200),
        size=normalized_size,
    )


def mcp_resource_result_text(
    result: dict[str, Any],
    expected_uri: str,
) -> tuple[str, list[str]]:
    contents = result.get("contents")
    if not isinstance(contents, list) or not contents:
        raise ValueError("MCP resources/read result did not include resource contents.")
    parts: list[str] = []
    mime_types: list[str] = []
    for item in contents:
        if not isinstance(item, dict):
            raise ValueError("MCP resource content must be an object.")
        uri = item.get("uri")
        if uri != expected_uri:
            raise ValueError("MCP resource content URI did not match the requested URI.")
        mime_type = _bounded_metadata_text(item.get("mimeType"), 200)
        if mime_type and mime_type not in mime_types:
            mime_types.append(mime_type)
        heading = f"resource: uri={expected_uri} mimeType={mime_type or 'unknown'}"
        text = item.get("text")
        blob = item.get("blob")
        if isinstance(text, str) and blob is None:
            parts.append(f"{heading}\n{text}")
            continue
        if isinstance(blob, str) and text is None:
            parts.append(
                f"{heading}\n[binary content omitted; encodedChars={len(blob)}]"
            )
            continue
        raise ValueError(
            "MCP resource content must contain exactly one text or blob field."
        )
    return "\n\n".join(parts), mime_types


def _bounded_metadata_text(value: object, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return redact_sensitive_text(value[:maximum])
