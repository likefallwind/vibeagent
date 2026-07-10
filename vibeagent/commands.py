from __future__ import annotations

from . import (
    check_commands as _check_commands,
    command_parsing as _command_parsing,
    config_commands as _config_commands,
    edit_commands as _edit_commands,
    git_commands as _git_commands,
    help_commands as _help_commands,
    local_runtime_commands as _local_runtime_commands,
    process_commands as _process_commands,
    project_prompt_commands as _project_prompt_commands,
    project_commands as _project_commands,
    project_context_commands as _project_context_commands,
    read_commands as _read_commands,
    session_commands as _session_commands,
    smart_code_commands as _smart_code_commands,
    tool_commands as _tool_commands,
    workflow_commands as _workflow_commands,
)
from .actions import execute_action
from .command_namespace_exports import install_command_exports_from_modules
from .command_parsing import LocalCommand, parse_local_command
from .tool_commands import APPROVAL_REQUIRED_TOOL_NAMES


COMMAND_EXPORT_MODULES = (
    _check_commands,
    _command_parsing,
    _config_commands,
    _edit_commands,
    _git_commands,
    _help_commands,
    _local_runtime_commands,
    _process_commands,
    _project_prompt_commands,
    _project_commands,
    _project_context_commands,
    _read_commands,
    _session_commands,
    _smart_code_commands,
    _tool_commands,
    _workflow_commands,
)


__all__ = install_command_exports_from_modules(globals(), COMMAND_EXPORT_MODULES)


def is_exit_command(value: str) -> bool:
    command = parse_local_command(value)
    return command is not None and command.type == "exit"
