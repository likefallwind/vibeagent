from __future__ import annotations

from .tool_categories import TOOL_CATEGORIES, valid_tool_categories
from .tool_catalog_core import (
    APPROVAL_REQUIRED_TOOL_NAMES,
    categorize_tools,
    suggest_tool_names,
    tool_category,
    tool_requires_approval,
)
from .tool_catalog_search import format_tool_search_report_text, get_tool_search_report, get_tool_search_text
from .tool_definitions import AGENT_TOOL_DEFINITIONS


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
