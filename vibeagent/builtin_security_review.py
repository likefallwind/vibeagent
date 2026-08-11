from __future__ import annotations

import json

from .builtin_workflow_types import BuiltinModelWorkflow
from .review_profiles import SECURITY_REVIEW_PERSPECTIVES


def build_security_review_workflow(argument: str | None) -> BuiltinModelWorkflow:
    parse_security_review_arguments(argument)
    perspectives = json.dumps(list(SECURITY_REVIEW_PERSPECTIVES))
    return BuiltinModelWorkflow(
        task="\n".join(
            [
                "Run the built-in read-only branch security review.",
                "Use git_info first. Require a Git repository with an origin remote, then use git_show on origin/HEAD to verify the cached origin default-branch ref. If either prerequisite is missing, stop with a concrete setup error; do not fetch or guess another base.",
                (
                    "Call deep_review exactly once with the security profile and all four perspectives: "
                    f'{{"review_kind": "security", "perspectives": {perspectives}, '
                    '"max_iterations": 4, "base_ref": "origin/HEAD"}.'
                ),
                "Treat the verified deep_review summary as the authoritative vulnerability list; do not promote unverified candidate reports.",
                "This workflow is strictly read-only. Do not edit, stage, commit, push, post comments, run project commands, or apply fixes.",
                "Report each verified vulnerability with severity, attacker capability, exploit path, affected asset, impact, and file:line evidence. If none survive verification, state that no vulnerabilities were verified.",
            ]
        ),
        metadata={
            "source": "builtin_command",
            "name": "security-review",
            "arguments": argument or "",
            "base_ref": "origin/HEAD",
        },
    )


def parse_security_review_arguments(argument: str | None) -> None:
    if argument is not None and argument.strip():
        raise ValueError("/security-review does not accept arguments; it reviews the current branch against origin/HEAD.")


__all__ = ["build_security_review_workflow", "parse_security_review_arguments"]
