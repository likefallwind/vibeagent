from __future__ import annotations

from .agent import run_agent
from .chat import run_chat
from .commands import get_help_text, get_model_text, parse_local_command
from .providers import create_chat_client
from .types import AgentStatus, ApprovalDecision, ApprovalRequest, ChatMessage, Observation, TaskStep


def main() -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print("VibeAgent v0.1")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")

    client = None
    mode = "code"
    chat_history: list[ChatMessage] = []
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

            result = run_agent(task, client=client, logger=log_status, approval_handler=prompt_approval)

            print("\nSuccess" if result.success else "\nStopped")
            print(result.message)
            print(f"Project directory: {result.run_dir}")
            print(f"Iterations: {result.iterations}")
            print_task_steps(result.steps)
            print_command_summary(result.observations)
        except Exception as error:
            print(f"\nError: {format_error(error)}")


def log_status(status: AgentStatus, detail: str | None = None) -> None:
    # One-line status line keeps the interactive session legible during each iteration.
    print(f"[{status}]{' ' + detail if detail else ''}")


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


def print_task_steps(steps: list[TaskStep]) -> None:
    if not steps:
        return

    print("Steps:")
    for step in steps:
        detail = f" - {step.message}" if step.message else ""
        print(f"- {step.status}: {step.label}{detail}")


def print_command_summary(observations: list[Observation]) -> None:
    # Show only command runs with compact output for quick debugging in the terminal.
    command_observations = [item for item in observations if item.kind == "run_command"]
    if not command_observations:
        return

    print("Commands:")
    for observation in command_observations:
        if observation.kind != "run_command":
            continue
        result = observation.result
        output = result.stdout.strip() or result.stderr.strip()
        timeout = " timeout" if result.timed_out else ""
        print(f"- {result.command} -> exit={result.exit_code}{timeout}")
        if output:
            print(indent(truncate(output, 800), "  "))


def truncate(value: str, max_length: int) -> str:
    # Keep printed output bounded to avoid flooding the terminal.
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}\n[truncated]"


def indent(value: str, prefix: str) -> str:
    # Left-pad each output line for readable command-summary formatting.
    return "\n".join(f"{prefix}{line}" for line in value.splitlines())


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
