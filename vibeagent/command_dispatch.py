from __future__ import annotations

from collections.abc import Callable

from .command_checkpoint_parsing import parse_checkpoint_local_command
from .command_code_intel_parsing import parse_code_intel_local_command
from .command_core_parsing import parse_core_local_command
from .command_file_edit_parsing import parse_file_edit_local_command
from .command_git_parsing import parse_git_local_command
from .command_inspection_parsing import parse_inspection_local_command
from .command_json_parsing import parse_json_local_command
from .command_process_parsing import parse_process_local_command
from .command_review_parsing import parse_review_local_command
from .command_runtime_parsing import parse_runtime_local_command
from .command_session_parsing import parse_session_local_command
from .command_types import LocalCommand

LocalCommandParser = Callable[[str], LocalCommand | None]

LOCAL_COMMAND_PARSERS: tuple[LocalCommandParser, ...] = (
    parse_core_local_command,
    parse_runtime_local_command,
    parse_inspection_local_command,
    parse_code_intel_local_command,
    parse_json_local_command,
    parse_file_edit_local_command,
    parse_git_local_command,
    parse_process_local_command,
    parse_review_local_command,
    parse_session_local_command,
    parse_checkpoint_local_command,
)


def parse_delegated_local_command(trimmed: str) -> LocalCommand | None:
    for parser in LOCAL_COMMAND_PARSERS:
        command = parser(trimmed)
        if command is not None:
            return command
    return None
