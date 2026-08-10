from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .mcp_protocol import McpToolsClient
from .redaction import redact_sensitive_text
from .types import McpResourceInfo, McpResourceTemplateInfo


_URI_TEMPLATE_EXPRESSION = re.compile(r"\{([^{}]+)\}")
_URI_TEMPLATE_VARIABLE = re.compile(
    r"(?:[A-Za-z0-9_]|%[0-9A-Fa-f]{2})(?:(?:[A-Za-z0-9_.])|%[0-9A-Fa-f]{2})*(?::[1-9][0-9]{0,3}|\*)?"
)


@dataclass(frozen=True)
class McpResourceCatalog:
    resources: list[McpResourceInfo]
    templates: list[McpResourceTemplateInfo]
    resource_total: int
    template_total: int
    truncated: bool

    @property
    def total(self) -> int:
        return self.resource_total + self.template_total

    def matching_template(self, uri: str) -> str | None:
        for template in self.templates:
            if mcp_uri_matches_template(uri, template.uri_template):
                return template.uri_template
        return None


def discover_mcp_resources(
    client: McpToolsClient,
    *,
    max_resources: int,
    max_templates: int,
) -> McpResourceCatalog:
    raw_resources, resource_total, resources_truncated = client.list_resources(
        max_resources
    )
    raw_templates, template_total, templates_truncated = (
        client.list_resource_templates(max_templates)
    )
    resources = [normalize_mcp_resource(item) for item in raw_resources]
    templates = [normalize_mcp_resource_template(item) for item in raw_templates]
    uris = [resource.uri for resource in resources]
    if len(set(uris)) != len(uris):
        raise ValueError("MCP resource catalog contains duplicate URIs.")
    uri_templates = [template.uri_template for template in templates]
    if len(set(uri_templates)) != len(uri_templates):
        raise ValueError("MCP resource catalog contains duplicate URI templates.")
    return McpResourceCatalog(
        resources=resources,
        templates=templates,
        resource_total=resource_total,
        template_total=template_total,
        truncated=resources_truncated or templates_truncated,
    )


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


def normalize_mcp_resource_template(
    item: dict[str, Any],
) -> McpResourceTemplateInfo:
    uri_template = item.get("uriTemplate")
    if not isinstance(uri_template, str):
        raise ValueError("MCP resource template metadata requires a URI template.")
    _uri_template_pattern(uri_template)
    return McpResourceTemplateInfo(
        uri_template=uri_template,
        name=_bounded_metadata_text(item.get("name"), 500),
        title=_bounded_metadata_text(item.get("title"), 500),
        description=_bounded_metadata_text(item.get("description"), 2_000),
        mime_type=_bounded_metadata_text(item.get("mimeType"), 200),
    )


def mcp_uri_matches_template(uri: str, uri_template: str) -> bool:
    if (
        not uri
        or len(uri) > 4_096
        or any(ord(character) < 32 for character in uri)
        or "{" in uri
        or "}" in uri
    ):
        return False
    return re.fullmatch(_uri_template_pattern(uri_template), uri) is not None


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


def _uri_template_pattern(uri_template: str) -> str:
    if (
        not uri_template
        or len(uri_template) > 4_096
        or any(ord(character) < 32 for character in uri_template)
    ):
        raise ValueError("MCP resource template requires a valid bounded URI template.")
    parts: list[str] = []
    position = 0
    for match in _URI_TEMPLATE_EXPRESSION.finditer(uri_template):
        literal = uri_template[position : match.start()]
        if "{" in literal or "}" in literal:
            raise ValueError("MCP resource template contains malformed braces.")
        parts.append(re.escape(literal))
        parts.append(_uri_template_expression_pattern(match.group(1)))
        position = match.end()
    literal = uri_template[position:]
    if "{" in literal or "}" in literal:
        raise ValueError("MCP resource template contains malformed braces.")
    parts.append(re.escape(literal))
    return "".join(parts)


def _uri_template_expression_pattern(expression: str) -> str:
    operator = expression[0] if expression and expression[0] in "+#./;?&" else ""
    variable_text = expression[1:] if operator else expression
    variables = variable_text.split(",")
    if not variables or any(
        not variable or _URI_TEMPLATE_VARIABLE.fullmatch(variable) is None
        for variable in variables
    ):
        raise ValueError("MCP resource template contains an invalid RFC 6570 expression.")
    names = [re.split(r"[:*]", variable, maxsplit=1)[0] for variable in variables]
    if operator == "+":
        return ".*"
    if operator == "#":
        return "(?:#.*)?"
    if operator == ".":
        return r"(?:\.[^/?#]*)?"
    if operator == "/":
        return r"(?:/[^?#]*)?"
    if operator in {"?", "&"}:
        prefix = r"\?" if operator == "?" else "&"
        names_pattern = "|".join(re.escape(name) for name in names)
        return rf"(?:{prefix}(?:{names_pattern})=[^&#]*(?:&(?:{names_pattern})=[^&#]*)*)?"
    if operator == ";":
        names_pattern = "|".join(re.escape(name) for name in names)
        return rf"(?:;(?:{names_pattern})(?:=[^;/?#]*)?(?:;(?:{names_pattern})(?:=[^;/?#]*)?)*)?"
    return r"[A-Za-z0-9._~%\-,]*"
