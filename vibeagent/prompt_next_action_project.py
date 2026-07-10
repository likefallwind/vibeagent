from __future__ import annotations

from .types import Observation


PROJECT_NEXT_ACTION_KINDS = {
    "delegate_task",
    "suggest_checks",
    "check_suggested_checks",
    "project_commands",
    "tool_search",
    "related_tests",
    "focused_test_commands",
    "check_focused_test_commands",
    "project_manifests",
    "project_instructions",
    "project_todos",
    "project_overview",
    "environment_info",
}


def _command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", ".") or ".").strip() or "."
        if command:
            labels.append(f"{command} (cwd={cwd})")
    return labels


def _available_command_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if not getattr(value, "available", True):
            continue
        command = str(getattr(value, "command", "") or "").strip()
        cwd = str(getattr(value, "cwd", ".") or ".").strip() or "."
        if command:
            labels.append(f"{command} (cwd={cwd})")
    return labels


def _blocked_check_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        if getattr(value, "ok", False):
            continue
        command = str(getattr(value, "command", "") or "").strip()
        reason = str(getattr(value, "block_reason", "") or getattr(value, "missing_tool", "") or getattr(value, "message", "") or "").strip()
        if command and reason:
            labels.append(f"{command}: {reason}")
        elif command:
            labels.append(command)
        elif reason:
            labels.append(reason)
    return labels


def _format_next_action_items(items: list[str], max_items: int = 3) -> str:
    shown = items[:max_items]
    suffix = "" if len(items) <= max_items else f"; +{len(items) - max_items} more"
    return "; ".join(shown) + suffix


def _tool_names(matches: object) -> list[str]:
    names: list[str] = []
    if not isinstance(matches, list):
        return names
    for match in matches:
        if not isinstance(match, dict):
            continue
        name = str(match.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def _manifest_paths(values: object) -> list[str]:
    paths: list[str] = []
    if not isinstance(values, list):
        return paths
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        if path:
            paths.append(path)
    return paths


def _instruction_paths(values: object) -> list[str]:
    paths: list[str] = []
    if not isinstance(values, list):
        return paths
    for value in values:
        if not getattr(value, "included", False):
            continue
        path = str(getattr(value, "path", "") or "").strip()
        if path:
            paths.append(path)
    return paths


def _todo_labels(values: object) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for value in values:
        path = str(getattr(value, "path", "") or "").strip()
        line = getattr(value, "line", None)
        marker = str(getattr(value, "marker", "") or "").strip()
        text = str(getattr(value, "text", "") or "").strip()
        location = f"{path}:{line}" if path and isinstance(line, int) else path
        label = location
        if marker:
            label = f"{label} [{marker}]" if label else f"[{marker}]"
        if text:
            label = f"{label} {text}" if label else text
        if label:
            labels.append(label)
    return labels


def _unavailable_tool_names(values: object) -> list[str]:
    names: list[str] = []
    if not isinstance(values, list):
        return names
    for value in values:
        if getattr(value, "available", False):
            continue
        name = str(getattr(value, "name", "") or "").strip()
        if name:
            names.append(name)
    return names


def _tool_search_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Tool search failed. Use the known tool catalog or choose the next concrete action manually."

    names = _tool_names(getattr(latest, "matches", []))
    if names:
        return (
            f"{base} Tool search found matching tool(s): {_format_next_action_items(names)}. "
            "Use the most specific matching tool if it advances the current task; otherwise continue with the known workflow."
        )

    suggestions = [str(item).strip() for item in getattr(latest, "suggestions", []) if str(item).strip()]
    if suggestions:
        return (
            f"{base} Tool search found no direct matches. Consider suggested tool names: {_format_next_action_items(suggestions)}."
        )
    return f"{base} Tool search found no matches. Choose from the currently known tools or continue manually."


def _suggest_checks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Suggested checks could not be collected. Use project_commands or focused_test_commands to find runnable checks, "
            "or continue with a known verification command."
        )

    available = _available_command_labels(getattr(latest, "checks", []))
    if available:
        return (
            f"{base} Suggested checks are available. Run run_suggested_checks or run_command for: "
            f"{_format_next_action_items(available)}. Fix failures before finishing."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Suggested checks were found but are not directly available. "
            "Inspect missing tools, use project_commands for alternatives, or run an equivalent check manually."
        )

    return (
        f"{base} No suggested checks were found. Use project_commands, related_tests, or focused_test_commands to find a verification path."
    )


def _check_suggested_checks_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        blockers = _blocked_check_labels(getattr(latest, "checks", []))
        if blockers:
            return (
                f"{base} Suggested check dry-run found blocked command(s): {_format_next_action_items(blockers)}. "
                "Fix the command context or choose another verification path before running checks."
            )
        return f"{base} Suggested check dry-run failed. Inspect the message, then choose another verification path."

    runnable = _command_labels(getattr(latest, "suggested_checks", []))
    if runnable:
        return (
            f"{base} Suggested check dry-run passed. Run run_suggested_checks or run_command for: "
            f"{_format_next_action_items(runnable)}."
        )
    return f"{base} Suggested check dry-run passed but no commands were listed. Continue with the next required check or answer directly."


def _project_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Project commands could not be collected. Inspect project_manifests or run a known check command if available."
        )

    available = _available_command_labels(getattr(latest, "commands", []))
    if available:
        return (
            f"{base} Project commands were found. Choose the relevant command and use command_check or run_command: "
            f"{_format_next_action_items(available)}."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Project command hints exist but are not directly runnable. Inspect missing tools or project_manifests, "
            "then choose an equivalent verification command."
        )
    return f"{base} No project commands were found. Use related_tests, focused_test_commands, or a known repository check."


def _related_tests_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Related tests could not be identified. Use project_commands or suggest_checks to choose verification."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Related tests were found. Use focused_test_commands to build runnable focused checks, "
            "or run the listed tests manually before broader verification."
        )
    return f"{base} No related tests were found. Use suggest_checks or project_commands for broader verification."


def _focused_test_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return (
            f"{base} Focused test commands could not be collected. Use related_tests, suggest_checks, or project_commands for verification."
        )

    available = _available_command_labels(getattr(latest, "commands", []))
    if available:
        return (
            f"{base} Focused test commands are available. Run run_focused_test_commands or run_command for: "
            f"{_format_next_action_items(available)}. Then run broader checks if the change needs them."
        )

    total = int(getattr(latest, "total", 0) or 0)
    if total > 0:
        return (
            f"{base} Focused test commands were found but are not directly available. "
            "Inspect missing tools, use related_tests for paths, or choose another verification command."
        )
    return f"{base} No focused test commands were found. Use suggest_checks or project_commands for verification."


def _check_focused_test_commands_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        blockers = _blocked_check_labels(getattr(latest, "checks", []))
        if blockers:
            return (
                f"{base} Focused test dry-run found blocked command(s): {_format_next_action_items(blockers)}. "
                "Fix the command context or choose another focused check before running tests."
            )
        return f"{base} Focused test dry-run failed. Inspect the message, then choose another verification path."

    runnable = _command_labels(getattr(latest, "focused_commands", []))
    if runnable:
        return (
            f"{base} Focused test dry-run passed. Run run_focused_test_commands or run_command for: "
            f"{_format_next_action_items(runnable)}."
        )
    return f"{base} Focused test dry-run passed but no commands were listed. Continue with the next required check or answer directly."


def _project_manifests_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project manifests could not be read. Continue with project_commands or known repository conventions."

    paths = _manifest_paths(getattr(latest, "manifests", []))
    if paths:
        return (
            f"{base} Project manifests were found: {_format_next_action_items(paths)}. "
            "Use project_commands or suggest_checks to turn manifest metadata into runnable verification steps."
        )
    return f"{base} No project manifests were found. Use project_instructions, project_commands, or direct file inspection to understand the repo."


def _project_instructions_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project instructions could not be read. Continue carefully with local code conventions and targeted inspection."

    paths = _instruction_paths(getattr(latest, "files", []))
    if paths:
        return (
            f"{base} Project instructions were read from: {_format_next_action_items(paths)}. "
            "Follow those instructions for subsequent edits, then continue with the next concrete task step."
        )

    if str(getattr(latest, "text", "") or "").strip():
        return f"{base} Project instructions text is available. Follow it for subsequent edits, then continue with the task."
    return f"{base} No project instructions were found. Continue using local code patterns and targeted inspection."


def _project_todos_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project TODO search failed. Narrow the path or continue with direct code inspection."

    todos = _todo_labels(getattr(latest, "todos", []))
    if todos:
        return (
            f"{base} Project TODOs were found: {_format_next_action_items(todos)}. "
            "Inspect the relevant files before editing, or ignore them if they are unrelated to the current task."
        )
    return f"{base} No project TODOs were found. Continue with the current implementation or verification path."


def _project_overview_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Project overview could not be read. Use targeted inspection such as list_files, project_commands, or git_status."

    commands = _available_command_labels(getattr(latest, "commands", []))
    checks = _available_command_labels(getattr(latest, "suggested_checks", []))
    instructions = _instruction_paths(getattr(latest, "instruction_sources", []))
    todos = _todo_labels(getattr(latest, "todos", []))
    instruction_detail = (
        f" Project instructions are present in {_format_next_action_items(instructions)}; use project_instructions before editing if their content is needed."
        if instructions
        else ""
    )
    todo_detail = (
        f" Project TODO markers are present: {_format_next_action_items(todos)}; inspect them if they are relevant to the task."
        if todos
        else ""
    )
    if commands or checks:
        return (
            f"{base} Project overview found runnable project context. "
            f"Use project_commands or suggest_checks for: {_format_next_action_items(commands + checks)}."
            f"{instruction_detail}"
            f"{todo_detail}"
        )

    if str(getattr(latest, "git_status", "") or "").strip():
        return (
            f"{base} Project overview shows existing git changes. Inspect git_diff or review_changes before editing, "
            f"then continue with the requested task.{instruction_detail}"
            f"{todo_detail}"
        )
    return f"{base} Project overview is available. Use the tree, manifests, files, instruction sources, and TODO markers to choose the next targeted inspection or edit.{instruction_detail}{todo_detail}"


def _environment_info_next_action_instruction(base: str, latest: Observation) -> str:
    if not getattr(latest, "ok", False):
        return f"{base} Environment info could not be read. Continue with commands that are already known to work."

    unavailable = _unavailable_tool_names(getattr(latest, "tools", []))
    if unavailable:
        return (
            f"{base} Environment info reports unavailable tool(s): {_format_next_action_items(unavailable)}. "
            "Choose commands that use available tools or inspect project_commands for alternatives."
        )
    return f"{base} Environment info is available. Use it to choose compatible commands, then continue with implementation or verification."


def project_next_action_instruction(base: str, latest: Observation) -> str:
    if latest.kind == "delegate_task":
        if not getattr(latest, "ok", False):
            return (
                f"{base} The delegated investigation failed. Continue the necessary inspection in the main agent context "
                "or retry once with a narrower task; do not repeat the same delegation unchanged."
            )
        return (
            f"{base} Use the delegated findings as evidence, verify critical details with focused reads when needed, "
            "then continue implementation or answer if the task is complete."
        )
    if latest.kind == "suggest_checks":
        return _suggest_checks_next_action_instruction(base, latest)
    if latest.kind == "check_suggested_checks":
        return _check_suggested_checks_next_action_instruction(base, latest)
    if latest.kind == "project_commands":
        return _project_commands_next_action_instruction(base, latest)
    if latest.kind == "tool_search":
        return _tool_search_next_action_instruction(base, latest)
    if latest.kind == "related_tests":
        return _related_tests_next_action_instruction(base, latest)
    if latest.kind == "focused_test_commands":
        return _focused_test_commands_next_action_instruction(base, latest)
    if latest.kind == "check_focused_test_commands":
        return _check_focused_test_commands_next_action_instruction(base, latest)
    if latest.kind == "project_manifests":
        return _project_manifests_next_action_instruction(base, latest)
    if latest.kind == "project_instructions":
        return _project_instructions_next_action_instruction(base, latest)
    if latest.kind == "project_todos":
        return _project_todos_next_action_instruction(base, latest)
    if latest.kind == "project_overview":
        return _project_overview_next_action_instruction(base, latest)
    if latest.kind == "environment_info":
        return _environment_info_next_action_instruction(base, latest)

    raise ValueError(f"Unsupported project next-action kind: {latest.kind}")
