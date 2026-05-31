from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Literal, Protocol, TypeAlias


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class ChatClient(Protocol):
    # Protocol so MiniMaxClient and any future providers can plug into the same agent loop.
    def complete(self, messages: list[ChatMessage]) -> str:
        ...


@dataclass(frozen=True)
class WriteFileAction:
    type: Literal["write_file"]
    path: str
    content: str


@dataclass(frozen=True)
class RunCommandAction:
    type: Literal["run_command"]
    command: str


@dataclass(frozen=True)
class FinishAction:
    type: Literal["finish"]
    message: str


# Small union of all supported model action types.
AgentAction: TypeAlias = WriteFileAction | RunCommandAction | FinishAction


@dataclass(frozen=True)
class ModelActionResponse:
    thought: str
    action: AgentAction


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
    ok: Literal[True]
    message: str


@dataclass(frozen=True)
class RunCommandObservation:
    kind: Literal["run_command"]
    result: CommandResult


@dataclass(frozen=True)
class FinishObservation:
    kind: Literal["finish"]
    message: str


# Unified envelope returned from one agent step.
Observation: TypeAlias = WriteFileObservation | RunCommandObservation | FinishObservation

# Status tokens are constrained to keep logger and callers consistent.
AgentStatus: TypeAlias = Literal[
    "thinking",
    "writing file",
    "running command",
    "observed success",
    "observed failure",
    "finished",
]

# Logger receives a status plus optional detail for each agent transition.
AgentLogger: TypeAlias = Callable[[AgentStatus, str | None], None]
