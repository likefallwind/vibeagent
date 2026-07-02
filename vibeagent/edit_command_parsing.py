from __future__ import annotations

import json
import shlex
import sys

from .process_commands import decode_stdin_escapes
from .types import DirectoryTransfer, EditOperation, JsonPatchOperation, MoveFileTransfer, WriteFileItem

def parse_required_single_path_argument(argument: str | None, *, path: str | None = None, usage: str) -> str:
    if path is not None:
        if not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        return path.strip()

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires a path.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 1:
        raise ValueError("expected one path.")
    parsed_path = parts[0].strip()
    if not parsed_path:
        raise ValueError(f"{usage} requires a non-empty path.")
    return parsed_path


def parse_required_path_list_argument(argument: str | None, *, paths: list[str] | None = None, usage: str) -> list[str]:
    if paths is not None:
        parsed_paths = [path.strip() for path in paths if path and path.strip()]
        if not parsed_paths:
            raise ValueError(f"{usage} requires at least one path.")
        return parsed_paths

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires at least one path.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    parsed_paths = [part.strip() for part in parts if part.strip()]
    if not parsed_paths:
        raise ValueError(f"{usage} requires at least one path.")
    return parsed_paths


def parse_source_destination_argument(
    argument: str | None,
    *,
    source: str | None = None,
    destination: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if source is not None or destination is not None:
        if not source or not source.strip():
            raise ValueError(f"{usage} requires a non-empty source.")
        if not destination or not destination.strip():
            raise ValueError(f"{usage} requires a non-empty destination.")
        return source.strip(), destination.strip()

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires source and destination.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected source and destination.")
    parsed_source, parsed_destination = parts[0].strip(), parts[1].strip()
    if not parsed_source:
        raise ValueError(f"{usage} requires a non-empty source.")
    if not parsed_destination:
        raise ValueError(f"{usage} requires a non-empty destination.")
    return parsed_source, parsed_destination


def parse_file_transfer_list_argument(
    argument: str | None,
    *,
    transfers: list[MoveFileTransfer] | list[str] | None = None,
    usage: str,
) -> list[MoveFileTransfer]:
    if transfers is not None:
        if transfers and all(isinstance(transfer, MoveFileTransfer) for transfer in transfers):
            return list(transfers)
        parts = [str(part).strip() for part in transfers if str(part).strip()]
    else:
        if not argument or not argument.strip():
            raise ValueError(f"{usage} requires source and destination pairs.")
        try:
            split_parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        parts = [part.strip() for part in split_parts if part.strip()]

    if not parts:
        raise ValueError(f"{usage} requires source and destination pairs.")
    if len(parts) % 2 != 0:
        raise ValueError("expected source and destination pairs.")

    parsed_transfers: list[MoveFileTransfer] = []
    for index in range(0, len(parts), 2):
        source, destination = parts[index], parts[index + 1]
        if not source:
            raise ValueError(f"{usage} requires a non-empty source.")
        if not destination:
            raise ValueError(f"{usage} requires a non-empty destination.")
        parsed_transfers.append(MoveFileTransfer(source=source, destination=destination))
    return parsed_transfers


def parse_directory_transfer_list_argument(
    argument: str | None,
    *,
    transfers: list[DirectoryTransfer] | list[str] | None = None,
    usage: str,
) -> list[DirectoryTransfer]:
    if transfers is not None:
        if transfers and all(isinstance(transfer, DirectoryTransfer) for transfer in transfers):
            return list(transfers)
        parts = [str(part).strip() for part in transfers if str(part).strip()]
    else:
        if not argument or not argument.strip():
            raise ValueError(f"{usage} requires source and destination pairs.")
        try:
            split_parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        parts = [part.strip() for part in split_parts if part.strip()]

    if not parts:
        raise ValueError(f"{usage} requires source and destination pairs.")
    if len(parts) % 2 != 0:
        raise ValueError("expected source and destination pairs.")

    parsed_transfers: list[DirectoryTransfer] = []
    for index in range(0, len(parts), 2):
        source, destination = parts[index], parts[index + 1]
        if not source:
            raise ValueError(f"{usage} requires a non-empty source.")
        if not destination:
            raise ValueError(f"{usage} requires a non-empty destination.")
        parsed_transfers.append(DirectoryTransfer(source=source, destination=destination))
    return parsed_transfers


def parse_executable_argument(
    argument: str | None,
    *,
    path: str | None = None,
    executable: bool | str | None = None,
    usage: str,
) -> tuple[str, bool]:
    if path is not None or executable is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        return path.strip(), parse_optional_bool(executable, field="executable", default=True)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires a path.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) not in (1, 2):
        raise ValueError("expected path and optional executable value.")
    parsed_path = parts[0].strip()
    if not parsed_path:
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_executable = parse_optional_bool(parts[1] if len(parts) == 2 else None, field="executable", default=True)
    return parsed_path, parsed_executable


def parse_optional_bool(value: bool | str | None, *, field: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1", "on"}:
        return True
    if normalized in {"false", "no", "0", "off"}:
        return False
    raise ValueError(f"{field} must be true or false.")


def parse_patch_argument(
    argument: str | None,
    *,
    path: str | None = None,
    patch: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or patch is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if patch is None:
            raise ValueError(f"{usage} requires a patch.")
        return path.strip(), read_patch_argument_value(patch)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and patch.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and patch.")
    parsed_path = parts[0].strip()
    if not parsed_path:
        raise ValueError(f"{usage} requires a non-empty path.")
    return parsed_path, read_patch_argument_value(parts[1])


def parse_patches_argument(argument: str | None, *, patch: str | None = None, usage: str) -> str:
    if patch is not None:
        return read_patch_argument_value(patch)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires a patch.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 1:
        raise ValueError("expected patch.")
    return read_patch_argument_value(parts[0])


def read_patch_argument_value(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    return decode_stdin_escapes(value)


def parse_write_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or content is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if content is None:
            raise ValueError(f"{usage} requires text.")
        return path.strip(), decode_stdin_escapes(content)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and text.")
    parsed_path, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    return parsed_path, decode_stdin_escapes(raw_content)


def parse_write_file_list_argument(
    argument: str | None,
    *,
    files: list[WriteFileItem] | list[str] | None = None,
    usage: str,
) -> list[WriteFileItem]:
    if files is not None:
        if files and all(isinstance(file, WriteFileItem) for file in files):
            return list(files)
        parts = [str(part) for part in files]
    else:
        if not argument or not argument.strip():
            raise ValueError(f"{usage} requires path and text pairs.")
        try:
            split_parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        parts = list(split_parts)

    if not parts:
        raise ValueError(f"{usage} requires path and text pairs.")
    if len(parts) % 2 != 0:
        raise ValueError("expected path and text pairs.")

    parsed_files: list[WriteFileItem] = []
    for index in range(0, len(parts), 2):
        path, raw_content = parts[index], parts[index + 1]
        if not path:
            raise ValueError(f"{usage} requires a non-empty path.")
        parsed_files.append(WriteFileItem(path=path, content=decode_stdin_escapes(raw_content)))
    return parsed_files


def parse_edit_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    old: str | None = None,
    new: str | None = None,
    usage: str,
) -> tuple[str, str, str]:
    if path is not None or old is not None or new is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if old is None or old == "":
            raise ValueError(f"{usage} requires non-empty old text.")
        if new is None:
            raise ValueError(f"{usage} requires new text.")
        return path.strip(), decode_stdin_escapes(old), decode_stdin_escapes(new)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, old text, and new text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 3:
        raise ValueError("expected path, old text, and new text.")
    parsed_path, raw_old, raw_new = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if raw_old == "":
        raise ValueError(f"{usage} requires non-empty old text.")
    return parsed_path.strip(), decode_stdin_escapes(raw_old), decode_stdin_escapes(raw_new)


def parse_multi_edit_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    edits: list[EditOperation] | list[str] | None = None,
    usage: str,
) -> tuple[str, list[EditOperation]]:
    if edits is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if edits and all(isinstance(edit, EditOperation) for edit in edits):
            return path.strip(), list(edits)
        parts = [str(part) for part in edits]
        parsed_path = path.strip()
    else:
        if not argument or not argument.strip():
            raise ValueError(f"{usage} requires path and old/new pairs.")
        try:
            split_parts = shlex.split(argument)
        except ValueError as error:
            raise ValueError(str(error)) from error
        if not split_parts:
            raise ValueError(f"{usage} requires path and old/new pairs.")
        parsed_path, parts = split_parts[0].strip(), list(split_parts[1:])
        if not parsed_path:
            raise ValueError(f"{usage} requires a non-empty path.")

    if not parts:
        raise ValueError(f"{usage} requires at least one old/new pair.")
    if len(parts) % 2 != 0:
        raise ValueError("expected old/new pairs.")

    parsed_edits: list[EditOperation] = []
    for index in range(0, len(parts), 2):
        old, new = parts[index], parts[index + 1]
        if old == "":
            raise ValueError(f"{usage} requires non-empty old text.")
        parsed_edits.append(EditOperation(old=decode_stdin_escapes(old), new=decode_stdin_escapes(new)))
    return parsed_path, parsed_edits


def parse_json_set_argument(
    argument: str | None,
    *,
    path: str | None = None,
    pointer: str | None = None,
    value: object = None,
    create_missing: bool = False,
    usage: str,
) -> tuple[str, str, object, bool]:
    if path is not None or pointer is not None:
        if not path or not path.strip() or not pointer or not pointer.strip():
            raise ValueError(f"{usage} requires path and pointer.")
        return path.strip(), pointer.strip(), value, create_missing

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, pointer, and JSON value.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    parsed_create_missing = False
    if "--create-missing" in parts:
        parsed_create_missing = True
        parts = [part for part in parts if part != "--create-missing"]
    if len(parts) != 3:
        raise ValueError("expected path, pointer, and JSON value.")
    parsed_path, parsed_pointer, raw_value = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if not parsed_pointer.strip():
        raise ValueError(f"{usage} requires a non-empty pointer.")
    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON value is invalid: {error.msg}") from error
    return parsed_path, parsed_pointer, parsed_value, parsed_create_missing


def parse_json_remove_argument(
    argument: str | None,
    *,
    path: str | None = None,
    pointer: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or pointer is not None:
        if not path or not path.strip() or not pointer or not pointer.strip():
            raise ValueError(f"{usage} requires path and pointer.")
        return path.strip(), pointer.strip()

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and pointer.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and pointer.")
    parsed_path, parsed_pointer = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if not parsed_pointer.strip():
        raise ValueError(f"{usage} requires a non-empty pointer.")
    return parsed_path, parsed_pointer


def parse_json_patch_argument(
    argument: str | None,
    *,
    path: str | None = None,
    operations: object = None,
    usage: str,
) -> tuple[str, list[JsonPatchOperation]]:
    if path is not None or operations is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        return path.strip(), parse_json_patch_operations(operations)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and JSON operations array.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and JSON operations array.")
    parsed_path, raw_operations = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    try:
        parsed_operations = json.loads(raw_operations)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON operations array is invalid: {error.msg}") from error
    return parsed_path, parse_json_patch_operations(parsed_operations)


def parse_json_patch_operations(operations: object) -> list[JsonPatchOperation]:
    if not isinstance(operations, list) or not operations:
        raise ValueError("JSON operations must be a non-empty array.")
    if len(operations) > 50:
        raise ValueError("JSON operations must contain at most 50 items.")
    parsed: list[JsonPatchOperation] = []
    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            raise ValueError(f"operation {index} must be an object.")
        op = operation.get("op")
        pointer = operation.get("path")
        if op not in {"add", "replace", "remove"}:
            raise ValueError(f"operation {index} has an unsupported op.")
        if not isinstance(pointer, str) or not pointer.strip():
            raise ValueError(f"operation {index} requires a non-empty path.")
        if op in {"add", "replace"} and "value" not in operation:
            raise ValueError(f"operation {index} requires value.")
        parsed.append(JsonPatchOperation(op=op, path=pointer.strip(), value=operation.get("value")))
    return parsed


def parse_replace_lines_argument(
    argument: str | None,
    *,
    path: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, int, int, str]:
    if any(value is not None for value in (path, start_line, end_line, content)):
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if start_line is None or end_line is None:
            raise ValueError(f"{usage} requires start and end line numbers.")
        if content is None:
            raise ValueError(f"{usage} requires text.")
        return path.strip(), validate_line_number(start_line, "start"), validate_line_range(start_line, end_line), decode_stdin_escapes(content)

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, start, end, and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 4:
        raise ValueError("expected path, start, end, and text.")
    parsed_path, raw_start, raw_end, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_start = parse_line_number(raw_start, "start")
    parsed_end = parse_line_number(raw_end, "end")
    if parsed_end < parsed_start:
        raise ValueError("end must be greater than or equal to start.")
    return parsed_path, parsed_start, parsed_end, decode_stdin_escapes(raw_content)


def parse_insert_lines_argument(
    argument: str | None,
    *,
    path: str | None = None,
    line: int | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, int, str]:
    if any(value is not None for value in (path, line, content)):
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if line is None:
            raise ValueError(f"{usage} requires a line number.")
        parsed_content = decode_stdin_escapes(content or "")
        if parsed_content == "":
            raise ValueError(f"{usage} requires non-empty text.")
        return path.strip(), validate_line_number(line, "line"), parsed_content

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, line, and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 3:
        raise ValueError("expected path, line, and text.")
    parsed_path, raw_line, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_content = decode_stdin_escapes(raw_content)
    if parsed_content == "":
        raise ValueError(f"{usage} requires non-empty text.")
    return parsed_path, parse_line_number(raw_line, "line"), parsed_content


def parse_append_file_argument(
    argument: str | None,
    *,
    path: str | None = None,
    content: str | None = None,
    usage: str,
) -> tuple[str, str]:
    if path is not None or content is not None:
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        parsed_content = decode_stdin_escapes(content or "")
        if parsed_content == "":
            raise ValueError(f"{usage} requires non-empty text.")
        return path.strip(), parsed_content

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path and text.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error
    if len(parts) != 2:
        raise ValueError("expected path and text.")
    parsed_path, raw_content = parts
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    parsed_content = decode_stdin_escapes(raw_content)
    if parsed_content == "":
        raise ValueError(f"{usage} requires non-empty text.")
    return parsed_path, parsed_content


def parse_regex_replace_argument(
    argument: str | None,
    *,
    path: str | None = None,
    pattern: str | None = None,
    replacement: str | None = None,
    count: int | str = 0,
    case_sensitive: bool = True,
    multiline: bool = False,
    max_replacements: int | str = 100,
    usage: str,
) -> dict[str, object]:
    if any(value is not None for value in (path, pattern, replacement)):
        if not path or not path.strip():
            raise ValueError(f"{usage} requires a non-empty path.")
        if not pattern:
            raise ValueError(f"{usage} requires a non-empty pattern.")
        if replacement is None:
            raise ValueError(f"{usage} requires replacement text.")
        return {
            "path": path.strip(),
            "pattern": pattern,
            "replacement": decode_stdin_escapes(replacement),
            "count": validate_nonnegative_int(count, "count", maximum=1000),
            "case_sensitive": bool(case_sensitive),
            "multiline": bool(multiline),
            "max_replacements": validate_positive_int(max_replacements, "max-replacements", maximum=1000),
        }

    if not argument or not argument.strip():
        raise ValueError(f"{usage} requires path, pattern, and replacement.")
    try:
        parts = shlex.split(argument)
    except ValueError as error:
        raise ValueError(str(error)) from error

    parsed_count = 0
    parsed_case_sensitive = True
    parsed_multiline = False
    parsed_max_replacements = 100
    positional: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--ignore-case":
            parsed_case_sensitive = False
            index += 1
        elif part == "--case-sensitive":
            parsed_case_sensitive = True
            index += 1
        elif part == "--multiline":
            parsed_multiline = True
            index += 1
        elif part == "--count":
            if index + 1 >= len(parts):
                raise ValueError("--count requires a value.")
            parsed_count = validate_nonnegative_int(parts[index + 1], "count", maximum=1000)
            index += 2
        elif part == "--max-replacements":
            if index + 1 >= len(parts):
                raise ValueError("--max-replacements requires a value.")
            parsed_max_replacements = validate_positive_int(parts[index + 1], "max-replacements", maximum=1000)
            index += 2
        elif part.startswith("-"):
            raise ValueError(f"unknown option: {part}")
        else:
            positional.append(part)
            index += 1
    if len(positional) != 3:
        raise ValueError("expected path, pattern, and replacement.")
    parsed_path, parsed_pattern, parsed_replacement = positional
    if not parsed_path.strip():
        raise ValueError(f"{usage} requires a non-empty path.")
    if not parsed_pattern:
        raise ValueError(f"{usage} requires a non-empty pattern.")
    return {
        "path": parsed_path,
        "pattern": parsed_pattern,
        "replacement": decode_stdin_escapes(parsed_replacement),
        "count": parsed_count,
        "case_sensitive": parsed_case_sensitive,
        "multiline": parsed_multiline,
        "max_replacements": parsed_max_replacements,
    }


def parse_line_number(value: str, name: str) -> int:
    if not value.isdigit():
        raise ValueError(f"{name} must be a positive integer.")
    return validate_line_number(int(value), name)


def validate_line_number(value: object, name: str) -> int:
    if isinstance(value, str):
        return parse_line_number(value, name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer.")
    if value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def validate_line_range(start_line: object, end_line: object) -> int:
    parsed_start = validate_line_number(start_line, "start")
    parsed_end = validate_line_number(end_line, "end")
    if parsed_end < parsed_start:
        raise ValueError("end must be greater than or equal to start.")
    return parsed_end


def validate_nonnegative_int(value: object, name: str, *, maximum: int) -> int:
    if isinstance(value, str):
        if not value.isdigit():
            raise ValueError(f"{name} must be a non-negative integer.")
        parsed = int(value)
    elif isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a non-negative integer.")
    else:
        parsed = value
    if parsed < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    if parsed > maximum:
        raise ValueError(f"{name} must be at most {maximum}.")
    return parsed


def validate_positive_int(value: object, name: str, *, maximum: int) -> int:
    parsed = validate_nonnegative_int(value, name, maximum=maximum)
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return parsed

