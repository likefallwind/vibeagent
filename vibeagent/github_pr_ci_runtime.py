from __future__ import annotations

import re
import shutil
from typing import Any

from .github_pr_context_runtime import (
    normalize_pr_selector,
    run_gh_json,
    run_gh_output,
    select_local_github_repository,
)
from .redaction import redact_sensitive_text
from .workspace_core import RunWorkspace
from .workspace_git_utils import redact_git_text


MAX_FAILED_CHECKS = 100
MAX_CI_RUNS = 10
MIN_LOG_CHARS = 1_000
MAX_LOG_CHARS = 100_000
DEFAULT_LOG_CHARS = 30_000
_CHECK_FIELDS = "bucket,link,name,state,workflow"


def read_github_pr_ci_logs(
    workspace: RunWorkspace,
    *,
    pr: str | None = None,
    remote: str | None = None,
    max_runs: int = 3,
    max_output_chars: int = DEFAULT_LOG_CHARS,
) -> dict[str, Any]:
    repository, error = select_local_github_repository(workspace, remote)
    if error:
        return _failure(error)
    selector, error = normalize_pr_selector(workspace, pr)
    if error:
        return _failure(error, repository=repository)
    if not 1 <= max_runs <= MAX_CI_RUNS:
        return _failure(f"max_runs must be between 1 and {MAX_CI_RUNS}.", repository=repository)
    if not MIN_LOG_CHARS <= max_output_chars <= MAX_LOG_CHARS:
        return _failure(
            f"max_output_chars must be between {MIN_LOG_CHARS} and {MAX_LOG_CHARS}.",
            repository=repository,
        )
    executable = shutil.which("gh")
    if executable is None:
        return _failure("GitHub CLI executable 'gh' was not found.", repository=repository)

    command = [executable, "pr", "checks"]
    if selector:
        command.append(selector)
    command.extend(["--repo", repository, "--json", _CHECK_FIELDS])
    payload, error = run_gh_json(
        command,
        workspace.root,
        accepted_returncodes=frozenset({0, 1, 8}),
    )
    if error:
        return _failure(error, repository=repository)
    if not isinstance(payload, list):
        return _failure("gh pr checks returned a JSON value that was not an array.", repository=repository)

    all_failed = [item for item in payload if isinstance(item, dict) and str(item.get("bucket", "")).lower() == "fail"]
    failed_source = all_failed[:MAX_FAILED_CHECKS]
    failed_checks = [_failed_check(item, repository) for item in failed_source]
    run_groups: dict[str, dict[str, Any]] = {}
    for check in failed_checks:
        run_id = str(check["run_id"])
        if not run_id:
            continue
        group = run_groups.setdefault(
            run_id,
            {"run_id": run_id, "url": str(check["link"]), "check_names": []},
        )
        group["check_names"].append(str(check["name"]))

    runs: list[dict[str, Any]] = []
    for group in list(run_groups.values())[:max_runs]:
        log_command = [
            executable,
            "run",
            "view",
            str(group["run_id"]),
            "--repo",
            repository,
            "--log-failed",
        ]
        stdout, stderr, returncode, command_error = run_gh_output(log_command, workspace.root)
        if command_error:
            logs = ""
            log_error = command_error
            truncated = False
        elif returncode != 0:
            logs = ""
            log_error = redact_git_text(stderr or stdout or "gh run view --log-failed failed.")[:4_000]
            truncated = False
        else:
            logs, truncated = _clip_log(redact_sensitive_text(stdout), max_output_chars)
            log_error = ""
        runs.append({**group, "logs": logs, "logs_truncated": truncated, "error": log_error})

    return {
        "ok": True,
        "repository": repository,
        "selector": selector or "current branch",
        "failed_checks": failed_checks,
        "failed_total": len(all_failed),
        "failed_truncated": len(all_failed) > MAX_FAILED_CHECKS,
        "runs": runs,
        "runs_total": len(run_groups),
        "runs_truncated": len(run_groups) > max_runs,
        "message": (
            f"Read {len(failed_checks)} failed check(s) and failed-step logs for "
            f"{len(runs)}/{len(run_groups)} GitHub Actions run(s)."
        ),
    }


def _failed_check(item: dict[str, Any], repository: str) -> dict[str, str]:
    link = str(item.get("link", ""))[:2_000]
    return {
        "name": str(item.get("name", ""))[:500],
        "state": str(item.get("state", ""))[:100],
        "workflow": str(item.get("workflow", ""))[:500],
        "link": link,
        "run_id": _actions_run_id(link, repository),
    }


def _actions_run_id(link: str, repository: str) -> str:
    owner, name = (re.escape(part) for part in repository.split("/", 1))
    pattern = re.compile(
        rf"^https://github\.com/{owner}/{name}/actions/runs/([1-9][0-9]*)(?:/.*)?$",
        re.IGNORECASE,
    )
    match = pattern.fullmatch(link)
    return match.group(1) if match else ""


def _clip_log(value: str, maximum: int) -> tuple[str, bool]:
    if len(value) <= maximum:
        return value, False
    head = maximum // 2
    tail = maximum - head
    marker = "\n[CI log truncated: middle omitted]\n"
    return value[: max(0, head - len(marker))] + marker + value[-tail:], True


def _failure(message: str, *, repository: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "repository": repository,
        "selector": "",
        "failed_checks": [],
        "failed_total": 0,
        "failed_truncated": False,
        "runs": [],
        "runs_total": 0,
        "runs_truncated": False,
        "message": message,
    }
