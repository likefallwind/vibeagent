from __future__ import annotations

from dataclasses import dataclass

from .action_tool_aliases import tool_name_candidates
from .agent_delegate_policy import (
    DELEGATE_TOOL_NAMES,
    NESTED_DELEGATE_TOOL_NAMES,
    READ_ONLY_CLAUDE_DELEGATE_TOOL_NAMES,
)
from .agent_delegate_profile import load_delegate_profile_runtime
from .types import DelegateTaskAction
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
    prompt: str | None = None
    mode: str = "code"
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
        if candidates & self.disallowed_tool_names:
            return False
        return self.allowed_tool_names is None or bool(candidates & self.allowed_tool_names)


def load_main_agent_profile(
    workspace: RunWorkspace, name: str | None
) -> MainAgentProfile:
    if name is None:
        return MainAgentProfile()
    selected = name.strip()
    if not selected:
        raise ValueError("Main agent profile name must not be empty.")
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
        allowed = MAIN_EXPLORE_TOOL_NAMES if allowed is None else allowed & MAIN_EXPLORE_TOOL_NAMES
    return MainAgentProfile(
        name=selected,
        prompt=loaded.prompt,
        mode=loaded.mode or "code",
        allowed_tool_names=allowed,
        disallowed_tool_names=loaded.disallowed_tool_names,
        max_turns=loaded.max_turns,
        skills=loaded.skills,
        memory_scope=loaded.memory_scope,
        workspace=loaded.workspace,
    )


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


__all__ = [
    "MainAgentProfile",
    "append_main_profile_prompt",
    "load_main_agent_profile",
]
