from __future__ import annotations

from .prompt_observation_utils import truncate


def format_edit_observation(index: int, observation: object) -> str | None:
    if observation.kind in {"edit_file", "check_edit_file", "multi_edit_file", "check_multi_edit_file", "check_notebook_edit", "notebook_edit"}:
        return _format_path_diff(index, observation)

    if observation.kind == "check_replace_lines":
        return "\n".join(
            [
                (
                    f"{index}. check_replace_lines {observation.path}:"
                    f"{observation.start_line}-{observation.end_line}: {observation.message}"
                ),
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"check_replace_python_definition", "replace_python_definition"}:
        target = observation.definition_path or observation.path or "."
        return "\n".join(
            [
                (
                    f"{index}. {observation.kind} {observation.symbol} in {target}: "
                    f"{observation.message}"
                ),
                f"qualifiedName: {observation.qualified_name or '.'}",
                f"lines: {observation.start_line or '?'}-{observation.end_line or '?'}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind == "replace_lines":
        return "\n".join(
            [
                (
                    f"{index}. replace_lines {observation.path}:{observation.start_line}-{observation.end_line}: "
                    f"{observation.message}"
                ),
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"check_insert_lines", "insert_lines"}:
        return "\n".join(
            [
                f"{index}. {observation.kind} {observation.path}:{observation.line}: {observation.message}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"check_append_file", "append_file"}:
        return _format_path_diff(index, observation)

    if observation.kind in {"regex_replace", "check_regex_replace"}:
        return "\n".join(
            [
                (
                    f"{index}. {observation.kind} {observation.path}: {observation.message} "
                    f"replacements={observation.replacements} count={observation.count}"
                ),
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"check_json_set", "json_set", "check_json_remove", "json_remove"}:
        return "\n".join(
            [
                f"{index}. {observation.kind} {observation.path} {observation.pointer}: {observation.message}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"check_json_patch", "json_patch"}:
        return "\n".join(
            [
                f"{index}. {observation.kind} {observation.path}: {observation.message} operations={observation.operation_count}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"check_patch", "patch_file"}:
        return _format_path_diff(index, observation)

    if observation.kind in {"check_patches", "patch_files"}:
        return "\n".join(
            [
                f"{index}. {observation.kind} {', '.join(observation.files) or 'no files'}: {observation.message}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"delete_file", "check_delete_file"}:
        return _format_path_diff(index, observation)

    if observation.kind in {"check_delete_files", "delete_files"}:
        return "\n".join(
            [
                f"{index}. {observation.kind} {', '.join(observation.paths)}: {observation.message}",
                f"diff:\n{truncate(observation.diff)}",
            ]
        )

    if observation.kind in {"move_file", "check_move_file", "copy_file", "check_copy_file"}:
        return f"{index}. {observation.kind} {observation.source} -> {observation.destination}: {observation.message}"

    if observation.kind in {"check_move_files", "move_files", "check_copy_files", "copy_files"}:
        transfers = ", ".join(
            f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
        )
        return f"{index}. {observation.kind} {transfers}: {observation.message}"

    if observation.kind in {"check_move_dir", "move_dir", "check_copy_dir", "copy_dir"}:
        return f"{index}. {observation.kind} {observation.source} -> {observation.destination}: {observation.message}"

    if observation.kind in {"check_move_dirs", "move_dirs", "check_copy_dirs", "copy_dirs"}:
        transfers = ", ".join(
            f"{transfer.source} -> {transfer.destination}" for transfer in observation.transfers
        )
        return f"{index}. {observation.kind} {transfers}: {observation.message}"

    if observation.kind in {
        "check_create_dir",
        "create_dir",
        "check_delete_empty_dir",
        "delete_empty_dir",
    }:
        return f"{index}. {observation.kind} {observation.path}: {observation.message}"

    if observation.kind in {
        "check_create_dirs",
        "create_dirs",
        "check_delete_empty_dirs",
        "delete_empty_dirs",
    }:
        return f"{index}. {observation.kind} {', '.join(observation.paths)}: {observation.message}"

    if observation.kind in {"check_set_executable", "set_executable"}:
        return (
            f"{index}. {observation.kind} {observation.path}: {observation.message} "
            f"ok={str(observation.ok).lower()} executable={str(observation.executable).lower()} "
            f"mode={observation.mode_before or '?'}->{observation.mode_after or '?'}"
        )

    return None


def _format_path_diff(index: int, observation: object) -> str:
    return "\n".join(
        [
            f"{index}. {observation.kind} {observation.path}: {observation.message}",
            f"diff:\n{truncate(observation.diff)}",
        ]
    )


__all__ = ["format_edit_observation"]
