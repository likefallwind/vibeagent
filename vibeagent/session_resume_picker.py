from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import BinaryIO

from .cli_config import resolve_project_root
from .cli_context import is_resume_clear_arg
from .cli_numbered_picker import prompt_numbered_choice
from .session_id import is_valid_session_id
from .session_machine_index import is_machine_searchable_session_id
from .session_names import (
    SESSION_BRANCH_EVENT,
    SESSION_NAMED_EVENT,
    normalize_session_name,
    resolve_session_reference,
)
from .session_store import list_sessions
from .session_utils import compact, events_path
from .terminal_text import terminal_safe_text


MAX_RESUME_SESSION_SCAN = 1_000
MAX_RESUME_SESSION_CANDIDATES = 100
MAX_RESUME_SEARCH_QUERY_CHARS = 2_048
MAX_RESUME_PICKER_EVENTS = 10_000
MAX_RESUME_PICKER_EVENT_BYTES = 1 * 1024 * 1024


@dataclass(frozen=True)
class ResumeSessionCandidate:
    run_id: str
    session_name: str | None
    task: str | None
    status: str
    last_event_time: datetime | None

    @property
    def search_text(self) -> str:
        return " ".join(
            part
            for part in (
                self.run_id,
                self.session_name,
                self.status,
                compact(self.task, 1_000) if self.task else None,
            )
            if part
        ).casefold()


def prepare_session_resume(
    args: argparse.Namespace,
    *,
    input_func: Callable[[str], str] | None = None,
    print_func: Callable[[str], None] = print,
    terminal_available: bool | None = None,
) -> None:
    selector = getattr(args, "resume", None)
    if (
        selector is None
        or getattr(args, "resume_from_continue", False)
        or getattr(args, "resume_from_pull_request", False)
        or getattr(args, "resume_from_background_followup", False)
    ):
        return
    root = (resolve_project_root(getattr(args, "cwd", None)) or Path.cwd()).resolve()
    exact = resolve_exact_resume_reference(root, selector)
    if exact is not None:
        args.resume = exact
        return
    if terminal_available is None:
        terminal_available = sys.stdin.isatty() and sys.stdout.isatty()
    if not terminal_available or args.json or args.output_format != "text":
        raise ValueError(
            "--resume without an exact session ID or name requires an interactive text terminal."
        )
    query = selector.strip() or None
    candidates = list_resume_session_candidates(root, query)
    args.resume = prompt_resume_session(
        candidates,
        query=query,
        input_func=input_func,
        print_func=print_func,
    )
    args.resume_from_picker = True


def resolve_exact_resume_reference(project_root: Path, selector: str) -> str | None:
    value = selector.strip()
    if not value:
        return None
    if value.casefold() == "latest" or is_resume_clear_arg(value):
        return value
    if is_machine_searchable_session_id(value):
        return value
    resolved = resolve_session_reference(project_root, value)
    direct = project_root / ".vibeagent" / "sessions" / value
    if resolved != value or (
        is_valid_session_id(value) and direct.is_dir() and not direct.is_symlink()
    ):
        return resolved
    return None


def list_resume_session_candidates(
    project_root: Path,
    query: str | None = None,
    *,
    scan_limit: int = MAX_RESUME_SESSION_SCAN,
    result_limit: int = MAX_RESUME_SESSION_CANDIDATES,
) -> tuple[ResumeSessionCandidate, ...]:
    if scan_limit < 1 or result_limit < 1:
        raise ValueError("Resume session candidate limits must be positive.")
    needle = _validate_search_query(query)
    root = project_root.resolve()
    candidates: list[ResumeSessionCandidate] = []
    for info in list_sessions(root, limit=scan_limit):
        try:
            session_name, task, status = _read_candidate_metadata(root, info.run_id)
        except (OSError, ValueError):
            continue
        candidate = ResumeSessionCandidate(
            run_id=info.run_id,
            session_name=session_name,
            task=compact(task, 240) if task else None,
            status=status,
            last_event_time=info.last_event_time,
        )
        if needle is not None and needle not in candidate.search_text:
            continue
        candidates.append(candidate)
        if len(candidates) >= result_limit:
            break
    return tuple(candidates)


def prompt_resume_session(
    candidates: Sequence[ResumeSessionCandidate],
    *,
    query: str | None = None,
    input_func: Callable[[str], str] | None = None,
    print_func: Callable[[str], None] = print,
) -> str:
    if not candidates:
        if query is None:
            raise ValueError("No local sessions are available to resume.")
        raise ValueError(f"No local sessions match {query!r}.")
    selected = prompt_numbered_choice(
        candidates,
        heading="Local sessions:",
        item_lines=_candidate_lines,
        prompt_label="a session",
        input_func=input_func,
        print_func=print_func,
    )
    return selected.run_id


def rewrite_resume_picker_arguments(argv: Sequence[str], run_id: str) -> list[str]:
    rewritten: list[str] = []
    values = list(argv)
    options = True
    index = 0
    while index < len(values):
        value = values[index]
        if options and value == "--":
            options = False
            rewritten.append(value)
            index += 1
            continue
        if options and value in {"--resume", "-r"}:
            index += 1
            if index < len(values) and values[index] != "--" and not values[index].startswith("-"):
                index += 1
            continue
        if options and value.startswith("--resume="):
            index += 1
            continue
        rewritten.append(value)
        index += 1
    return ["--resume", run_id, *rewritten]


def _candidate_lines(index: int, candidate: ResumeSessionCandidate) -> tuple[str, ...]:
    label = terminal_safe_text(candidate.session_name or candidate.run_id)
    timestamp = (
        candidate.last_event_time.isoformat(timespec="seconds")
        if candidate.last_event_time is not None
        else "unknown"
    )
    first = f"  {index}. {label} [{candidate.status}] - {timestamp}"
    details = [f"     session: {terminal_safe_text(candidate.run_id)}"]
    if candidate.task:
        details.append(f"     task: {terminal_safe_text(candidate.task)}")
    return (first, *details)


def _validate_search_query(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Resume session search query must be non-empty.")
    if len(value) > MAX_RESUME_SEARCH_QUERY_CHARS or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ValueError(
            "Resume session search query is too long or contains control characters."
        )
    query = value.strip()
    if not query:
        raise ValueError("Resume session search query must be non-empty.")
    return query.casefold()


def _read_candidate_metadata(
    project_root: Path,
    run_id: str,
) -> tuple[str | None, str | None, str]:
    path = events_path(project_root, run_id)
    if not path.exists():
        return None, None, "incomplete"
    session_name: str | None = None
    task: str | None = None
    status = "incomplete"
    with path.open("rb") as stream:
        for _index in range(MAX_RESUME_PICKER_EVENTS):
            raw = stream.readline(MAX_RESUME_PICKER_EVENT_BYTES + 1)
            if not raw:
                break
            if len(raw) > MAX_RESUME_PICKER_EVENT_BYTES:
                if not raw.endswith(b"\n"):
                    _discard_line_remainder(stream)
                continue
            try:
                event = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                continue
            event_type = event["type"]
            if event_type == "task" and isinstance(event.get("task"), str):
                task = event["task"]
            elif event_type in {SESSION_BRANCH_EVENT, SESSION_NAMED_EVENT}:
                name = event.get("name")
                if event_type == SESSION_BRANCH_EVENT and name is None:
                    continue
                if event_type == SESSION_NAMED_EVENT and name is None:
                    session_name = None
                    continue
                if not isinstance(name, str):
                    raise ValueError(f"Session {run_id} has malformed name metadata.")
                normalized = normalize_session_name(name)
                if normalized != name:
                    raise ValueError(f"Session {run_id} has malformed name metadata.")
                session_name = normalized
            elif event_type == "result":
                success = event.get("success")
                if success is True:
                    status = (
                        "blocked"
                        if event.get("completion_ready") is False
                        or event.get("status") == "blocked"
                        else "completed"
                    )
                elif success is False:
                    status = "failed"
    return session_name, task, status


def _discard_line_remainder(stream: BinaryIO) -> None:
    while True:
        chunk = stream.readline(MAX_RESUME_PICKER_EVENT_BYTES + 1)
        if not chunk or chunk.endswith(b"\n"):
            return


__all__ = [
    "ResumeSessionCandidate",
    "list_resume_session_candidates",
    "prepare_session_resume",
    "prompt_resume_session",
    "resolve_exact_resume_reference",
    "rewrite_resume_picker_arguments",
]
