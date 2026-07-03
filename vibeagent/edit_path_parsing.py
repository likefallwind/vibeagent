from __future__ import annotations

import shlex

from .types import DirectoryTransfer, MoveFileTransfer


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
