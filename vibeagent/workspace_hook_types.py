from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


HookEvent = Literal[
    "ConfigChange",
    "CwdChanged",
    "DirectoryAdded",
    "Elicitation",
    "ElicitationResult",
    "FileChanged",
    "InstructionsLoaded",
    "MessageDisplay",
    "Notification",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "PreToolUse",
    "PermissionRequest",
    "PostCompact",
    "PreCompact",
    "SessionStart",
    "SessionEnd",
    "StopFailure",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "TaskCompleted",
    "TaskCreated",
    "TeammateIdle",
    "UserPromptExpansion",
    "UserPromptSubmit",
    "WorktreeCreate",
    "WorktreeRemove",
]
HOOK_EVENTS = frozenset(
    {
        "CwdChanged",
        "ConfigChange",
        "DirectoryAdded",
        "Elicitation",
        "ElicitationResult",
        "FileChanged",
        "InstructionsLoaded",
        "MessageDisplay",
        "Notification",
        "PostToolUse",
        "PostToolUseFailure",
        "PostToolBatch",
        "PreToolUse",
        "PermissionRequest",
        "PostCompact",
        "PreCompact",
        "SessionStart",
        "SessionEnd",
        "StopFailure",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "TaskCompleted",
        "TaskCreated",
        "TeammateIdle",
        "UserPromptExpansion",
        "UserPromptSubmit",
        "WorktreeCreate",
        "WorktreeRemove",
    }
)
SEQUENTIAL_TOOL_HOOK_EVENTS = frozenset(
    {
        "CwdChanged",
        "InstructionsLoaded",
        "PermissionRequest",
        "PostCompact",
        "PreCompact",
        "PostToolUse",
        "PostToolUseFailure",
        "PreToolUse",
        "TaskCompleted",
        "TaskCreated",
    }
)
PROMPT_HOOK_EVENTS = frozenset(
    {
        "PostToolUse",
        "PostToolUseFailure",
        "PostToolBatch",
        "PreToolUse",
        "PermissionRequest",
        "Stop",
        "SubagentStop",
        "TaskCompleted",
        "TaskCreated",
        "TeammateIdle",
        "UserPromptExpansion",
        "UserPromptSubmit",
    }
)


@dataclass(frozen=True)
class ProjectHook:
    event: HookEvent
    matcher: str
    command: str
    timeout_ms: int
    source: str
    handler_type: Literal["command", "http", "mcp_tool", "prompt", "agent"] = "command"
    url: str = ""
    headers: tuple[tuple[str, str], ...] = ()
    allowed_env_vars: tuple[str, ...] = ()
    mcp_server: str = ""
    mcp_tool: str = ""
    mcp_input: dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    model: str | None = None
    continue_on_block: bool = False
    environment: dict[str, str] = field(default_factory=dict)
    async_: bool = False
    async_rewake: bool = False

    @property
    def handler_target(self) -> str:
        if self.handler_type == "command":
            return self.command
        if self.handler_type == "http":
            return self.url
        if self.handler_type == "mcp_tool":
            return f"{self.mcp_server}/{self.mcp_tool}"
        return self.prompt


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


__all__ = [
    "HOOK_EVENTS",
    "PROMPT_HOOK_EVENTS",
    "HookEvent",
    "ProjectHook",
    "ProjectHooks",
]
