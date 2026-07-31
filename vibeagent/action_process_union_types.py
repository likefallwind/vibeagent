from __future__ import annotations

from typing import TypeAlias

from .action_process_types import (
    CheckRunCommandsAction,
    CheckStartCommandAction,
    CheckStopAllProcessesAction,
    CheckStopProcessAction,
    CheckWriteProcessAction,
    CommandCheckAction,
    EnvironmentInfoAction,
    HttpCheckAction,
    HttpFetchAction,
    ListProcessesAction,
    PortCheckAction,
    ProcessOutputContextsAction,
    ProcessOutputDiagnosticsAction,
    ReadProcessAction,
    RunCommandAction,
    RunCommandsAction,
    StartCommandAction,
    StopAllProcessesAction,
    StopProcessAction,
    WaitProcessAction,
    WebFetchAction,
    WriteProcessAction,
)


ProcessAgentAction: TypeAlias = (
    CommandCheckAction
    | CheckRunCommandsAction
    | CheckStartCommandAction
    | PortCheckAction
    | HttpCheckAction
    | HttpFetchAction
    | WebFetchAction
    | EnvironmentInfoAction
    | RunCommandAction
    | RunCommandsAction
    | StartCommandAction
    | ReadProcessAction
    | ProcessOutputContextsAction
    | ProcessOutputDiagnosticsAction
    | WaitProcessAction
    | CheckWriteProcessAction
    | WriteProcessAction
    | ListProcessesAction
    | CheckStopAllProcessesAction
    | CheckStopProcessAction
    | StopProcessAction
    | StopAllProcessesAction
)
