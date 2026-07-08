from __future__ import annotations

import shlex

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
from .command_types import LocalCommand, make_local_command


def parse_local_command(value: str) -> LocalCommand | None:
    # Recognize slash commands before sending anything to the model.
    trimmed = value.strip()
    core_command = parse_core_local_command(trimmed)
    if core_command is not None:
        return core_command
    runtime_command = parse_runtime_local_command(trimmed)
    if runtime_command is not None:
        return runtime_command
    inspection_command = parse_inspection_local_command(trimmed)
    if inspection_command is not None:
        return inspection_command
    code_intel_command = parse_code_intel_local_command(trimmed)
    if code_intel_command is not None:
        return code_intel_command
    json_command = parse_json_local_command(trimmed)
    if json_command is not None:
        return json_command
    file_edit_command = parse_file_edit_local_command(trimmed)
    if file_edit_command is not None:
        return file_edit_command
    git_command = parse_git_local_command(trimmed)
    if git_command is not None:
        return git_command
    process_command = parse_process_local_command(trimmed)
    if process_command is not None:
        return process_command
    review_command = parse_review_local_command(trimmed)
    if review_command is not None:
        return review_command
    session_command = parse_session_local_command(trimmed)
    if session_command is not None:
        return session_command
    checkpoint_command = parse_checkpoint_local_command(trimmed)
    if checkpoint_command is not None:
        return checkpoint_command
    return None

def parse_local_path_args(argument: str | list[str] | None, max_paths: int) -> list[str]:
    if argument is None:
        return []
    if isinstance(argument, list):
        paths = [path.strip() for path in argument if path.strip()]
    else:
        try:
            paths = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
    if len(paths) > max_paths:
        raise ValueError(f"expected at most {max_paths} paths.")
    return paths


def parse_optional_single_path_argument(argument: str | None) -> str | None:
    if not argument or not argument.strip():
        return None
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) > 1:
        raise ValueError("expected at most one path.")
    return parts[0]
