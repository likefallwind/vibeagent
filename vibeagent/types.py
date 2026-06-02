from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Literal, Protocol, TypeAlias


ContentBlock: TypeAlias = dict[str, Any]
MessageContent: TypeAlias = str | list[ContentBlock]
ToolSpec: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: MessageContent


@dataclass(frozen=True)
class AssistantResponse:
    # Provider-neutral blocks:
    # - {"type": "text", "text": "..."}
    # - {"type": "tool_call", "id": "...", "name": "...", "input": {...}}
    content: list[ContentBlock]
    raw: dict[str, Any]


class ChatClient(Protocol):
    # Protocol so MiniMaxClient and any future providers can plug into the same agent loop.
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> AssistantResponse:
        ...


@dataclass(frozen=True)
class WriteFileAction:
    type: Literal["write_file"]
    path: str
    content: str


@dataclass(frozen=True)
class ListFilesAction:
    type: Literal["list_files"]
    path: str | None = None


@dataclass(frozen=True)
class ReadFileAction:
    type: Literal["read_file"]
    path: str


@dataclass(frozen=True)
class SearchAction:
    type: Literal["search"]
    query: str


@dataclass(frozen=True)
class EditFileAction:
    type: Literal["edit_file"]
    path: str
    old: str
    new: str


@dataclass(frozen=True)
class RunCommandAction:
    type: Literal["run_command"]
    command: str


@dataclass(frozen=True)
class FinishAction:
    type: Literal["finish"]
    message: str


# Small union of all supported model action types.
AgentAction: TypeAlias = (
    WriteFileAction | ListFilesAction | ReadFileAction | SearchAction | EditFileAction | RunCommandAction | FinishAction
)


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    signal: str | None


@dataclass(frozen=True)
class WriteFileObservation:
    kind: Literal["write_file"]
    path: str
    ok: bool
    message: str


@dataclass(frozen=True)
class RunCommandObservation:
    kind: Literal["run_command"]
    result: CommandResult


@dataclass(frozen=True)
class ListFilesObservation:
    kind: Literal["list_files"]
    path: str
    files: list[str]
    total: int
    truncated: bool
    message: str


@dataclass(frozen=True)
class ReadFileObservation:
    kind: Literal["read_file"]
    path: str
    content: str
    message: str


@dataclass(frozen=True)
class SearchObservation:
    kind: Literal["search"]
    query: str
    matches: list[str]
    message: str


@dataclass(frozen=True)
class EditFileObservation:
    kind: Literal["edit_file"]
    path: str
    ok: bool
    message: str
    diff: str


@dataclass(frozen=True)
class FinishObservation:
    kind: Literal["finish"]
    message: str


@dataclass(frozen=True)
class ToolErrorObservation:
    kind: Literal["tool_error"]
    tool: str
    message: str


# Unified envelope returned from one agent step.
Observation: TypeAlias = (
    WriteFileObservation
    | ListFilesObservation
    | ReadFileObservation
    | SearchObservation
    | EditFileObservation
    | RunCommandObservation
    | FinishObservation
    | ToolErrorObservation
)

# Status tokens are constrained to keep logger and callers consistent.
AgentStatus: TypeAlias = Literal[
    "thinking",
    "listing files",
    "reading file",
    "searching",
    "editing file",
    "writing file",
    "running command",
    "observed success",
    "observed failure",
    "finished",
]

# Logger receives a status plus optional detail for each agent transition.
AgentLogger: TypeAlias = Callable[[AgentStatus, str | None], None]
