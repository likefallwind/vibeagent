from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .background_agent_runtime import launch_background_agent
from .background_agent_store import write_private_text_atomic
from .background_agent_types import BackgroundAgentView
from .dynamic_agent_profiles import DynamicAgentProfile
from .session_names import read_session_name
from .types import ApprovalPolicy


DEFAULT_BACKGROUND_PROMPT = (
    "Continue the current task autonomously from the recorded session context."
)


@dataclass(frozen=True)
class InteractiveBackgroundRequest(Exception):
    project_root: Path
    run_id: str
    prompt: str
    argv: tuple[str, ...]
    attached_agent_id: str | None = None


def create_interactive_background_request(
    project_root: Path,
    run_id: str,
    prompt: str | None,
    *,
    approval_policy: ApprovalPolicy,
    model: str | None,
    agent: str | None,
    dynamic_agent_profiles: tuple[DynamicAgentProfile, ...],
    effort: str | None,
    autocompact_tokens: int | None,
    system_prompt: str | None,
    append_system_prompt: str | None,
    additional_directories: tuple[Path, ...],
    safe_mode: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    attached_agent_id: str | None = None,
) -> InteractiveBackgroundRequest:
    task = prompt.strip() if prompt and prompt.strip() else DEFAULT_BACKGROUND_PROMPT
    argv = ["--background", "--resume", run_id, "--approval", approval_policy]
    _append_option(argv, "--model-name", model)
    _append_option(argv, "--agent", agent)
    if dynamic_agent_profiles:
        argv.extend(["--agents", serialize_dynamic_agent_profiles(dynamic_agent_profiles)])
    _append_option(argv, "--effort", effort)
    if autocompact_tokens is not None:
        argv.extend(["--autocompact", str(autocompact_tokens)])
    _append_option(argv, "--system-prompt", system_prompt)
    _append_option(argv, "--append-system-prompt", append_system_prompt)
    for path in additional_directories:
        argv.extend(["--add-dir", path.resolve().as_posix()])
    if safe_mode:
        argv.append("--safe-mode")
    if setting_sources != ("user", "project", "local"):
        argv.extend(["--setting-sources", ",".join(setting_sources)])
    if settings_override_json is not None:
        settings_path = project_root / ".vibeagent" / "sessions" / run_id / "invocation-settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        write_private_text_atomic(settings_path, settings_override_json + "\n")
        argv.extend(["--settings", settings_path.as_posix()])
    argv.extend(["--", task])
    return InteractiveBackgroundRequest(
        project_root=project_root.resolve(),
        run_id=run_id,
        prompt=task,
        argv=tuple(argv),
        attached_agent_id=attached_agent_id,
    )


def launch_interactive_background_request(
    request: InteractiveBackgroundRequest,
    *,
    invocation_root: Path,
) -> BackgroundAgentView:
    return launch_background_agent(
        request.project_root,
        invocation_root,
        list(request.argv),
        task_summary=request.prompt,
        session_name=read_session_name(request.project_root, request.run_id),
        resume_reference=request.run_id,
    )


def serialize_dynamic_agent_profiles(
    profiles: tuple[DynamicAgentProfile, ...],
) -> str:
    payload: dict[str, dict[str, object]] = {}
    for profile in profiles:
        definition: dict[str, object] = {
            "description": profile.description,
            "prompt": profile.prompt,
            "mode": profile.mode,
        }
        optional = {
            "model": profile.model,
            "effort": profile.effort,
            "tools": list(profile.tools) if profile.tools is not None else None,
            "maxTurns": profile.max_turns,
            "memory": profile.memory,
            "isolation": profile.isolation,
            "permissionMode": profile.permission_mode,
            "hooks": profile.hooks,
            "initialPrompt": profile.initial_prompt,
            "color": profile.color,
        }
        definition.update({key: value for key, value in optional.items() if value is not None})
        if profile.disallowed_tools:
            definition["disallowedTools"] = list(profile.disallowed_tools)
        if profile.skills:
            definition["skills"] = list(profile.skills)
        if profile.mcp_servers:
            definition["mcpServers"] = list(profile.mcp_servers)
        if profile.background:
            definition["background"] = True
        payload[profile.name] = definition
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def format_interactive_background_started(view: BackgroundAgentView) -> str:
    record = view.record
    return "\n".join(
        [
            f"Session moved to background agent {record.id}.",
            f"  session: {record.session_name or '.'}",
            f"  logs: vibeagent --background-agent-log {record.id}",
            "  attach: vibeagent agents",
        ]
    )


def _append_option(argv: list[str], option: str, value: str | None) -> None:
    if value is not None:
        argv.extend([option, value])


__all__ = [
    "DEFAULT_BACKGROUND_PROMPT",
    "InteractiveBackgroundRequest",
    "create_interactive_background_request",
    "format_interactive_background_started",
    "launch_interactive_background_request",
    "serialize_dynamic_agent_profiles",
]
