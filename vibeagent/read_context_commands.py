from __future__ import annotations

from pathlib import Path

from .actions import execute_action
from .local_command_workspace import local_command_workspace
from .read_command_failures import (
    AROUND_MANY_USAGE,
    AROUND_USAGE,
    around_failure_report,
    around_many_failure_report,
    usage_error,
)
from .read_command_parsing import (
    parse_around_many_argument,
    parse_around_request,
    serialize_context_result,
)
from .types import ReadFileContextAction, ReadFileContextsAction


def get_around_report(
    project_root: str | Path = ".",
    argument: str | None = None,
    context_lines: int | None = None,
    max_bytes: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    try:
        path, line, selected_context = parse_around_request(argument, context_lines)
    except ValueError as error:
        return around_failure_report(
            root,
            usage_error(AROUND_USAGE, error),
            context_lines=context_lines,
            max_bytes=max_bytes,
        )
    if path is None or line is None:
        return around_failure_report(
            root,
            AROUND_USAGE,
            context_lines=context_lines,
            max_bytes=max_bytes,
        )

    workspace = local_command_workspace(root, "local-around")
    observation = execute_action(
        workspace,
        ReadFileContextAction(
            type="read_file_context",
            path=path,
            line=line,
            context_lines=selected_context,
            max_bytes=max_bytes,
        ),
    )
    if observation.kind != "read_file_context":
        return around_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            path=path,
            line=line,
            context_lines=selected_context,
            max_bytes=max_bytes,
        )
    context = serialize_context_result(observation)
    return {
        "projectRoot": str(root),
        "ok": observation.ok,
        "path": observation.path,
        "line": observation.line,
        "context": {key: value for key, value in context.items() if key not in {"path", "line", "ok"}},
        "message": observation.message,
    }


def get_around_many_report(
    project_root: str | Path = ".",
    argument: str | list[str] | None = None,
    max_bytes_per_context: int = 20_000,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if max_bytes_per_context < 1_000:
        return around_many_failure_report(
            root,
            usage_error(AROUND_MANY_USAGE, "max_bytes_per_context must be at least 1000."),
            max_bytes_per_context=max_bytes_per_context,
        )
    if max_bytes_per_context > 200_000:
        return around_many_failure_report(
            root,
            usage_error(AROUND_MANY_USAGE, "max_bytes_per_context must be at most 200000."),
            max_bytes_per_context=max_bytes_per_context,
        )
    try:
        contexts = parse_around_many_argument(argument)
    except ValueError as error:
        return around_many_failure_report(
            root,
            usage_error(AROUND_MANY_USAGE, error),
            max_bytes_per_context=max_bytes_per_context,
        )
    if not contexts:
        return around_many_failure_report(
            root,
            AROUND_MANY_USAGE,
            max_bytes_per_context=max_bytes_per_context,
        )

    workspace = local_command_workspace(root, "local-around-many")
    observation = execute_action(
        workspace,
        ReadFileContextsAction(
            type="read_file_contexts",
            contexts=contexts,
            max_bytes_per_context=max_bytes_per_context,
        ),
    )
    if observation.kind != "read_file_contexts":
        return around_many_failure_report(
            root,
            f"Unexpected observation: {observation.kind}",
            total=len(contexts),
            max_bytes_per_context=max_bytes_per_context,
        )

    items = [serialize_context_result(item) for item in observation.contexts]
    ok_count = sum(1 for item in items if item["ok"])
    return {
        "projectRoot": str(root),
        "ok": ok_count == len(items),
        "contexts": {"ok": ok_count, "total": len(items), "items": items},
        "maxBytesPerContext": max_bytes_per_context,
        "message": observation.message,
    }
