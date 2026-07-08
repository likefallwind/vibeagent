from __future__ import annotations

import shlex

from .command_checkpoint_parsing import parse_checkpoint_local_command
from .command_code_intel_parsing import parse_code_intel_local_command
from .command_git_parsing import parse_git_local_command
from .command_inspection_parsing import parse_inspection_local_command
from .command_process_parsing import parse_process_local_command
from .command_review_parsing import parse_review_local_command
from .command_runtime_parsing import parse_runtime_local_command
from .command_session_parsing import parse_session_local_command
from .command_types import LocalCommand, make_local_command


def parse_local_command(value: str) -> LocalCommand | None:
    # Recognize slash commands before sending anything to the model.
    trimmed = value.strip()
    if trimmed == "/exit":
        return LocalCommand(type="exit")
    if trimmed == "/help":
        return LocalCommand(type="help")
    if trimmed == "/model":
        return LocalCommand(type="model")
    if trimmed == "/config":
        return LocalCommand(type="config")
    runtime_command = parse_runtime_local_command(trimmed)
    if runtime_command is not None:
        return runtime_command
    inspection_command = parse_inspection_local_command(trimmed)
    if inspection_command is not None:
        return inspection_command
    code_intel_command = parse_code_intel_local_command(trimmed)
    if code_intel_command is not None:
        return code_intel_command
    if trimmed == "/config-check" or trimmed.startswith("/config-check "):
        return LocalCommand(type="config_check", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-json-set" or trimmed.startswith("/check-json-set "):
        return LocalCommand(type="check_json_set", argument=trimmed[16:].strip() or None)
    if trimmed == "/json-set" or trimmed.startswith("/json-set "):
        return LocalCommand(type="json_set", argument=trimmed[10:].strip() or None)
    if trimmed == "/check-json-remove" or trimmed.startswith("/check-json-remove "):
        return LocalCommand(type="check_json_remove", argument=trimmed[19:].strip() or None)
    if trimmed == "/json-remove" or trimmed.startswith("/json-remove "):
        return LocalCommand(type="json_remove", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-json-patch" or trimmed.startswith("/check-json-patch "):
        return LocalCommand(type="check_json_patch", argument=trimmed[18:].strip() or None)
    if trimmed == "/json-patch" or trimmed.startswith("/json-patch "):
        return LocalCommand(type="json_patch", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-replace-lines" or trimmed.startswith("/check-replace-lines "):
        return LocalCommand(type="check_replace_lines", argument=trimmed[21:].strip() or None)
    if trimmed == "/replace-lines" or trimmed.startswith("/replace-lines "):
        return LocalCommand(type="replace_lines", argument=trimmed[15:].strip() or None)
    if trimmed == "/check-insert-lines" or trimmed.startswith("/check-insert-lines "):
        return LocalCommand(type="check_insert_lines", argument=trimmed[20:].strip() or None)
    if trimmed == "/insert-lines" or trimmed.startswith("/insert-lines "):
        return LocalCommand(type="insert_lines", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-append" or trimmed.startswith("/check-append "):
        return LocalCommand(type="check_append_file", argument=trimmed[14:].strip() or None)
    if trimmed == "/append" or trimmed.startswith("/append "):
        return LocalCommand(type="append_file", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-write" or trimmed.startswith("/check-write "):
        return LocalCommand(type="check_write_file", argument=trimmed[13:].strip() or None)
    if trimmed == "/write" or trimmed.startswith("/write "):
        return LocalCommand(type="write_file", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-write-files" or trimmed.startswith("/check-write-files "):
        return LocalCommand(type="check_write_files", argument=trimmed[19:].strip() or None)
    if trimmed == "/write-files" or trimmed.startswith("/write-files "):
        return LocalCommand(type="write_files", argument=trimmed[13:].strip() or None)
    if trimmed == "/check-edit" or trimmed.startswith("/check-edit "):
        return LocalCommand(type="check_edit_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/edit" or trimmed.startswith("/edit "):
        return LocalCommand(type="edit_file", argument=trimmed[6:].strip() or None)
    if trimmed == "/check-multi-edit" or trimmed.startswith("/check-multi-edit "):
        return LocalCommand(type="check_multi_edit_file", argument=trimmed[18:].strip() or None)
    if trimmed == "/multi-edit" or trimmed.startswith("/multi-edit "):
        return LocalCommand(type="multi_edit_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-delete" or trimmed.startswith("/check-delete "):
        return LocalCommand(type="check_delete_file", argument=trimmed[14:].strip() or None)
    if trimmed == "/delete" or trimmed.startswith("/delete "):
        return LocalCommand(type="delete_file", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-delete-files" or trimmed.startswith("/check-delete-files "):
        return LocalCommand(type="check_delete_files", argument=trimmed[20:].strip() or None)
    if trimmed == "/delete-files" or trimmed.startswith("/delete-files "):
        return LocalCommand(type="delete_files", argument=trimmed[14:].strip() or None)
    if trimmed == "/check-move" or trimmed.startswith("/check-move "):
        return LocalCommand(type="check_move_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/move" or trimmed.startswith("/move "):
        return LocalCommand(type="move_file", argument=trimmed[6:].strip() or None)
    if trimmed == "/check-move-files" or trimmed.startswith("/check-move-files "):
        return LocalCommand(type="check_move_files", argument=trimmed[18:].strip() or None)
    if trimmed == "/move-files" or trimmed.startswith("/move-files "):
        return LocalCommand(type="move_files", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-copy" or trimmed.startswith("/check-copy "):
        return LocalCommand(type="check_copy_file", argument=trimmed[12:].strip() or None)
    if trimmed == "/copy" or trimmed.startswith("/copy "):
        return LocalCommand(type="copy_file", argument=trimmed[6:].strip() or None)
    if trimmed == "/check-copy-files" or trimmed.startswith("/check-copy-files "):
        return LocalCommand(type="check_copy_files", argument=trimmed[18:].strip() or None)
    if trimmed == "/copy-files" or trimmed.startswith("/copy-files "):
        return LocalCommand(type="copy_files", argument=trimmed[12:].strip() or None)
    if trimmed == "/check-move-dir" or trimmed.startswith("/check-move-dir "):
        return LocalCommand(type="check_move_dir", argument=trimmed[16:].strip() or None)
    if trimmed == "/move-dir" or trimmed.startswith("/move-dir "):
        return LocalCommand(type="move_dir", argument=trimmed[10:].strip() or None)
    if trimmed == "/check-move-dirs" or trimmed.startswith("/check-move-dirs "):
        return LocalCommand(type="check_move_dirs", argument=trimmed[17:].strip() or None)
    if trimmed == "/move-dirs" or trimmed.startswith("/move-dirs "):
        return LocalCommand(type="move_dirs", argument=trimmed[11:].strip() or None)
    if trimmed == "/check-copy-dir" or trimmed.startswith("/check-copy-dir "):
        return LocalCommand(type="check_copy_dir", argument=trimmed[16:].strip() or None)
    if trimmed == "/copy-dir" or trimmed.startswith("/copy-dir "):
        return LocalCommand(type="copy_dir", argument=trimmed[10:].strip() or None)
    if trimmed == "/check-copy-dirs" or trimmed.startswith("/check-copy-dirs "):
        return LocalCommand(type="check_copy_dirs", argument=trimmed[17:].strip() or None)
    if trimmed == "/copy-dirs" or trimmed.startswith("/copy-dirs "):
        return LocalCommand(type="copy_dirs", argument=trimmed[11:].strip() or None)
    if trimmed == "/check-mkdir" or trimmed.startswith("/check-mkdir "):
        return LocalCommand(type="check_create_dir", argument=trimmed[13:].strip() or None)
    if trimmed == "/mkdir" or trimmed.startswith("/mkdir "):
        return LocalCommand(type="create_dir", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-mkdirs" or trimmed.startswith("/check-mkdirs "):
        return LocalCommand(type="check_create_dirs", argument=trimmed[14:].strip() or None)
    if trimmed == "/mkdirs" or trimmed.startswith("/mkdirs "):
        return LocalCommand(type="create_dirs", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-rmdir" or trimmed.startswith("/check-rmdir "):
        return LocalCommand(type="check_delete_empty_dir", argument=trimmed[13:].strip() or None)
    if trimmed == "/rmdir" or trimmed.startswith("/rmdir "):
        return LocalCommand(type="delete_empty_dir", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-rmdirs" or trimmed.startswith("/check-rmdirs "):
        return LocalCommand(type="check_delete_empty_dirs", argument=trimmed[14:].strip() or None)
    if trimmed == "/rmdirs" or trimmed.startswith("/rmdirs "):
        return LocalCommand(type="delete_empty_dirs", argument=trimmed[8:].strip() or None)
    if trimmed == "/check-executable" or trimmed.startswith("/check-executable "):
        return LocalCommand(type="check_set_executable", argument=trimmed[18:].strip() or None)
    if trimmed == "/set-executable" or trimmed.startswith("/set-executable "):
        return LocalCommand(type="set_executable", argument=trimmed[16:].strip() or None)
    if trimmed == "/check-patch" or trimmed.startswith("/check-patch "):
        return LocalCommand(type="check_patch", argument=trimmed[13:].strip() or None)
    if trimmed == "/patch" or trimmed.startswith("/patch "):
        return LocalCommand(type="patch_file", argument=trimmed[7:].strip() or None)
    if trimmed == "/check-patches" or trimmed.startswith("/check-patches "):
        return LocalCommand(type="check_patches", argument=trimmed[15:].strip() or None)
    if trimmed == "/patches" or trimmed.startswith("/patches "):
        return LocalCommand(type="patch_files", argument=trimmed[9:].strip() or None)
    if trimmed == "/check-regex-replace" or trimmed.startswith("/check-regex-replace "):
        return LocalCommand(type="check_regex_replace", argument=trimmed[21:].strip() or None)
    if trimmed == "/regex-replace" or trimmed.startswith("/regex-replace "):
        return LocalCommand(type="regex_replace", argument=trimmed[15:].strip() or None)
    git_command = parse_git_local_command(trimmed)
    if git_command is not None:
        return git_command
    process_command = parse_process_local_command(trimmed)
    if process_command is not None:
        return process_command
    review_command = parse_review_local_command(trimmed)
    if review_command is not None:
        return review_command
    if trimmed == "/clear":
        return LocalCommand(type="clear")
    if trimmed == "/usage":
        return LocalCommand(type="usage")
    if trimmed == "/cost":
        return LocalCommand(type="cost")
    if trimmed == "/approval" or trimmed.startswith("/approval "):
        return LocalCommand(type="approval", argument=trimmed[9:].strip() or None)
    session_command = parse_session_local_command(trimmed)
    if session_command is not None:
        return session_command
    checkpoint_command = parse_checkpoint_local_command(trimmed)
    if checkpoint_command is not None:
        return checkpoint_command
    if trimmed == "/resume" or trimmed.startswith("/resume "):
        return LocalCommand(type="resume", argument=trimmed[8:].strip() or None)
    if trimmed == "/compact" or trimmed.startswith("/compact "):
        return LocalCommand(type="compact", argument=trimmed[9:].strip() or None)
    if trimmed == "/chat" or trimmed.startswith("/chat "):
        return LocalCommand(type="chat", argument=trimmed[5:].strip() or None)
    if trimmed == "/code" or trimmed.startswith("/code "):
        return LocalCommand(type="code", argument=trimmed[5:].strip() or None)
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
