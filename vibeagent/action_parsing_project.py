from __future__ import annotations

from typing import Any

from .action_parsing_helpers import ActionParseError, parse_optional_positive_int
from .action_parsing_project_tests import PROJECT_TEST_ACTION_TYPES, parse_project_test_action
from .tool_categories import valid_tool_categories
from .types import (
    FinalReviewAction,
    ProjectCommandsAction,
    ProjectAgentsAction,
    ProjectInstructionsAction,
    ProjectSkillsAction,
    ProjectManifestsAction,
    ProjectOverviewAction,
    ProjectTodosAction,
    ReviewChangesAction,
    SkillAction,
    ToolSearchAction,
)


PROJECT_ACTION_TYPES = PROJECT_TEST_ACTION_TYPES | {
    "review_changes",
    "final_review",
    "project_commands",
    "tool_search",
    "project_manifests",
    "project_instructions",
    "project_skills",
    "project_agents",
    "skill",
    "project_todos",
    "project_overview",
}


def parse_project_action(action_type: object, value: dict[str, Any], raw: str) -> object | None:
    if action_type not in PROJECT_ACTION_TYPES:
        return None

    test_action = parse_project_test_action(action_type, value, raw)
    if test_action is not None:
        return test_action

    if action_type == "review_changes":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        return ReviewChangesAction(type="review_changes", max_files=max_files)

    if action_type == "final_review":
        max_files = parse_optional_positive_int(value.get("max_files", 200), "max_files", raw, maximum=500) or 200
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=100) or 10
        return FinalReviewAction(type="final_review", max_files=max_files, max_checks=max_checks)

    if action_type == "project_commands":
        max_commands = parse_optional_positive_int(value.get("max_commands", 100), "max_commands", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        return ProjectCommandsAction(type="project_commands", max_commands=max_commands, max_files=max_files)

    if action_type == "tool_search":
        query = value.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ActionParseError("tool_search action query must be a non-empty string.", raw)
        max_matches = parse_optional_positive_int(value.get("max_matches", 20), "max_matches", raw, maximum=100) or 20
        category = value.get("category")
        if category is not None and not isinstance(category, str):
            raise ActionParseError("tool_search action category must be a string when provided.", raw)
        normalized_category = category.strip() if isinstance(category, str) and category.strip() else None
        if normalized_category is not None and normalized_category not in valid_tool_categories():
            valid = ", ".join(valid_tool_categories())
            raise ActionParseError(f"tool_search action category must be one of: {valid}.", raw)
        approval_required = value.get("approval_required")
        if approval_required is not None and not isinstance(approval_required, bool):
            raise ActionParseError("tool_search action approval_required must be a boolean when provided.", raw)
        return ToolSearchAction(
            type="tool_search",
            query=query.strip(),
            max_matches=max_matches,
            category=normalized_category,
            approval_required=approval_required,
        )

    if action_type == "project_manifests":
        max_files = parse_optional_positive_int(value.get("max_files", 30), "max_files", raw, maximum=200) or 30
        max_items = parse_optional_positive_int(value.get("max_items", 500), "max_items", raw, maximum=2000) or 500
        return ProjectManifestsAction(type="project_manifests", max_files=max_files, max_items=max_items)

    if action_type == "project_instructions":
        max_files = parse_optional_positive_int(value.get("max_files", 20), "max_files", raw, maximum=200) or 20
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 12_000), "max_bytes", raw, maximum=50_000) or 12_000
        if max_bytes < 200:
            raise ActionParseError("max_bytes must be at least 200.", raw)
        return ProjectInstructionsAction(type="project_instructions", max_files=max_files, max_bytes=max_bytes)

    if action_type == "project_skills":
        max_skills = parse_optional_positive_int(value.get("max_skills", 100), "max_skills", raw, maximum=500) or 100
        return ProjectSkillsAction(type="project_skills", max_skills=max_skills)

    if action_type == "project_agents":
        max_agents = parse_optional_positive_int(value.get("max_agents", 100), "max_agents", raw, maximum=500) or 100
        return ProjectAgentsAction(type="project_agents", max_agents=max_agents)

    if action_type == "skill":
        name = value.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ActionParseError("skill action requires a non-empty name.", raw)
        max_bytes = parse_optional_positive_int(value.get("max_bytes", 20_000), "max_bytes", raw, maximum=50_000) or 20_000
        if max_bytes < 200:
            raise ActionParseError("max_bytes must be at least 200.", raw)
        return SkillAction(type="skill", name=name.strip(), max_bytes=max_bytes)

    if action_type == "project_todos":
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise ActionParseError("project_todos action path must be a string when provided.", raw)
        max_items = parse_optional_positive_int(value.get("max_items", 100), "max_items", raw, maximum=500) or 100
        max_files = parse_optional_positive_int(value.get("max_files", 1000), "max_files", raw, maximum=5000) or 1000
        return ProjectTodosAction(
            type="project_todos",
            path=path.strip() if isinstance(path, str) and path.strip() else None,
            max_items=max_items,
            max_files=max_files,
        )

    if action_type == "project_overview":
        max_files = parse_optional_positive_int(value.get("max_files", 80), "max_files", raw, maximum=200) or 80
        max_commands = parse_optional_positive_int(value.get("max_commands", 20), "max_commands", raw, maximum=100) or 20
        max_checks = parse_optional_positive_int(value.get("max_checks", 10), "max_checks", raw, maximum=50) or 10
        max_manifests = parse_optional_positive_int(value.get("max_manifests", 10), "max_manifests", raw, maximum=50) or 10
        return ProjectOverviewAction(
            type="project_overview",
            max_files=max_files,
            max_commands=max_commands,
            max_checks=max_checks,
            max_manifests=max_manifests,
        )

    raise AssertionError(f"Unhandled project action type: {action_type!r}")
