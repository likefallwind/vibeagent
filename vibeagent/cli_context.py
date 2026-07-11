from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .session_input import normalize_optional_run_id


SessionContextGetter = Callable[..., tuple[str | None, str | None, str]]


@dataclass(frozen=True)
class OneShotPriorContext:
    context: str | None = None
    error: str | None = None
    source: str = "auto_compact"
    run_id: str | None = None

    @property
    def loaded(self) -> bool:
        return self.context is not None

    def to_json(self) -> dict[str, object]:
        return {
            "loaded": self.loaded,
            "source": self.source,
            "runId": self.run_id,
        }


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
    return normalize_optional_run_id(value)


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
) -> OneShotPriorContext:
    if resume_arg is not None:
        normalized_resume_arg = normalize_resume_arg(resume_arg)
        selected, resume_context, text = get_resume_context_func(normalized_resume_arg, project_root, **resume_kwargs)
        if resume_context is None and not is_resume_clear_arg(normalized_resume_arg):
            return OneShotPriorContext(error=text, source="resume", run_id=selected)
        source = "resume_clear" if is_resume_clear_arg(normalized_resume_arg) else "resume"
        return OneShotPriorContext(context=resume_context, source=source, run_id=selected)
    if compact_arg is not None:
        selected, resume_context, text = get_compact_context_func(normalize_resume_arg(compact_arg), project_root, **compact_kwargs)
        if resume_context is None:
            return OneShotPriorContext(error=text, source="compact", run_id=selected)
        return OneShotPriorContext(context=resume_context, source="compact", run_id=selected)

    selected, resume_context, _text = get_compact_context_func(None, project_root)
    return OneShotPriorContext(context=resume_context, source="auto_compact", run_id=selected)
