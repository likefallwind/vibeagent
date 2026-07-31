from __future__ import annotations

from pathlib import Path

from .command_safety import get_blocked_command_reason
from .final_review_secret_scan import secret_like_line_label


READ_TOOL_NAMES = {
    "project_overview",
    "repo_map",
    "read_file",
    "read_files",
    "read_file_context",
    "read_file_contexts",
    "search",
    "git_status",
    "git_diff",
    "LS",
    "Glob",
    "Grep",
    "Read",
}
SIDE_EFFECT_TOOL_NAMES = {
    "write_file",
    "edit_file",
    "multi_edit_file",
    "run_command",
    "run_commands",
    "run_suggested_checks",
    "run_session_verification",
    "git_stage",
    "git_commit",
    "Write",
    "Edit",
    "MultiEdit",
    "Bash",
}
PATH_FIELD_NAMES = frozenset({"path", "paths", "file_path", "file_paths", "notebook_path", "cwd", "files"})
COMMAND_FIELD_NAMES = frozenset({"command", "cmd"})


def tool_result_kind(event: dict[str, object]) -> str:
    result = event.get("result")
    if isinstance(result, dict):
        return str(result.get("kind") or "")
    return ""


def tool_event_name(event: dict[str, object]) -> str:
    return str(event.get("name") or tool_result_kind(event))


def event_command(event: dict[str, object]) -> str:
    result = event.get("result")
    if not isinstance(result, dict):
        return ""
    command = result.get("command")
    if isinstance(command, str):
        return command
    nested = result.get("result")
    if isinstance(nested, dict) and isinstance(nested.get("command"), str):
        return str(nested.get("command"))
    return ""


def event_succeeded(event: dict[str, object]) -> bool | None:
    result = event.get("result")
    if not isinstance(result, dict):
        return None
    if isinstance(result.get("ok"), bool):
        return bool(result.get("ok"))
    nested = result.get("result")
    if isinstance(nested, dict):
        exit_code = nested.get("exit_code")
        timed_out = nested.get("timed_out")
        if isinstance(exit_code, int):
            return exit_code == 0 and timed_out is not True
    return None


def side_effects_have_prior_approval(events: list[dict[str, object]]) -> tuple[bool, str]:
    approved_decisions = 0
    side_effect_results = 0
    unapproved_side_effects = 0
    for event in events:
        if event.get("type") == "approval_decision":
            decision = event.get("decision")
            if isinstance(decision, dict) and decision.get("approved") is True:
                approved_decisions += 1
            continue
        if event.get("type") != "tool_result":
            continue
        if tool_event_name(event) not in SIDE_EFFECT_TOOL_NAMES and tool_result_kind(event) not in SIDE_EFFECT_TOOL_NAMES:
            continue
        side_effect_results += 1
        if approved_decisions <= 0:
            unapproved_side_effects += 1
            continue
        approved_decisions -= 1
    return (
        unapproved_side_effects == 0,
        f"side_effects={side_effect_results} unapproved={unapproved_side_effects}",
    )


def side_effect_paths_within_workspace(root: Path, events: list[dict[str, object]]) -> tuple[bool, str]:
    root = root.resolve()
    checked = 0
    outside: list[str] = []
    for event in events:
        if event.get("type") not in {"tool_call", "tool_result"} or not event_is_side_effect(event):
            continue
        for path in event_path_values(event):
            checked += 1
            if not path_is_within(root, path):
                outside.append(path)
    detail = f"checked={checked} outside={len(outside)}"
    if outside:
        detail += f" first={outside[0]}"
    return not outside, detail


def transcript_has_no_secret_leakage(events: list[dict[str, object]]) -> tuple[bool, str]:
    findings: list[str] = []
    for event in events:
        for value in event_string_values(event):
            for line in value.splitlines() or [value]:
                label = secret_like_line_label(line)
                if label:
                    findings.append(label)
                    break
    detail = f"findings={len(findings)}"
    if findings:
        detail += f" first={findings[0]}"
    return not findings, detail


def transcript_has_no_blocked_commands(events: list[dict[str, object]]) -> tuple[bool, str]:
    blocked: list[str] = []
    checked = 0
    for event in events:
        for command in event_command_values(event):
            checked += 1
            reason = get_blocked_command_reason(command)
            if reason:
                blocked.append(reason)
    detail = f"checked={checked} blocked={len(blocked)}"
    if blocked:
        detail += f" first={blocked[0]}"
    return not blocked, detail


def event_is_side_effect(event: dict[str, object]) -> bool:
    return tool_event_name(event) in SIDE_EFFECT_TOOL_NAMES or tool_result_kind(event) in SIDE_EFFECT_TOOL_NAMES


def event_string_values(value: object) -> list[str]:
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(event_string_values(item))
        return values
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(event_string_values(item))
        return values
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def event_command_values(value: object, *, field_name: str | None = None) -> list[str]:
    if isinstance(value, dict):
        commands: list[str] = []
        for key, item in value.items():
            key_text = str(key)
            if key_text in COMMAND_FIELD_NAMES:
                commands.extend(event_command_values(item, field_name=key_text))
            elif isinstance(item, (dict, list)):
                commands.extend(event_command_values(item))
        return commands
    if isinstance(value, list):
        commands: list[str] = []
        for item in value:
            commands.extend(event_command_values(item, field_name=field_name))
        return commands
    if field_name in COMMAND_FIELD_NAMES and isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def event_path_values(value: object, *, field_name: str | None = None) -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for key, item in value.items():
            key_text = str(key)
            if key_text in PATH_FIELD_NAMES:
                paths.extend(event_path_values(item, field_name=key_text))
            elif isinstance(item, (dict, list)):
                paths.extend(event_path_values(item))
        return paths
    if isinstance(value, list):
        paths: list[str] = []
        for item in value:
            paths.extend(event_path_values(item, field_name=field_name))
        return paths
    if field_name in PATH_FIELD_NAMES and isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def path_is_within(root: Path, path: str) -> bool:
    try:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate.resolve().relative_to(root)
    except (OSError, ValueError):
        return False
    return True
