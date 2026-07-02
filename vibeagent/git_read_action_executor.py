from __future__ import annotations

from .process_runtime import truncate_command_output
from .types import (
    GitBlameAction,
    GitBlameObservation,
    GitDiffAction,
    GitDiffContext,
    GitDiffContextsAction,
    GitDiffContextsObservation,
    GitDiffHunk,
    GitDiffHunksAction,
    GitDiffHunksObservation,
    GitDiffObservation,
    GitLogAction,
    GitLogObservation,
    GitShowAction,
    GitShowObservation,
    Observation,
    ReadFileContextResult,
)
from .workspace import (
    RunWorkspace,
    read_git_blame,
    read_git_diff,
    read_git_diff_hunks,
    read_git_log,
    read_git_show,
    read_project_file_context_result,
)


def execute_git_read_action(workspace: RunWorkspace, action: object) -> Observation | None:
    if isinstance(action, GitDiffAction):
        try:
            result = read_git_diff(workspace, action.path, action.staged)
        except ValueError as error:
            return GitDiffObservation(
                kind="git_diff",
                ok=False,
                diff="",
                path=action.path,
                staged=action.staged,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        diff, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git diff." if result.ok else result.stderr or "git diff failed."
        return GitDiffObservation(
            kind="git_diff",
            ok=result.ok,
            diff=diff,
            path=action.path,
            staged=action.staged,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, GitDiffHunksAction):
        try:
            summary = read_git_diff_hunks(
                workspace,
                action.path,
                action.staged,
                max_hunks=action.max_hunks,
                max_lines_per_hunk=action.max_lines_per_hunk,
            )
            hunks = [GitDiffHunk(**item) for item in summary["hunks"]]
            return GitDiffHunksObservation(
                kind="git_diff_hunks",
                ok=bool(summary["ok"]),
                hunks=hunks,
                total_hunks=int(summary["total_hunks"]),
                truncated=bool(summary["truncated"]),
                path=action.path,
                staged=action.staged,
                message=str(summary["message"]),
            )
        except ValueError as error:
            return GitDiffHunksObservation(
                kind="git_diff_hunks",
                ok=False,
                hunks=[],
                total_hunks=0,
                truncated=False,
                path=action.path,
                staged=action.staged,
                message=str(error),
            )

    if isinstance(action, GitDiffContextsAction):
        try:
            summary = read_git_diff_hunks(
                workspace,
                action.path,
                action.staged,
                max_hunks=action.max_hunks,
                max_lines_per_hunk=1,
            )
            contexts: list[GitDiffContext] = []
            for item in summary["hunks"]:
                hunk = GitDiffHunk(**item)
                try:
                    result = read_project_file_context_result(
                        workspace,
                        hunk.file,
                        line=max(1, hunk.new_start),
                        context_lines=action.context_lines,
                        max_bytes=action.max_bytes_per_context,
                    )
                    context = ReadFileContextResult(
                        path=hunk.file,
                        line=int(result["line"]),
                        context_lines=int(result["context_lines"]),
                        ok=True,
                        content=str(result["content"]),
                        message=f"Read {hunk.file} around diff hunk line {hunk.new_start}.",
                        start_line=int(result["start_line"]),
                        end_line=int(result["end_line"]),
                        line_count=int(result["line_count"]),
                        total_lines=int(result["total_lines"]),
                        target_line_exists=bool(result["target_line_exists"]),
                        truncated=bool(result["truncated"]),
                        max_bytes=int(result["max_bytes"]),
                    )
                except ValueError as error:
                    context = ReadFileContextResult(
                        path=hunk.file,
                        line=max(1, hunk.new_start),
                        context_lines=action.context_lines,
                        ok=False,
                        content="",
                        message=str(error),
                        max_bytes=action.max_bytes_per_context,
                    )
                contexts.append(GitDiffContext(hunk=hunk, context=context))
            return GitDiffContextsObservation(
                kind="git_diff_contexts",
                ok=bool(summary["ok"]),
                contexts=contexts,
                total_hunks=int(summary["total_hunks"]),
                truncated=bool(summary["truncated"]),
                path=action.path,
                staged=action.staged,
                context_lines=action.context_lines,
                message=str(summary["message"]),
            )
        except ValueError as error:
            return GitDiffContextsObservation(
                kind="git_diff_contexts",
                ok=False,
                contexts=[],
                total_hunks=0,
                truncated=False,
                path=action.path,
                staged=action.staged,
                context_lines=action.context_lines,
                message=str(error),
            )

    if isinstance(action, GitLogAction):
        try:
            result = read_git_log(workspace, action.max_count, action.path)
        except ValueError as error:
            return GitLogObservation(
                kind="git_log",
                ok=False,
                log="",
                max_count=action.max_count,
                path=action.path,
                message=str(error),
            )
        message = "Read git log." if result.ok else result.stderr or "git log failed."
        return GitLogObservation(
            kind="git_log",
            ok=result.ok,
            log=result.stdout,
            max_count=action.max_count,
            path=action.path,
            message=message,
        )

    if isinstance(action, GitShowAction):
        try:
            result = read_git_show(workspace, action.rev, action.path)
        except ValueError as error:
            return GitShowObservation(
                kind="git_show",
                ok=False,
                output="",
                rev=action.rev,
                path=action.path,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        output, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git show." if result.ok else result.stderr or "git show failed."
        return GitShowObservation(
            kind="git_show",
            ok=result.ok,
            output=output,
            rev=action.rev,
            path=action.path,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    if isinstance(action, GitBlameAction):
        try:
            result = read_git_blame(workspace, action.path, action.start_line, action.line_count)
        except ValueError as error:
            return GitBlameObservation(
                kind="git_blame",
                ok=False,
                blame="",
                path=action.path,
                start_line=action.start_line,
                line_count=action.line_count,
                truncated=False,
                max_output_chars=action.max_output_chars,
                message=str(error),
            )
        blame, truncated = truncate_command_output(result.stdout, action.max_output_chars)
        message = "Read git blame." if result.ok else result.stderr or "git blame failed."
        return GitBlameObservation(
            kind="git_blame",
            ok=result.ok,
            blame=blame,
            path=action.path,
            start_line=action.start_line,
            line_count=action.line_count,
            truncated=truncated,
            max_output_chars=action.max_output_chars,
            message=message,
        )

    return None
