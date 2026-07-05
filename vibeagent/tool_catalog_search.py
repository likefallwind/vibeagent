from __future__ import annotations

import re

from .tool_categories import valid_tool_categories
from .tool_catalog_core import suggest_tool_names, tool_category, tool_requires_approval
from .tool_definitions import AGENT_TOOL_DEFINITIONS


def get_tool_search_report(
    query: str | None,
    max_matches: int = 20,
    category: str | None = None,
    approval_required: bool | None = None,
) -> dict[str, object]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return {
            "ok": False,
            "query": "",
            "category": category,
            "approvalRequired": approval_required,
            "matches": [],
            "total": 0,
            "shown": 0,
            "truncated": False,
            "suggestions": [],
            "message": "Usage: /tool-search <query>",
        }
    if max_matches < 1:
        raise ValueError("max_matches must be at least 1")
    if max_matches > 100:
        raise ValueError("max_matches must be at most 100")

    normalized_category = category.strip().lower() if isinstance(category, str) and category.strip() else None
    valid_categories = set(valid_tool_categories())
    if normalized_category is not None and normalized_category not in valid_categories:
        return {
            "ok": False,
            "query": normalized_query,
            "category": normalized_category,
            "approvalRequired": approval_required,
            "matches": [],
            "total": 0,
            "shown": 0,
            "truncated": False,
            "suggestions": sorted(valid_categories),
            "message": f"Unknown tool category: {normalized_category}.",
        }

    terms = _search_terms(normalized_query)
    matches = []
    for tool in AGENT_TOOL_DEFINITIONS:
        match = _match_tool(tool, normalized_query, terms)
        if match is None:
            continue
        if normalized_category is not None and match["category"] != normalized_category:
            continue
        if approval_required is not None and bool(match["approvalRequired"]) != approval_required:
            continue
        matches.append(match)

    matches.sort(key=lambda item: (-int(item["score"]), str(item["name"])))
    total = len(matches)
    shown_matches = matches[:max_matches]
    truncated = total > len(shown_matches)
    return {
        "ok": True,
        "query": normalized_query,
        "category": normalized_category,
        "approvalRequired": approval_required,
        "matches": shown_matches,
        "total": total,
        "shown": len(shown_matches),
        "truncated": truncated,
        "suggestions": suggest_tool_names(normalized_query),
        "message": f"Found {total} matching tool(s).",
    }


def format_tool_search_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("ok")):
        return str(report.get("message") or "No matching tools.")
    lines = [
        "Tool search:",
        f"  query: {report.get('query') or ''}",
        f"  matches: {report.get('shown', 0)}/{report.get('total', 0)}",
        f"  truncated: {'yes' if bool(report.get('truncated')) else 'no'}",
    ]
    if report.get("category"):
        lines.append(f"  category: {report.get('category')}")
    if report.get("approvalRequired") is not None:
        lines.append(f"  approvalRequired: {'yes' if bool(report.get('approvalRequired')) else 'no'}")
    matches = report.get("matches") if isinstance(report.get("matches"), list) else []
    for match in matches:
        if not isinstance(match, dict):
            continue
        description = str(match.get("description") or "").strip()
        suffix = f" - {description}" if description else ""
        lines.append(
            f"  - {match.get('name')} [{match.get('category')}, "
            f"approvalRequired={'yes' if bool(match.get('approvalRequired')) else 'no'}, "
            f"score={match.get('score')}]"
            f"{suffix}"
        )
        matched_fields = match.get("matchedFields")
        if isinstance(matched_fields, list) and matched_fields:
            lines.append(f"    matched: {', '.join(str(item) for item in matched_fields)}")
        required = match.get("required")
        if isinstance(required, list) and required:
            lines.append(f"    required: {', '.join(str(item) for item in required)}")
    return "\n".join(lines)


def get_tool_search_text(
    query: str | None,
    max_matches: int = 20,
    category: str | None = None,
    approval_required: bool | None = None,
) -> str:
    return format_tool_search_report_text(
        get_tool_search_report(query, max_matches=max_matches, category=category, approval_required=approval_required)
    )


def _search_terms(query: str) -> list[str]:
    return [term for term in re.split(r"[\s,_/-]+", query.lower()) if term]


def _match_tool(tool: dict[str, object], query: str, terms: list[str]) -> dict[str, object] | None:
    name = str(tool.get("name", ""))
    description = str(tool.get("description", "")).strip()
    schema = tool.get("input_schema")
    schema_obj = schema if isinstance(schema, dict) else {}
    required = schema_obj.get("required")
    required_names = [item for item in required if isinstance(item, str)] if isinstance(required, list) else []
    properties = schema_obj.get("properties")
    property_names = [str(key) for key in properties.keys()] if isinstance(properties, dict) else []
    property_descriptions = _property_descriptions(properties if isinstance(properties, dict) else {})
    category = tool_category(name)
    approval = tool_requires_approval(name, description)
    field_values = {
        "name": name,
        "category": category,
        "description": description,
        "required": " ".join(required_names),
        "properties": " ".join([*property_names, *property_descriptions]),
    }
    score = 0
    matched_fields: list[str] = []
    normalized_query = query.lower()
    normalized_name = name.lower()
    if normalized_name == normalized_query:
        score += 200
        matched_fields.append("name")
    elif normalized_name.startswith(normalized_query):
        score += 120
        matched_fields.append("name")
    elif normalized_query in normalized_name:
        score += 90
        matched_fields.append("name")

    for field, value in field_values.items():
        lowered = value.lower()
        if not lowered:
            continue
        field_score = 0
        if normalized_query in lowered and field != "name":
            field_score += 30
        for term in terms:
            if term in lowered:
                field_score += _field_weight(field)
        if field_score > 0:
            score += field_score
            if field not in matched_fields:
                matched_fields.append(field)

    if score <= 0:
        return None
    return {
        "name": name,
        "category": category,
        "approvalRequired": approval,
        "score": score,
        "matchedFields": matched_fields,
        "description": description,
        "required": required_names,
        "properties": property_names,
    }


def _field_weight(field: str) -> int:
    return {
        "name": 40,
        "category": 20,
        "description": 12,
        "required": 10,
        "properties": 8,
    }.get(field, 1)


def _property_descriptions(properties: dict[object, object]) -> list[str]:
    descriptions: list[str] = []
    for value in properties.values():
        schema_value = value if isinstance(value, dict) else {}
        description = schema_value.get("description")
        if isinstance(description, str) and description.strip():
            descriptions.append(description)
    return descriptions
