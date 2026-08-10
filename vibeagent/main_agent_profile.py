from __future__ import annotations

from dataclasses import dataclass, replace

from .action_tool_aliases import tool_name_candidates, tool_name_is_restricted
from .agent_delegate_policy import (
    DELEGATE_TOOL_NAMES,
    NESTED_DELEGATE_TOOL_NAMES,
    READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES,
)
from .agent_delegate_profile import load_delegate_profile_runtime
from .types import DelegateTaskAction
from .workspace_agents import read_project_agents
from .workspace_core import RunWorkspace


MAIN_EXPLORE_CONTROL_TOOLS = frozenset(
    {
        "AskUserQuestion",
        "ListAgents",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskUpdate",
        "ask_user",
        "finish",
        "update_plan",
    }
)
MAIN_EXPLORE_TOOL_NAMES = (
    DELEGATE_TOOL_NAMES
    | NESTED_DELEGATE_TOOL_NAMES
    | READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES
    | MAIN_EXPLORE_CONTROL_TOOLS
)


@dataclass(frozen=True)
class MainAgentProfile:
    name: str | None = None
    source: str | None = None
    prompt: str | None = None
    mode: str = "code"
    model: str | None = None
    effort: str | None = None
    allowed_tool_names: frozenset[str] | None = None
    disallowed_tool_names: frozenset[str] = frozenset()
    max_turns: int | None = None
    skills: tuple[str, ...] = ()
    memory_scope: str | None = None
    workspace: RunWorkspace | None = None

    @property
    def enabled(self) -> bool:
        return self.name is not None

    def allows_tool_call(self, tool_name: str, action: object | None = None) -> bool:
        candidates = frozenset(tool_name_candidates(tool_name, action))
        if any(tool_name_is_restricted(self.disallowed_tool_names, candidate) for candidate in candidates):
            return False
        return self.allowed_tool_names is None or bool(candidates & self.allowed_tool_names)


def load_main_agent_profile(
    workspace: RunWorkspace,
    name: str | None,
    *,
    source: str | None = None,
) -> MainAgentProfile:
    if name is None:
        return MainAgentProfile()
    selected = name.strip()
    if not selected:
        raise ValueError("Main agent profile name must not be empty.")
    selected = _resolve_profile_reference(workspace, selected)
    loaded = load_delegate_profile_runtime(
        workspace,
        DelegateTaskAction(
            type="delegate_task",
            task="Load main agent profile",
            agent=selected,
            mode="code",
        ),
        include_memory_content=False,
    )
    if loaded.error is not None:
        raise ValueError(f"Main agent profile could not be loaded: {loaded.error}")
    if loaded.isolation is not None:
        raise ValueError(
            "Main agent profiles cannot require isolation; use the CLI --worktree option for the whole session."
        )
    allowed = loaded.allowed_tool_names
    if loaded.mode == "explore":
        allowed = (
            MAIN_EXPLORE_TOOL_NAMES
            if allowed is None
            else allowed & MAIN_EXPLORE_TOOL_NAMES
        )
    return MainAgentProfile(
        name=selected,
        source=source,
        prompt=loaded.prompt,
        mode=loaded.mode or "code",
        model=loaded.model,
        effort=loaded.effort,
        allowed_tool_names=allowed,
        disallowed_tool_names=loaded.disallowed_tool_names,
        max_turns=loaded.max_turns,
        skills=loaded.skills,
        memory_scope=loaded.memory_scope,
        workspace=loaded.workspace,
    )


def _resolve_profile_reference(workspace: RunWorkspace, name: str) -> str:
    catalog = read_project_agents(workspace, max_agents=500)
    profiles = catalog["agents"]
    if any(str(profile["name"]) == name for profile in profiles):
        return name
    if ":" in name:
        return name
    matches = sorted(
        str(profile["name"])
        for profile in profiles
        if str(profile["name"]).endswith(f":{name}")
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"Main agent profile name {name!r} is ambiguous: {', '.join(matches)}."
        )
    return name


def append_main_profile_prompt(
    append_system_prompt: str | None, profile: MainAgentProfile
) -> str | None:
    sections = []
    if profile.prompt:
        sections.append(
            f"Selected main agent profile {profile.name!r} instructions:\n{profile.prompt}"
        )
    if append_system_prompt and append_system_prompt.strip():
        sections.append(append_system_prompt.strip())
    return "\n\n".join(sections) or None


def apply_tool_ceiling(
    profile: MainAgentProfile,
    tool_names: frozenset[str] | None,
    disallowed_tool_names: frozenset[str] = frozenset(),
) -> MainAgentProfile:
    if tool_names is None and not disallowed_tool_names:
        return profile
    if tool_names is None:
        allowed = profile.allowed_tool_names
    elif profile.allowed_tool_names is None:
        allowed = tool_names
    else:
        allowed = profile.allowed_tool_names & tool_names
    return replace(
        profile,
        allowed_tool_names=allowed,
        disallowed_tool_names=profile.disallowed_tool_names | disallowed_tool_names,
    )


__all__ = [
    "MainAgentProfile",
    "apply_tool_ceiling",
    "append_main_profile_prompt",
    "load_main_agent_profile",
]
