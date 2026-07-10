from __future__ import annotations

import json
from pathlib import Path

from .agent_result import AgentResult
from .cli_stream_output import JsonEventStream, error_result_payload
from .project_trust import is_project_permissions_trusted, trust_project_permissions
from .session_approval import SessionApprovalHandler
from .types import ApprovalDecision, ApprovalHandler, ApprovalPolicy, ApprovalRequest, UserInputRequest
from .workspace_permissions import read_project_permissions_from_root


def print_output(payload: dict[str, object], output_json: bool) -> None:
    if output_json:
        json_payload = dict(payload)
        if json_payload.get("success") is True and "status" not in json_payload:
            json_payload["status"] = "completed"
        print(json.dumps(json_payload, ensure_ascii=False, sort_keys=True))
        return
    text = payload.get("text") if "text" in payload else payload.get("message")
    print("" if text is None else text)


def print_error_result(
    error: str,
    output_json: bool,
    exit_code: int = 1,
    prefix: bool = False,
    output_format: str | None = None,
) -> int:
    if output_format == "stream-json":
        JsonEventStream().result(error_result_payload(error))
        return exit_code
    if output_json:
        print(json.dumps({"kind": "error", "success": False, "status": "failed", "error": error}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Error: {error}" if prefix else error)
    return exit_code


def print_interrupted_result(output_json: bool, output_format: str | None = None) -> int:
    if output_format == "stream-json":
        JsonEventStream().result(error_result_payload("Interrupted.", kind="interrupted", status="interrupted"))
        return 130
    if output_json:
        print(
            json.dumps(
                {"kind": "interrupted", "success": False, "status": "interrupted", "error": "Interrupted."},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    else:
        print("Interrupted.")
    return 130


def print_agent_result(result: AgentResult) -> None:
    if result.message:
        print(f"\n{result.message}")
    elif not result.success:
        print("\nStopped")
    if result.completion_blockers:
        print("Completion blockers:")
        for blocker in result.completion_blockers:
            print(f"- {blocker}")
    if result.completion_warnings:
        print("Warnings:")
        for warning in result.completion_warnings:
            print(f"- {warning}")
    if result.final_review_changed_files:
        print("Changed files:")
        for path in result.final_review_changed_files:
            print(f"- {path}")
    if result.verification_checks:
        print("Verified:")
        for check in result.verification_checks:
            print(f"- {check}")
    if result.pending_verification_checks:
        print("Pending checks:")
        for check in result.pending_verification_checks:
            print(f"- {check}")
    if result.failed_verification_checks:
        print("Failed checks:")
        for check in result.failed_verification_checks:
            print(f"- {check}")
    if result.latest_completion_final_review_issues:
        print("Latest final review issues:")
        for issue in result.latest_completion_final_review_issues:
            print(f"- {issue}")
    if result.latest_completion_final_review_changed_files:
        print("Latest final review changed files:")
        for path in result.latest_completion_final_review_changed_files:
            print(f"- {path}")
    if result.latest_completion_tool_errors:
        print("Latest tool errors:")
        for error in result.latest_completion_tool_errors:
            print(f"- {error}")
    if result.latest_completion_checkpoint_failures:
        print("Latest checkpoint failures:")
        for failure in result.latest_completion_checkpoint_failures:
            print(f"- {failure}")
    if result.latest_completion_active_background_processes:
        print("Latest active processes:")
        for process in result.latest_completion_active_background_processes:
            print(f"- {process}")
    if result.latest_completion_denied_approvals:
        print("Latest denied approvals:")
        for approval in result.latest_completion_denied_approvals:
            print(f"- {approval}")


def prompt_approval(request: ApprovalRequest) -> ApprovalDecision:
    print(f"Action: {request.action_type}")
    print(f"Target: {request.target}")
    print(f"Risk: {request.risk}")
    if request.preview:
        print(f"Preview: {request.preview}")
    try:
        answer = input("Approve? [y]es/[a]lways for this session/[N]o ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return ApprovalDecision(approved=False, message="Approval prompt interrupted.")

    if answer in {"y", "yes"}:
        return ApprovalDecision(approved=True, message="Approved by user.")
    if answer in {"a", "always"}:
        return ApprovalDecision(
            approved=True,
            message="Approved by user for matching actions in this session.",
            scope="session",
        )
    return ApprovalDecision(approved=False, message="Denied by user.")


def prompt_user_input(request: UserInputRequest) -> str | None:
    print(f"Question: {request.question}")
    for index, option in enumerate(request.options, start=1):
        print(f"  {index}. {option}")
    prompt = "Answer: "
    if request.options:
        prompt = "Choose a number"
        if request.allow_free_text:
            prompt += " or enter another answer"
        prompt += ": "
    while True:
        try:
            answer = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if not answer:
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(request.options):
            return request.options[int(answer) - 1]
        if answer in request.options or request.allow_free_text:
            return answer
        print(f"Enter a number from 1 to {len(request.options)}.")


def prompt_project_permission_trust(root: str | Path) -> bool:
    if is_project_permissions_trusted(root):
        return True
    permissions = read_project_permissions_from_root(root)
    allow_rules = [rule for rule in permissions.rules if rule.effect == "allow"]
    if permissions.error is not None or not allow_rules:
        return False
    print("\nThis project defines permission allow rules that can skip side-effect prompts.")
    print(f"Project: {Path(root).resolve()}")
    for rule in allow_rules:
        print(f"  - {rule.raw} ({rule.source})")
    try:
        answer = input("Trust these permission allow rules for this project? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if answer not in {"y", "yes"}:
        return False
    report = trust_project_permissions(root)
    print(str(report["message"]))
    if report.get("storeError"):
        print(f"Error: {report['storeError']}")
    return bool(report["trusted"])


def handle_approval_command(argument: str | None, current: ApprovalPolicy) -> tuple[ApprovalPolicy, str]:
    if not argument:
        return current, f"Approval policy: {current}"
    requested = argument.strip().lower()
    if requested not in {"ask", "allow", "deny", "plan"}:
        return current, "Usage: /approval [ask|allow|deny|plan]"
    policy = requested
    return policy, f"Approval policy: {policy}"


def build_approval_handler(policy: ApprovalPolicy) -> ApprovalHandler:
    if policy == "allow":
        return lambda request: ApprovalDecision(approved=True, message=f"Approved by policy for {request.action_type}.")
    if policy == "deny":
        return lambda request: ApprovalDecision(approved=False, message=f"Denied by policy for {request.action_type}.")
    if policy == "plan":
        return lambda request: ApprovalDecision(
            approved=False,
            message=f"Denied because Plan mode is read-only: {request.action_type}.",
        )
    return SessionApprovalHandler(prompt_approval)


def format_error(error: Exception) -> str:
    # Expand 401 guidance; otherwise return raw error text.
    if getattr(error, "status", None) == 401:
        return "\n".join(
            [
                str(error),
                "The configured model provider rejected the API key.",
                "Check /model for the active provider and key source.",
                "If you copied a value that starts with 'Bearer ', VibeAgent strips that prefix automatically.",
            ]
        )
    return str(error)
