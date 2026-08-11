from __future__ import annotations

import json
import shlex

from .builtin_workflow_types import BuiltinModelWorkflow


def build_verify_workflow(argument: str | None) -> BuiltinModelWorkflow:
    goal = parse_verify_goal(argument)
    goal_text = goal or "the behavior affected by the current changes"
    return BuiltinModelWorkflow(
        task="\n".join(
            [
                "Run the built-in application verification workflow.",
                f"Verification goal: {json.dumps(goal_text)}",
                "Inspect git status and changes, project instructions, manifests, commands, and project_skills before choosing how to verify. Prefer an available verify skill or the most specific run-* skill for the affected app or monorepo package, load it with skill, and follow its validated recipe without weakening this evidence contract. If several recipes match, resolve them from touched paths and descriptions instead of combining commands speculatively.",
                "Translate the goal into a short list of concrete, externally observable acceptance criteria. Identify whether each criterion requires a finite CLI command, a background process, an HTTP/API interaction, or browser/UI interaction.",
                "Build or run the narrowest relevant static checks first. Preflight every finite or long-running command with its matching check tool before requesting approval to execute it.",
                "For CLI behavior, run the real entry point with representative inputs and inspect its bounded output and exit status. Do not treat unit tests alone as proof that the application behavior works.",
                "For a service, record existing processes first, start only the required project command with start_command, wait for readiness output, then prove reachability with port_check and exercise the relevant endpoint with http_check or http_fetch. Inspect process output again after the interaction.",
                "For browser/UI behavior, use tool_search and available project skills or MCP tools to find a browser-capable interaction tool. Exercise the actual user flow and inspect rendered evidence. Never open a GUI through a shell command. If no browser-capable tool is available, report the visual and interaction criteria as unverified even when HTTP succeeds.",
                "If verification exposes a defect caused by the current changes, make only the narrow fix needed for the stated goal and rerun every affected criterion. Do not broaden scope or hide a failed or unavailable check.",
                "Stop only processes started by this workflow, using check_stop_process before stop_process. Never stop a process that was already running when verification began.",
                "If files changed, run focused verification and final_review after the last edit. Finish with an evidence table containing criterion, action, observed result, and PASS, FAIL, or UNVERIFIED. Claim completion only when every required criterion is PASS; distinguish tests, HTTP reachability, and actual UI interaction.",
            ]
        ),
        metadata={
            "source": "builtin_command",
            "name": "verify",
            "arguments": argument or "",
            "goal": goal,
        },
    )


def parse_verify_goal(argument: str | None) -> str | None:
    try:
        tokens = shlex.split(argument or "")
    except ValueError as error:
        raise ValueError(f"/verify arguments are invalid: {error}") from error

    goal_parts: list[str] = []
    options = True
    for token in tokens:
        if options and token == "--":
            options = False
        elif options and token.startswith("-"):
            raise ValueError(f"Unknown /verify option: {token}")
        else:
            goal_parts.append(token)
    goal = " ".join(goal_parts).strip() or None
    if goal is not None and (len(goal) > 4_000 or "\x00" in goal):
        raise ValueError("/verify goal must contain at most 4000 characters and no NUL.")
    return goal


__all__ = ["build_verify_workflow", "parse_verify_goal"]
