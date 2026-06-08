from __future__ import annotations

from .agent import AgentResult, run_agent
from .chat import run_chat
from .commands import (
    get_help_text,
    get_last_session_text,
    get_model_text,
    get_resume_context,
    get_session_text,
    get_sessions_text,
    parse_local_command,
)
from .providers import create_chat_client
from .types import ApprovalDecision, ApprovalHandler, ApprovalPolicy, ApprovalRequest, ChatMessage


def main() -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print("VibeAgent v0.1")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")

    client = None
    mode = "code"
    approval_policy: ApprovalPolicy = "ask"
    chat_history: list[ChatMessage] = []
    resume_context: str | None = None
    while True:
        try:
            task = input("\nvibeagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not task:
            continue

        command = parse_local_command(task)
        if command and command.type == "exit":
            return 0
        if command and command.type == "help":
            print(get_help_text())
            continue
        if command and command.type == "model":
            print(get_model_text())
            continue
        if command and command.type == "approval":
            approval_policy, text = handle_approval_command(command.argument, approval_policy)
            print(text)
            continue
        if command and command.type == "sessions":
            print(get_sessions_text())
            continue
        if command and command.type == "session":
            print(get_session_text(command.argument))
            continue
        if command and command.type == "last":
            print(get_last_session_text())
            continue
        if command and command.type == "resume":
            _, context, text = get_resume_context(command.argument)
            resume_context = context
            print(text)
            continue
        request_mode = mode
        if command and command.type == "chat":
            if not command.argument:
                mode = "chat"
                print("Chat mode. Use /code to switch back to coding mode.")
                continue
            task = command.argument
            request_mode = "chat"
        elif command and command.type == "code":
            if not command.argument:
                mode = "code"
                print("Coding mode. Use /chat to switch to daily conversation mode.")
                continue
            task = command.argument
            request_mode = "code"

        try:
            # Reuse client across turns so auth/model config is loaded once.
            client = client or create_chat_client()
            if request_mode == "chat":
                response = run_chat(task, client=client, history=chat_history)
                chat_history.extend(
                    [
                        ChatMessage(role="user", content=task),
                        ChatMessage(role="assistant", content=response),
                    ]
                )
                print(f"\n{response}")
                continue

            result = run_agent(
                task,
                client=client,
                approval_handler=build_approval_handler(approval_policy),
                prior_context=resume_context,
            )
            print_agent_result(result)
            _, next_context, _ = get_resume_context(result.run_id)
            if next_context:
                resume_context = next_context
        except Exception as error:
            print(f"\nError: {format_error(error)}")


def print_agent_result(result: AgentResult) -> None:
    if result.message:
        print(f"\n{result.message}")
    elif not result.success:
        print("\nStopped")


def prompt_approval(request: ApprovalRequest) -> ApprovalDecision:
    print(f"Action: {request.action_type}")
    print(f"Target: {request.target}")
    print(f"Risk: {request.risk}")
    try:
        answer = input("Approve? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return ApprovalDecision(approved=False, message="Approval prompt interrupted.")

    if answer in {"y", "yes"}:
        return ApprovalDecision(approved=True, message="Approved by user.")
    return ApprovalDecision(approved=False, message="Denied by user.")


def handle_approval_command(argument: str | None, current: ApprovalPolicy) -> tuple[ApprovalPolicy, str]:
    if not argument:
        return current, f"Approval policy: {current}"
    requested = argument.strip().lower()
    if requested not in {"ask", "allow", "deny"}:
        return current, "Usage: /approval [ask|allow|deny]"
    policy = requested
    return policy, f"Approval policy: {policy}"


def build_approval_handler(policy: ApprovalPolicy) -> ApprovalHandler:
    if policy == "allow":
        return lambda request: ApprovalDecision(approved=True, message=f"Approved by policy for {request.action_type}.")
    if policy == "deny":
        return lambda request: ApprovalDecision(approved=False, message=f"Denied by policy for {request.action_type}.")
    return prompt_approval


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


if __name__ == "__main__":
    raise SystemExit(main())
