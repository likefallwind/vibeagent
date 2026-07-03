from __future__ import annotations

from pathlib import Path
from typing import Callable


SessionContextGetter = Callable[..., tuple[str | None, str | None, str]]


def build_context_limit_kwargs(
    max_failures: int | None = None,
    max_files: int | None = None,
    max_commands: int | None = None,
    max_checks: int | None = None,
    max_output_chars: int | None = None,
    max_text: int | None = None,
) -> dict[str, int]:
    values = {
        "max_failures": max_failures,
        "max_files": max_files,
        "max_commands": max_commands,
        "max_checks": max_checks,
        "max_output_chars": max_output_chars,
        "max_text": max_text,
    }
    return {key: value for key, value in values.items() if value is not None}


def normalize_resume_arg(value: str) -> str | None:
    return value or None


def is_resume_clear_arg(value: str | None) -> bool:
    return isinstance(value, str) and value.strip().lower() in {"off", "clear", "none"}


def resolve_one_shot_prior_context(
    *,
    resume_arg: str | None,
    compact_arg: str | None,
    project_root: Path,
    resume_kwargs: dict[str, int],
    compact_kwargs: dict[str, int],
    get_resume_context_func: SessionContextGetter,
    get_compact_context_func: SessionContextGetter,
) -> tuple[str | None, str | None]:
    if resume_arg is not None:
        normalized_resume_arg = normalize_resume_arg(resume_arg)
        _selected, resume_context, text = get_resume_context_func(normalized_resume_arg, project_root, **resume_kwargs)
        if resume_context is None and not is_resume_clear_arg(normalized_resume_arg):
            return None, text
        return resume_context, None
    if compact_arg is not None:
        _selected, resume_context, text = get_compact_context_func(normalize_resume_arg(compact_arg), project_root, **compact_kwargs)
        if resume_context is None:
            return None, text
        return resume_context, None

    _selected, resume_context, _text = get_compact_context_func(None, project_root)
    return resume_context, None
