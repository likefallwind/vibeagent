from __future__ import annotations

from dataclasses import dataclass
import json
import shlex

from .command_types import LocalCommand


CODE_REVIEW_EFFORT_TURNS = {
    "low": 2,
    "medium": 3,
    "high": 4,
    "xhigh": 6,
    "max": 8,
}


@dataclass(frozen=True)
class BuiltinModelWorkflow:
    task: str
    metadata: dict[str, object]


def resolve_builtin_model_workflow(command: LocalCommand | None) -> BuiltinModelWorkflow | None:
    if command is None or command.type != "code_review":
        return None
    return build_code_review_workflow(command.argument)


def build_code_review_workflow(argument: str | None) -> BuiltinModelWorkflow:
    fix, effort, target = parse_code_review_arguments(argument)
    max_iterations = CODE_REVIEW_EFFORT_TURNS.get(effort or "high", 4)
    target_input = f', "target": {json.dumps(target)}' if target is not None else ""
    steps = [
        "Run the built-in local code review workflow.",
        (
            "You must call deep_review exactly once with all three perspectives and "
            f'{{"max_iterations": {max_iterations}{target_input}}}. Do not substitute review_changes or final_review.'
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


__all__ = [
    "BuiltinModelWorkflow",
    "CODE_REVIEW_EFFORT_TURNS",
    "build_code_review_workflow",
    "parse_code_review_arguments",
    "resolve_builtin_model_workflow",
]
