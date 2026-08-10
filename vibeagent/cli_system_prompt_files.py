from __future__ import annotations

from pathlib import Path

from .workspace_metadata_files import has_symlink_component, read_regular_file_bytes


MAX_SYSTEM_PROMPT_FILE_BYTES = 200_000


def resolve_system_prompt_inputs(
    *,
    system_prompt: str | None,
    system_prompt_file: str | None,
    append_system_prompt: str | None,
    append_system_prompt_file: str | None,
    invocation_root: Path,
) -> tuple[str | None, str | None]:
    replacement = system_prompt
    if system_prompt_file is not None:
        replacement = read_system_prompt_file(
            system_prompt_file,
            invocation_root=invocation_root,
            option="--system-prompt-file",
        )

    appended_file = None
    if append_system_prompt_file is not None:
        appended_file = read_system_prompt_file(
            append_system_prompt_file,
            invocation_root=invocation_root,
            option="--append-system-prompt-file",
        )
    return _normalized_text(replacement), _combine_text(append_system_prompt, appended_file)


def read_system_prompt_file(path_value: str, *, invocation_root: Path, option: str) -> str:
    if not path_value.strip():
        raise ValueError(f"{option} path cannot be empty.")
    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = invocation_root / candidate
    candidate = candidate.absolute()
    root = Path(candidate.anchor)
    if has_symlink_component(root, candidate):
        raise ValueError(f"{option} must not use symbolic links: {path_value}")
    try:
        raw = read_regular_file_bytes(
            candidate,
            max_bytes=MAX_SYSTEM_PROMPT_FILE_BYTES,
            label=option,
        )
    except (OSError, ValueError) as error:
        if isinstance(error, ValueError):
            raise
        raise ValueError(f"Cannot read {option} '{path_value}': {error.strerror or error}") from error
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{option} must be valid UTF-8: {path_value}") from error
    normalized = _normalized_text(content)
    if normalized is None:
        raise ValueError(f"{option} cannot be empty: {path_value}")
    return normalized


def _normalized_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _combine_text(first: str | None, second: str | None) -> str | None:
    chunks = [value.strip() for value in (first, second) if value is not None and value.strip()]
    return "\n\n".join(chunks) or None


__all__ = ["MAX_SYSTEM_PROMPT_FILE_BYTES", "read_system_prompt_file", "resolve_system_prompt_inputs"]
