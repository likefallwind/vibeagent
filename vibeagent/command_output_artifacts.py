from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from .workspace_core import RunWorkspace


OUTPUT_DIRECTORY_NAME = "command-output"
_ARTIFACT_NAME = re.compile(r"^[0-9a-f]{32}\.(?:stdout|stderr)\.log$")


def persist_truncated_command_outputs(
    workspace: RunWorkspace,
    stdout: str,
    stderr: str,
    *,
    stdout_truncated: bool,
    stderr_truncated: bool,
) -> tuple[str | None, str | None, str | None]:
    if not stdout_truncated and not stderr_truncated:
        return None, None, None

    try:
        directory = _prepare_output_directory(workspace)
    except OSError as error:
        return None, None, f"Could not create command output artifact directory: {error}"

    artifact_id = uuid.uuid4().hex
    paths: dict[str, str | None] = {"stdout": None, "stderr": None}
    errors: list[str] = []
    for stream, content, truncated in (
        ("stdout", stdout, stdout_truncated),
        ("stderr", stderr, stderr_truncated),
    ):
        if not truncated:
            continue
        target = directory / f"{artifact_id}.{stream}.log"
        try:
            _write_private_text_exclusive(target, content)
        except OSError as error:
            errors.append(f"{stream}: {error}")
        else:
            paths[stream] = command_output_artifact_reference(workspace, target)
    error_text = "Could not save complete command output: " + "; ".join(errors) if errors else None
    return paths["stdout"], paths["stderr"], error_text


def resolve_command_output_artifact(workspace: RunWorkspace, reference: str) -> Path | None:
    if not reference or not reference.strip():
        return None
    candidate = Path(reference)
    lexical = candidate if candidate.is_absolute() else workspace.root / candidate
    if not _ARTIFACT_NAME.fullmatch(lexical.name):
        return None

    directory = workspace.session_dir / OUTPUT_DIRECTORY_NAME
    if lexical.absolute().parent != directory.absolute():
        return None
    if workspace.session_dir.is_symlink() or directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Invalid command output artifact reference: {reference}")
    if lexical.is_symlink() or not lexical.is_file():
        raise ValueError(f"Invalid command output artifact reference: {reference}")
    return lexical.resolve()


def command_output_artifact_reference(workspace: RunWorkspace, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _prepare_output_directory(workspace: RunWorkspace) -> Path:
    session_dir = workspace.session_dir
    if session_dir.is_symlink() or (session_dir.exists() and not session_dir.is_dir()):
        raise OSError("session path is not a regular directory")
    session_dir.mkdir(parents=True, exist_ok=True)
    if session_dir.is_symlink() or not session_dir.is_dir():
        raise OSError("session path is not a regular directory")
    directory = workspace.session_dir / OUTPUT_DIRECTORY_NAME
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise OSError("command output artifact path is not a regular directory")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    return directory


def _write_private_text_exclusive(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", errors="replace") as handle:
            handle.write(content)
    except BaseException:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


__all__ = [
    "OUTPUT_DIRECTORY_NAME",
    "command_output_artifact_reference",
    "persist_truncated_command_outputs",
    "resolve_command_output_artifact",
]
