from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeAlias


ContentBlock: TypeAlias = dict[str, Any]


MessageContent: TypeAlias = str | list[ContentBlock]


ToolSpec: TypeAlias = dict[str, Any]


TaskStatus: TypeAlias = Literal["pending", "running", "completed", "failed", "denied"]


ApprovalPolicy: TypeAlias = Literal["ask", "allow", "deny"]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: MessageContent


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cache_creation_tokens: int | None = None
    cache_read_tokens: int | None = None


@dataclass(frozen=True)
class AssistantResponse:
    # Provider-neutral blocks:
    # - {"type": "text", "text": "..."}
    # - {"type": "tool_call", "id": "...", "name": "...", "input": {...}}
    content: list[ContentBlock]
    raw: dict[str, Any]
    usage: ModelUsage | None = None


class ChatClient(Protocol):
    # Protocol so MiniMaxClient and any future providers can plug into the same agent loop.
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_ms: int = 120_000,
    ) -> AssistantResponse:
        ...


@dataclass
class TaskStep:
    id: int
    label: str
    action_type: str
    target: str
    status: TaskStatus = "pending"
    message: str | None = None


@dataclass(frozen=True)
class ApprovalRequest:
    action_type: Literal[
        "write_file",
        "write_files",
        "edit_file",
        "multi_edit_file",
        "replace_lines",
        "insert_lines",
        "append_file",
        "regex_replace",
        "json_set",
        "json_remove",
        "json_patch",
        "patch_file",
        "patch_files",
        "delete_file",
        "delete_files",
        "move_file",
        "move_files",
        "copy_file",
        "copy_files",
        "move_dir",
        "move_dirs",
        "copy_dir",
        "copy_dirs",
        "create_dir",
        "create_dirs",
        "delete_empty_dir",
        "delete_empty_dirs",
        "set_executable",
        "git_stage",
        "git_unstage",
        "git_commit",
        "git_fetch",
        "git_pull",
        "git_push",
        "git_restore",
        "git_stash",
        "git_stash_apply",
        "git_stash_drop",
        "run_command",
        "run_commands",
        "run_suggested_checks",
        "start_command",
    ]
    target: str
    risk: str
    preview: str | None = None


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    message: str = ""


ApprovalHandler: TypeAlias = Callable[[ApprovalRequest], ApprovalDecision]
