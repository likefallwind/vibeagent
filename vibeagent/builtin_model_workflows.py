from __future__ import annotations

import json
import shlex

from .builtin_batch_workflow import build_batch_workflow, parse_batch_instruction
from .builtin_workflow_types import BuiltinModelWorkflow
from .command_types import LocalCommand
from .review_profiles import CLEANUP_REVIEW_PERSPECTIVES, DEFECT_REVIEW_PERSPECTIVES


CODE_REVIEW_EFFORT_TURNS = {
    "low": 2,
    "medium": 3,
    "high": 4,
    "xhigh": 6,
    "max": 8,
}


def resolve_builtin_model_workflow(
    command: LocalCommand | None,
    *,
    interactive: bool = True,
) -> BuiltinModelWorkflow | None:
    if command is None:
        return None
    if command.type == "code_review":
        return build_code_review_workflow(command.argument)
    if command.type == "simplify":
        return build_simplify_workflow(command.argument)
    if command.type == "batch":
        if not interactive:
            raise ValueError("/batch requires an interactive session so the execution plan can be approved.")
        return build_batch_workflow(command.argument)
    return None


def build_code_review_workflow(argument: str | None) -> BuiltinModelWorkflow:
    fix, effort, target = parse_code_review_arguments(argument)
    max_iterations = CODE_REVIEW_EFFORT_TURNS.get(effort or "high", 4)
    target_input = f', "target": {json.dumps(target)}' if target is not None else ""
    perspectives = json.dumps(list(DEFECT_REVIEW_PERSPECTIVES))
    steps = [
        "Run the built-in local code review workflow.",
        (
            "You must call deep_review exactly once with all three perspectives and "
            f'{{"review_kind": "defects", "perspectives": {perspectives}, '
            f'"max_iterations": {max_iterations}{target_input}}}. Do not substitute review_changes or final_review.'
        ),
        "Treat the verified deep_review summary as the authoritative findings list; do not promote unverified candidate reports.",
    ]
    if fix:
        steps.extend(
            [
                "After the review, inspect every verified finding and fix justified issues introduced by the reviewed changes.",
                "Do not modify pre-existing findings unless required for a safe fix. Run focused verification and final_review after edits.",
                "Report each verified finding as fixed, skipped with reason, or no change needed.",
            ]
        )
    else:
        steps.extend(
            [
                "This is a read-only review: do not edit, stage, commit, push, or post comments.",
                "Return the verified findings with severity and file:line evidence, or state that no findings survived verification.",
            ]
        )
    return BuiltinModelWorkflow(
        task="\n".join(steps),
        metadata={
            "source": "builtin_command",
            "name": "code-review",
            "arguments": argument or "",
            "fix": fix,
            "effort": effort,
            "target": target,
        },
    )


def build_simplify_workflow(argument: str | None) -> BuiltinModelWorkflow:
    target = parse_simplify_arguments(argument)
    target_input = f', "target": {json.dumps(target)}' if target is not None else ""
    perspectives = json.dumps(list(CLEANUP_REVIEW_PERSPECTIVES))
    return BuiltinModelWorkflow(
        task="\n".join(
            [
                "Run the built-in behavior-preserving code simplification workflow.",
                (
                    "You must call deep_review exactly once with the cleanup profile and all four perspectives: "
                    f'{{"review_kind": "cleanup", "perspectives": {perspectives}, '
                    f'"max_iterations": 4{target_input}}}. Do not substitute correctness review or final_review.'
                ),
                "Treat the verified deep_review summary as the authoritative cleanup list; do not promote unverified candidate reports.",
                "Inspect and apply every justified behavior-preserving cleanup. Do not change public behavior or fix unrelated correctness bugs.",
                "Skip any finding whose replacement is not clearly simpler, more reusable, more efficient, or better placed in this repository.",
                "Run focused verification and final_review after edits, then report each verified cleanup as applied or skipped with reason.",
            ]
        ),
        metadata={
            "source": "builtin_command",
            "name": "simplify",
            "arguments": argument or "",
            "target": target,
        },
    )


def parse_code_review_arguments(argument: str | None) -> tuple[bool, str | None, str | None]:
    try:
        tokens = shlex.split(argument or "")
    except ValueError as error:
        raise ValueError(f"/code-review arguments are invalid: {error}") from error

    fix = False
    effort: str | None = None
    target_parts: list[str] = []
    options = True
    for token in tokens:
        if options and token == "--":
            options = False
        elif options and token == "--fix":
            if fix:
                raise ValueError("/code-review accepts --fix at most once.")
            fix = True
        elif options and token == "--comment":
            raise ValueError("/code-review --comment is not supported yet; no GitHub comment was posted.")
        elif options and token == "ultra":
            raise ValueError("/code-review ultra requires a cloud review service and is not supported.")
        elif options and token in CODE_REVIEW_EFFORT_TURNS and effort is None and not target_parts:
            effort = token
        elif options and token.startswith("-"):
            raise ValueError(f"Unknown /code-review option: {token}")
        else:
            target_parts.append(token)

    target = " ".join(target_parts).strip() or None
    if target is not None and (len(target) > 1_000 or "\x00" in target):
        raise ValueError("/code-review target must contain at most 1000 characters and no NUL.")
    return fix, effort, target


def parse_simplify_arguments(argument: str | None) -> str | None:
    try:
        tokens = shlex.split(argument or "")
    except ValueError as error:
        raise ValueError(f"/simplify arguments are invalid: {error}") from error

    target_parts: list[str] = []
    options = True
    for token in tokens:
        if options and token == "--":
            options = False
        elif options and token.startswith("-"):
            raise ValueError(f"Unknown /simplify option: {token}")
        else:
            target_parts.append(token)
    target = " ".join(target_parts).strip() or None
    if target is not None and (len(target) > 1_000 or "\x00" in target):
        raise ValueError("/simplify target must contain at most 1000 characters and no NUL.")
    return target


__all__ = [
    "BuiltinModelWorkflow",
    "CODE_REVIEW_EFFORT_TURNS",
    "build_batch_workflow",
    "build_code_review_workflow",
    "build_simplify_workflow",
    "parse_code_review_arguments",
    "parse_batch_instruction",
    "parse_simplify_arguments",
    "resolve_builtin_model_workflow",
]
