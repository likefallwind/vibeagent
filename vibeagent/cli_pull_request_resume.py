from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
import sys

from .cli_config import resolve_project_root
from .cli_numbered_picker import prompt_numbered_choice
from .session_pull_requests import (
    PullRequestSessionCandidate,
    list_pull_request_session_candidates,
    resolve_session_from_pull_request,
)


def prepare_pull_request_resume(
    args: argparse.Namespace,
    *,
    input_func: Callable[[str], str] | None = None,
    print_func: Callable[[str], None] = print,
    terminal_available: bool | None = None,
) -> None:
    selector = getattr(args, "from_pr", None)
    if selector is None:
        return
    if args.resume is not None or args.session_id is not None or args.compact is not None or args.continue_latest:
        raise ValueError("--from-pr cannot be combined with --resume, --session-id, --compact, or --continue.")
    root = resolve_project_root(args.cwd) or Path.cwd().resolve()
    if _is_exact_pull_request_selector(selector):
        args.resume = resolve_session_from_pull_request(root, selector)
        args.resume_from_pull_request = True
        return
    if terminal_available is None:
        terminal_available = sys.stdin.isatty() and sys.stdout.isatty()
    if not terminal_available or args.json or args.output_format != "text":
        raise ValueError("--from-pr without an exact PR number or URL requires an interactive text terminal.")
    query = selector.strip() or None
    candidates = list_pull_request_session_candidates(root, query)
    args.resume = prompt_pull_request_session(
        candidates,
        query=query,
        input_func=input_func,
        print_func=print_func,
    )
    args.resume_from_pull_request = True


def prompt_pull_request_session(
    candidates: tuple[PullRequestSessionCandidate, ...],
    *,
    query: str | None = None,
    input_func: Callable[[str], str] | None = None,
    print_func: Callable[[str], None] = print,
) -> str:
    if not candidates:
        if query is None:
            raise ValueError("No local sessions are linked to pull requests.")
        raise ValueError(f"No local pull request sessions match {query!r}.")
    selected = prompt_numbered_choice(
        candidates,
        heading="Local pull request sessions:",
        item_lines=_candidate_lines,
        prompt_label="a pull request",
        input_func=input_func,
        print_func=print_func,
    )
    return selected.run_id


def _candidate_lines(
    index: int,
    candidate: PullRequestSessionCandidate,
) -> tuple[str, str]:
    link = candidate.pull_request
    label = candidate.session_name or candidate.run_id
    return (
        f"  {index}. {link.repository} #{link.number} [{link.provider}] - {label}",
        f"     {link.url}",
    )


def _is_exact_pull_request_selector(value: str) -> bool:
    selector = value.strip()
    return bool(selector) and (
        (selector.isascii() and selector.isdigit())
        or "://" in selector
    )


__all__ = ["prepare_pull_request_resume", "prompt_pull_request_session"]
