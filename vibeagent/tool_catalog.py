from __future__ import annotations

import re

from .tool_definitions import AGENT_TOOL_DEFINITIONS


APPROVAL_REQUIRED_TOOL_NAMES = {
    "append_file",
    "checkpoint_delete",
    "checkpoint_prune",
    "checkpoint_restore",
    "code_rename",
    "copy_dir",
    "copy_dirs",
    "copy_file",
    "copy_files",
    "create_dir",
    "create_dirs",
    "delete_empty_dir",
    "delete_empty_dirs",
    "delete_file",
    "delete_files",
    "edit_file",
    "git_commit",
    "git_fetch",
    "git_pull",
    "git_push",
    "git_restore",
    "git_stage",
    "git_stash",
    "git_stash_apply",
    "git_stash_drop",
    "git_switch",
    "git_unstage",
    "insert_lines",
    "json_patch",
    "json_remove",
    "json_set",
    "move_dir",
    "move_dirs",
    "move_file",
    "move_files",
    "multi_edit_file",
    "patch_file",
    "patch_files",
    "python_rename",
    "regex_replace",
    "replace_lines",
    "replace_python_definition",
    "run_command",
    "run_commands",
    "run_focused_test_commands",
    "run_session_verification",
    "run_suggested_checks",
    "set_executable",
    "start_command",
    "stop_all_processes",
    "stop_process",
    "write_file",
    "write_files",
    "write_process",
}


def get_tools_report() -> dict[str, object]:
    categories = categorize_tools()
    category_by_tool = {name: category for category, names in categories.items() for name in names}
    tools: list[dict[str, object]] = []
    approval_required: list[str] = []
    read_only: list[str] = []
    for tool in AGENT_TOOL_DEFINITIONS:
        name = str(tool.get("name", ""))
        description = str(tool.get("description", "")).strip()
        schema = tool.get("input_schema")
        schema_obj = schema if isinstance(schema, dict) else {}
        required = schema_obj.get("required")
        required_names = [item for item in required if isinstance(item, str)] if isinstance(required, list) else []
        properties = schema_obj.get("properties")
        property_names = [str(key) for key in properties.keys()] if isinstance(properties, dict) else []
        approval = tool_requires_approval(name, description)
        if approval:
            approval_required.append(name)
        else:
            read_only.append(name)
        tools.append(
            {
                "name": name,
                "category": category_by_tool.get(name, "other"),
                "description": description,
                "approvalRequired": approval,
                "required": required_names,
                "properties": property_names,
            }
        )
    category_items = [
        {"name": category, "total": len(names), "tools": list(names)}
        for category, names in categories.items()
        if names
    ]
    return {
        "ok": True,
        "total": len(tools),
        "approvalRequired": {"total": len(approval_required), "tools": approval_required},
        "readOnly": {"total": len(read_only), "tools": read_only},
        "categories": category_items,
        "tools": tools,
        "message": f"Found {len(tools)} model tool(s).",
    }


def format_tools_report_text(report: dict[str, object]) -> str:
    categories = report.get("categories") if isinstance(report.get("categories"), list) else []
    approval_required = report.get("approvalRequired") if isinstance(report.get("approvalRequired"), dict) else {}
    lines = [
        "Tools:",
        f"  total: {report.get('total', 0)}",
        f"  approvalRequired: {approval_required.get('total', 0)}",
    ]
    for item in categories:
        if not isinstance(item, dict):
            continue
        category = item.get("name")
        names = item.get("tools")
        if isinstance(category, str) and isinstance(names, list) and names:
            clean_names = [str(name) for name in names]
            lines.append(f"  {category}: {len(clean_names)}")
            lines.extend(wrap_tool_names(clean_names))
    return "\n".join(lines)


def get_tools_text() -> str:
    return format_tools_report_text(get_tools_report())


def get_tool_report(name: str | None) -> dict[str, object]:
    if not name:
        return {
            "ok": False,
            "found": False,
            "name": "",
            "suggestions": [],
            "message": "Usage: /tool <name>",
        }
    normalized = name.strip()
    tool = next((item for item in AGENT_TOOL_DEFINITIONS if item.get("name") == normalized), None)
    if tool is None:
        suggestions = suggest_tool_names(normalized)
        suffix = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
        return {
            "ok": False,
            "found": False,
            "name": normalized,
            "suggestions": suggestions,
            "message": f"Tool not found: {normalized}.{suffix}",
        }

    description = str(tool.get("description", "")).strip()
    schema = tool.get("input_schema")
    schema_obj = schema if isinstance(schema, dict) else {}
    properties = schema_obj.get("properties")
    required = schema_obj.get("required")
    required_names = [item for item in required if isinstance(item, str)] if isinstance(required, list) else []
    property_items = properties.items() if isinstance(properties, dict) else []
    property_reports: list[dict[str, object]] = []
    for property_name, value in property_items:
        schema_value = value if isinstance(value, dict) else {}
        property_reports.append(
            {
                "name": str(property_name),
                "type": schema_value.get("type", ""),
                "required": str(property_name) in required_names,
                "description": schema_value.get("description", ""),
                "enum": schema_value.get("enum", []),
            }
        )
    return {
        "ok": True,
        "found": True,
        "name": normalized,
        "category": tool_category(normalized),
        "description": description,
        "approvalRequired": tool_requires_approval(normalized, description),
        "required": required_names,
        "properties": property_reports,
        "schema": schema_obj,
        "message": f"Found tool: {normalized}.",
    }


def format_tool_report_text(report: dict[str, object]) -> str:
    if not bool(report.get("ok")):
        return str(report.get("message") or "Tool not found.")
    normalized = str(report.get("name", ""))
    description = str(report.get("description", "")).strip()
    required = report.get("required")
    required_names = [item for item in required if isinstance(item, str)] if isinstance(required, list) else []
    properties = report.get("properties") if isinstance(report.get("properties"), list) else []
    approval = "yes" if bool(report.get("approvalRequired")) else "no"
    lines = [
        f"Tool: {normalized}",
        f"  category: {report.get('category', 'other')}",
        f"  approvalRequired: {approval}",
    ]
    if description:
        lines.append(f"  description: {description}")
    if required_names:
        lines.append(f"  required: {', '.join(required_names)}")
    if properties:
        lines.append("  input:")
        schema = report.get("schema") if isinstance(report.get("schema"), dict) else {}
        schema_properties = schema.get("properties")
        for property_item in properties:
            if not isinstance(property_item, dict):
                continue
            property_name = str(property_item.get("name", ""))
            if not property_name:
                continue
            value = schema_properties.get(property_name) if isinstance(schema_properties, dict) else {}
            if isinstance(value, dict):
                lines.append(format_tool_property(property_name, value, required=property_name in required_names))
    if not properties:
        lines.append("  input: none")
    return "\n".join(lines)


def get_tool_text(name: str | None) -> str:
    return format_tool_report_text(get_tool_report(name))


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
    valid_categories = set(categorize_tools())
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


def get_permissions_report(approval_policy: str = "ask") -> dict[str, object]:
    from .workflow_commands import get_command_hard_block_report

    approval_required = sorted(
        str(tool["name"])
        for tool in AGENT_TOOL_DEFINITIONS
        if tool_requires_approval(str(tool.get("name", "")), str(tool.get("description", "")))
    )
    read_only = sorted(
        str(tool["name"])
        for tool in AGENT_TOOL_DEFINITIONS
        if not tool_requires_approval(str(tool.get("name", "")), str(tool.get("description", "")))
    )
    categories: dict[str, list[str]] = {
        "edit": [],
        "git": [],
        "command": [],
        "session": [],
        "checkpoint": [],
        "other": [],
    }
    for name in approval_required:
        category = tool_category(name)
        categories[category if category in categories else "other"].append(name)
    return {
        "approvalPolicy": approval_policy,
        "approvalRequiredTools": {
            "count": len(approval_required),
            "tools": approval_required,
            "byCategory": categories,
        },
        "readOnlyTools": {
            "count": len(read_only),
            "tools": read_only,
        },
        "commandHardBlocks": get_command_hard_block_report(),
    }


def get_permissions_text(approval_policy: str = "ask") -> str:
    return format_permissions_report_text(get_permissions_report(approval_policy))


def format_permissions_report_text(report: dict[str, object]) -> str:
    approval_required = report.get("approvalRequiredTools") if isinstance(report.get("approvalRequiredTools"), dict) else {}
    read_only = report.get("readOnlyTools") if isinstance(report.get("readOnlyTools"), dict) else {}
    categories = approval_required.get("byCategory") if isinstance(approval_required.get("byCategory"), dict) else {}
    lines = [
        "Permissions:",
        f"  approvalPolicy: {report.get('approvalPolicy') or 'ask'}",
        f"  approvalRequiredTools: {int(approval_required.get('count', 0) or 0)}",
        f"  readOnlyTools: {int(read_only.get('count', 0) or 0)}",
        "  approvalRequiredByCategory:",
    ]
    category_items = categories.items() if isinstance(categories, dict) else []
    for category, names in category_items:
        if names:
            lines.append(f"    {category}: {len(names)}")
            lines.extend(f"      {line.strip()}" for line in wrap_tool_names(names, width=96))

    lines.extend(
        [
            "  commandHardBlocks:",
            "    These commands stay blocked even when approvalPolicy is allow.",
        ]
    )
    hard_blocks = report.get("commandHardBlocks")
    if isinstance(hard_blocks, dict):
        for check in hard_blocks.get("checks", []):
            if isinstance(check, dict) and check.get("reason"):
                lines.append(f"    - {check.get('command')}: {check.get('reason')}")
    return "\n".join(lines)


def suggest_tool_names(name: str, limit: int = 5) -> list[str]:
    if not name:
        return []
    names = [str(tool["name"]) for tool in AGENT_TOOL_DEFINITIONS]
    exact_prefix = [tool_name for tool_name in names if tool_name.startswith(name)]
    contains = [tool_name for tool_name in names if name in tool_name and tool_name not in exact_prefix]
    return (exact_prefix + contains)[:limit]


def format_tool_property(name: str, schema: dict[str, object], required: bool) -> str:
    type_name = schema.get("type")
    type_text = str(type_name) if isinstance(type_name, str) else "any"
    constraints = []
    if "minimum" in schema:
        constraints.append(f"min={schema['minimum']}")
    if "maximum" in schema:
        constraints.append(f"max={schema['maximum']}")
    if "enum" in schema and isinstance(schema["enum"], list):
        constraints.append("enum=" + "|".join(str(item) for item in schema["enum"]))
    constraint_text = f" ({', '.join(constraints)})" if constraints else ""
    marker = "required" if required else "optional"
    description = schema.get("description")
    detail = f" - {description}" if isinstance(description, str) and description.strip() else ""
    return f"    - {name}: {type_text}, {marker}{constraint_text}{detail}"


def wrap_tool_names(names: list[str], width: int = 100) -> list[str]:
    lines: list[str] = []
    current = "    "
    for name in names:
        item = name if current.strip() == "" else f", {name}"
        if len(current) + len(item) > width and current.strip():
            lines.append(current)
            current = f"    {name}"
        else:
            current += item
    if current.strip():
        lines.append(current)
    return lines


def categorize_tools() -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {
        "project": [],
        "code": [],
        "edit": [],
        "git": [],
        "command": [],
        "session": [],
        "checkpoint": [],
        "other": [],
    }
    for tool in AGENT_TOOL_DEFINITIONS:
        name = str(tool["name"])
        categories[tool_category(name)].append(name)
    return categories


def tool_category(name: str) -> str:
    if name in {
        "update_plan",
        "finish",
        "session_summary",
        "session_plan",
        "session_transcript",
        "session_search",
        "session_commands",
        "session_output_contexts",
        "session_output_diagnostics",
        "session_files",
        "session_failures",
        "session_verification",
        "run_session_verification",
        "session_audit",
        "session_handoff",
    }:
        return "session"
    if name.startswith("checkpoint_") or name.startswith("check_checkpoint_"):
        return "checkpoint"
    if name.startswith("git_") or name.startswith("check_git_"):
        return "git"
    if name in {
        "command_check",
        "check_run_commands",
        "check_suggested_checks",
        "run_focused_test_commands",
        "check_focused_test_commands",
        "run_commands",
        "run_suggested_checks",
        "run_command",
        "check_start_command",
        "start_command",
        "list_processes",
        "read_process",
        "process_output_contexts",
        "process_output_diagnostics",
        "wait_process",
        "check_write_process",
        "write_process",
        "check_stop_process",
        "stop_process",
        "check_stop_all_processes",
        "stop_all_processes",
        "port_check",
        "http_check",
        "http_fetch",
    }:
        return "command"
    if name in {
        "list_files",
        "list_tree",
        "repo_map",
        "read_file",
        "read_file_context",
        "read_file_contexts",
        "output_contexts",
        "output_diagnostics",
        "tail_file",
        "read_files",
        "read_file_ranges",
        "file_info",
        "image_info",
        "find_files",
        "glob",
        "search",
        "search_contexts",
        "code_reference_contexts",
        "python_reference_contexts",
        "tool_search",
        "project_overview",
        "project_commands",
        "related_tests",
        "focused_test_commands",
        "project_manifests",
        "project_instructions",
        "project_todos",
        "environment_info",
        "suggest_checks",
        "review_changes",
        "final_review",
    }:
        return "project"
    edit_keywords = (
        "append",
        "copy",
        "create",
        "delete",
        "edit",
        "insert",
        "json_",
        "move",
        "multi_edit",
        "patch",
        "regex_replace",
        "replace",
        "set_executable",
        "write_file",
        "write_files",
    )
    if name.startswith("check_") and any(keyword in name for keyword in edit_keywords):
        return "edit"
    if name.startswith(("json_", "python_rename", "code_rename")) or any(name.startswith(prefix) for prefix in edit_keywords):
        return "edit"
    if name.startswith(("python_", "code_", "config_check")):
        return "code"
    return "other"


def tool_requires_approval(name: str, description: str) -> bool:
    if name in APPROVAL_REQUIRED_TOOL_NAMES:
        return True
    lowered = description.lower()
    return "requires approval" in lowered or "after approval" in lowered


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
