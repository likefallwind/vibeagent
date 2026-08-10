from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


HookEvent = Literal[
    "CwdChanged",
    "InstructionsLoaded",
    "PostToolUse",
    "PostToolUseFailure",
    "PreToolUse",
    "SessionStart",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "UserPromptSubmit",
]
HOOK_EVENTS = frozenset(
    {
        "CwdChanged",
        "InstructionsLoaded",
        "PostToolUse",
        "PostToolUseFailure",
        "PreToolUse",
        "SessionStart",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "UserPromptSubmit",
    }
)
SEQUENTIAL_TOOL_HOOK_EVENTS = frozenset(
    {"CwdChanged", "InstructionsLoaded", "PostToolUse", "PostToolUseFailure", "PreToolUse"}
)


@dataclass(frozen=True)
class ProjectHook:
    event: HookEvent
    matcher: str
    command: str
    timeout_ms: int
    source: str
    handler_type: Literal["command", "http"] = "command"
    url: str = ""
    headers: tuple[tuple[str, str], ...] = ()
    allowed_env_vars: tuple[str, ...] = ()
    environment: dict[str, str] = field(default_factory=dict)
    async_: bool = False
    async_rewake: bool = False

    @property
    def handler_target(self) -> str:
        return self.command if self.handler_type == "command" else self.url


@dataclass(frozen=True)
class ProjectHooks:
    hooks: tuple[ProjectHook, ...] = ()
    sources: tuple[str, ...] = ()
    error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.hooks) or self.error is not None

    @property
    def requires_sequential_tools(self) -> bool:
        return self.error is not None or any(
            hook.event in SEQUENTIAL_TOOL_HOOK_EVENTS for hook in self.hooks
        )


__all__ = ["HOOK_EVENTS", "HookEvent", "ProjectHook", "ProjectHooks"]
