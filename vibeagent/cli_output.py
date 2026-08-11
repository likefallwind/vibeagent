from __future__ import annotations

import json
from pathlib import Path

from .agent_result import AgentResult
from .cli_result_payloads import error_result_payload
from .cli_stream_output import JsonEventStream
from .project_trust import is_project_permissions_trusted, trust_project_permissions
from .session_approval import SessionApprovalHandler
from .types import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalPolicy,
    ApprovalRequest,
    UserInputAnswer,
    UserInputRequest,
)
from .workspace_permissions import read_project_permissions_from_root, safe_permission_rule_text


MAX_SHOWN_PERMISSION_TRUST_RULES = 20


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
        JsonEventStream().result(error_result_payload(error, exit_code=exit_code))
        return exit_code
    if output_json:
        print(json.dumps(error_result_payload(error, exit_code=exit_code), ensure_ascii=False, sort_keys=True))
    else:
        print(f"Error: {error}" if prefix else error)
    return exit_code


def print_interrupted_result(output_json: bool, output_format: str | None = None) -> int:
    if output_format == "stream-json":
        JsonEventStream().result(
            error_result_payload("Interrupted.", kind="interrupted", status="interrupted", exit_code=130)
        )
        return 130
    if output_json:
        print(
            json.dumps(
                error_result_payload("Interrupted.", kind="interrupted", status="interrupted", exit_code=130),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    else:
        print("Interrupted.")
    return 130


def print_agent_result(result: AgentResult, *, message_already_displayed: bool = False) -> None:
    if result.displayed_message:
        if not message_already_displayed:
            print(f"\n{result.displayed_message}")
    elif not result.success:
        print("\nStopped")
    print_item_section("Completion blockers:", result.completion_blockers)
    print_item_section("Warnings:", result.completion_warnings)
    print_item_section("Hook messages:", result.hook_system_messages)
    print_item_section("Changed files:", result.final_review_changed_files)
    print_item_section("Verified:", result.verification_checks)
    print_item_section("Pending checks:", result.pending_verification_checks)
    print_item_section("Failed checks:", result.failed_verification_checks)
    print_item_section("Latest completion blockers:", result.latest_completion_blockers)
    print_item_section("Latest completion pending checks:", result.latest_completion_pending_verification_checks)
    print_item_section("Latest completion failed checks:", result.latest_completion_failed_verification_checks)
    print_item_section("Latest final review issues:", result.latest_completion_final_review_issues)
    print_item_section("Latest final review changed files:", result.latest_completion_final_review_changed_files)
    print_item_section("Latest tool errors:", result.latest_completion_tool_errors)
    print_item_section("Latest checkpoint failures:", result.latest_completion_checkpoint_failures)
    print_item_section("Latest active processes:", result.latest_completion_active_background_processes)
    print_item_section("Latest denied approvals:", result.latest_completion_denied_approvals)
    print_item_section("Latest next actions:", result.latest_completion_next_actions)


def print_item_section(title: str, items: list[str]) -> None:
    if not items:
        return
    print(title)
    for item in items:
        print(f"- {item}")


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


def prompt_user_input(request: UserInputRequest) -> UserInputAnswer | None:
    prefix = f"[{request.header}] " if request.header else "Question: "
    print(f"{prefix}{request.question}")
    for index, option in enumerate(request.options, start=1):
        print(f"  {index}. {option}")
        description = (request.option_descriptions or {}).get(option)
        if description:
            print(f"     {description}")
    prompt = "Answer: "
    if request.options:
        prompt = "Choose one or more numbers separated by commas" if request.multi_select else "Choose a number"
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
        selections = _numbered_user_input_selections(answer, request)
        if selections is not None:
            return selections if request.multi_select else selections[0]
        if answer in request.options or request.allow_free_text:
            return answer
        suffix = " separated by commas" if request.multi_select else ""
        print(f"Enter valid numbers from 1 to {len(request.options)}{suffix}.")


def _numbered_user_input_selections(
    answer: str,
    request: UserInputRequest,
) -> list[str] | None:
    parts = [part.strip() for part in answer.split(",")]
    if not parts or any(not part.isdigit() for part in parts):
        return None
    indexes = [int(part) for part in parts]
    if (
        any(index < 1 or index > len(request.options) for index in indexes)
        or len(set(indexes)) != len(indexes)
        or (not request.multi_select and len(indexes) != 1)
    ):
        return None
    return [request.options[index - 1] for index in indexes]


def prompt_project_permission_trust(root: str | Path) -> bool:
    if is_project_permissions_trusted(root):
        return True
    permissions = read_project_permissions_from_root(root)
    allow_rules = [rule for rule in permissions.rules if rule.effect == "allow"]
    if permissions.error is not None or not allow_rules:
        return False
    print("\nThis project defines permission allow rules that can skip side-effect prompts.")
    print(f"Project: {Path(root).resolve()}")
    for rule in allow_rules[:MAX_SHOWN_PERMISSION_TRUST_RULES]:
        print(f"  - {safe_permission_rule_text(rule)} ({rule.source})")
    hidden_rules = len(allow_rules) - MAX_SHOWN_PERMISSION_TRUST_RULES
    if hidden_rules > 0:
        print(f"  ... {hidden_rules} more allow rule(s) not shown.")
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
    policies: dict[str, ApprovalPolicy] = {
        "ask": "ask",
        "allow": "allow",
        "auto": "auto",
        "deny": "deny",
        "dontask": "dontAsk",
        "plan": "plan",
    }
    if requested not in policies:
        return current, "Usage: /approval [ask|allow|auto|deny|dontAsk|plan]"
    policy = policies[requested]
    return policy, f"Approval policy: {policy}"


def build_approval_handler(policy: ApprovalPolicy) -> ApprovalHandler:
    if policy == "allow":
        return lambda request: ApprovalDecision(approved=True, message=f"Approved by policy for {request.action_type}.")
    if policy == "deny":
        return lambda request: ApprovalDecision(approved=False, message=f"Denied by policy for {request.action_type}.")
    if policy == "dontAsk":
        return lambda request: ApprovalDecision(
            approved=False,
            message=f"Denied because dontAsk mode does not prompt for {request.action_type}.",
        )
    if policy == "plan":
        return PlanSessionApprovalHandler()
    return SessionApprovalHandler(prompt_approval)


class PlanSessionApprovalHandler:
    def __init__(self) -> None:
        self.mode: ApprovalPolicy = "plan"
        self._session = SessionApprovalHandler(prompt_approval)

    def __call__(self, request: ApprovalRequest) -> ApprovalDecision:
        if self.mode == "plan":
            if request.action_type != "exit_plan_mode":
                return ApprovalDecision(
                    approved=False,
                    message=(
                        f"Denied because Plan mode is read-only: "
                        f"{request.action_type}."
                    ),
                )
            decision = prompt_plan_approval(request)
            if decision.approved:
                self.mode = decision.permission_mode or "ask"
            return decision
        if self.mode == "allow":
            return ApprovalDecision(
                approved=True,
                message=f"Approved by session policy for {request.action_type}.",
            )
        return self._session(request)

    def needs_prompt(self, request: ApprovalRequest) -> bool:
        if self.mode == "allow":
            return False
        if self.mode == "plan":
            return request.action_type == "exit_plan_mode"
        return self._session.needs_prompt(request)


def prompt_plan_approval(request: ApprovalRequest) -> ApprovalDecision:
    print(f"Plan: {request.target}")
    print(f"Risk: {request.risk}")
    try:
        answer = input(
            "Proceed? [y]es, review each action/[a]llow actions/"
            "[p] keep planning/[N]o "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return ApprovalDecision(
            approved=False,
            message="Plan approval prompt interrupted; continue planning.",
            permission_mode="plan",
        )

    if answer in {"y", "yes"}:
        return ApprovalDecision(
            approved=True,
            message="Plan approved; review each action.",
            permission_mode="ask",
        )
    if answer in {"a", "allow", "all"}:
        return ApprovalDecision(
            approved=True,
            message="Plan approved; allow subsequent actions.",
            permission_mode="allow",
        )
    return ApprovalDecision(
        approved=False,
        message="Plan not approved; continue planning.",
        permission_mode="plan",
    )


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
