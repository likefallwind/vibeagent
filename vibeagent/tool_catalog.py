from __future__ import annotations

from .tool_categories import TOOL_CATEGORIES, valid_tool_categories
from .tool_catalog_core import (
    APPROVAL_REQUIRED_TOOL_NAMES,
    categorize_tools,
    suggest_tool_names,
    tool_category,
    tool_requires_approval,
)
from .tool_catalog_reports import (
    TOOL_USAGE,
    format_tool_property,
    format_tool_report_text,
    format_tools_report_text,
    get_tool_report,
    get_tool_text,
    get_tools_report,
    get_tools_text,
    wrap_tool_names,
)
from .tool_catalog_search import format_tool_search_report_text, get_tool_search_report, get_tool_search_text
from .tool_definitions import AGENT_TOOL_DEFINITIONS

def get_permissions_report(approval_policy: str = "ask", root: str = ".") -> dict[str, object]:
    from .project_trust import get_project_trust_report
    from .workflow_commands import get_command_hard_block_report
    from .workspace_permissions import PERMISSION_EFFECTS, read_project_permissions_from_root

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
    project_permissions = read_project_permissions_from_root(root)
    project_trust = get_project_trust_report(root)
    rules_by_effect = {
        effect: [
            {"rule": rule.raw, "source": rule.source}
            for rule in project_permissions.rules
            if rule.effect == effect
        ]
        for effect in PERMISSION_EFFECTS
    }
    return {
        "approvalPolicy": approval_policy,
        "planMode": approval_policy == "plan",
        "approvalRequiredTools": {
            "count": len(approval_required),
            "tools": approval_required,
            "byCategory": categories,
        },
        "readOnlyTools": {
            "count": len(read_only),
            "tools": read_only,
        },
        "projectPermissions": {
            "enabled": project_permissions.enabled,
            "allowRulesRequireExplicitTrust": True,
            "persistentlyTrusted": project_trust["trusted"],
            "trustStorePath": project_trust["storePath"],
            "trustStoreError": project_trust["storeError"],
            "count": len(project_permissions.rules),
            "sources": list(project_permissions.sources),
            "error": project_permissions.error,
            "byEffect": rules_by_effect,
        },
        "commandHardBlocks": get_command_hard_block_report(),
    }


def get_permissions_text(approval_policy: str = "ask", root: str = ".") -> str:
    return format_permissions_report_text(get_permissions_report(approval_policy, root))


def format_permissions_report_text(report: dict[str, object]) -> str:
    approval_required = report.get("approvalRequiredTools") if isinstance(report.get("approvalRequiredTools"), dict) else {}
    read_only = report.get("readOnlyTools") if isinstance(report.get("readOnlyTools"), dict) else {}
    categories = approval_required.get("byCategory") if isinstance(approval_required.get("byCategory"), dict) else {}
    lines = [
        "Permissions:",
        f"  approvalPolicy: {report.get('approvalPolicy') or 'ask'}",
        f"  planMode: {'read-only tools only' if report.get('planMode') else 'off'}",
        f"  approvalRequiredTools: {int(approval_required.get('count', 0) or 0)}",
        f"  readOnlyTools: {int(read_only.get('count', 0) or 0)}",
        "  approvalRequiredByCategory:",
    ]
    category_items = categories.items() if isinstance(categories, dict) else []
    for category, names in category_items:
        if names:
            lines.append(f"    {category}: {len(names)}")
            lines.extend(f"      {line.strip()}" for line in wrap_tool_names(names, width=96))

    project_permissions = report.get("projectPermissions")
    if isinstance(project_permissions, dict):
        sources = project_permissions.get("sources")
        clean_sources = [str(source) for source in sources] if isinstance(sources, list) else []
        lines.extend(
            [
                "  projectPermissions:",
                f"    rules: {int(project_permissions.get('count', 0) or 0)}",
                f"    sources: {', '.join(clean_sources) or '(none)'}",
                "    allowRules: require one-shot or persistent project trust to skip side-effect approval",
                f"    persistentlyTrusted: {'yes' if project_permissions.get('persistentlyTrusted') else 'no'}",
            ]
        )
        error = project_permissions.get("error")
        if isinstance(error, str) and error:
            lines.append(f"    error: {error}")
        by_effect = project_permissions.get("byEffect")
        if isinstance(by_effect, dict):
            for effect in ("deny", "ask", "allow"):
                rules = by_effect.get(effect)
                if not isinstance(rules, list):
                    continue
                for item in rules:
                    if isinstance(item, dict):
                        lines.append(f"    - {effect}: {item.get('rule')} ({item.get('source')})")

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
