from __future__ import annotations

import json

from .builtin_workflow_types import BuiltinModelWorkflow


def build_batch_workflow(argument: str | None) -> BuiltinModelWorkflow:
    instruction = parse_batch_instruction(argument)
    return BuiltinModelWorkflow(
        task="\n".join(
            [
                "Run the built-in large-scale parallel coding workflow.",
                f"User batch instruction: {json.dumps(instruction)}",
                "First verify this is a Git repository with an origin remote and a clean parent worktree. Stop with a concrete reason if any prerequisite is missing.",
                "Research the repository, its instructions, architecture, tests, and affected ownership boundaries. You may use up to four parallel read-only delegate_task calls for research.",
                "Decompose the instruction into 5 to 30 genuinely independent implementation units. Do not pad the count; if fewer than five disjoint units are justified, stop and recommend the normal coding workflow.",
                "For every unit specify a unique short ID, exact non-overlapping owned paths, implementation objective, acceptance checks, and why it can be completed from the current HEAD without another unit.",
                "Present the complete unit plan with risks, then call ask_user with Approve and launch, Revise plan, and Cancel choices. Do not edit files, create worktrees or branches, start coding agents, push, or open pull requests before explicit approval.",
                "Plan approval authorizes orchestration only. It does not change the active approval policy or grant file, command, Git, network, push, or pull-request permissions; every delegated side effect remains normally approval-gated.",
                "If revision is requested, incorporate the feedback and ask again. If cancelled, finish without side effects.",
                "After approval, create one TaskCreate record per unit and launch exactly one background delegate_task for each unit with mode=code and isolation=worktree. Start all units before waiting for results.",
                "Each delegated task must stay inside its owned paths, obey project instructions, implement only its unit, run its acceptance checks, review its diff, commit the changes, push its isolated branch, and use check_github_pr_create then github_pr_create to open a pull request against the repository default branch. Use tool_search first when those GitHub tools are not visible.",
                "Collect every agent with TaskOutput, update task status honestly, and never silently replace a failed unit in the parent checkout. Report each unit's branch, worktree, checks, commit, pull request URL, or exact failure; include a final total of succeeded and failed units.",
            ]
        ),
        metadata={
            "source": "builtin_command",
            "name": "batch",
            "arguments": argument or "",
            "instruction": instruction,
            "interactive_only": True,
        },
    )


def parse_batch_instruction(argument: str | None) -> str:
    instruction = (argument or "").strip()
    if not instruction:
        raise ValueError("/batch requires an implementation instruction.")
    if len(instruction) > 4_000 or "\x00" in instruction:
        raise ValueError("/batch instruction must contain at most 4000 characters and no NUL.")
    return instruction


__all__ = ["build_batch_workflow", "parse_batch_instruction"]
