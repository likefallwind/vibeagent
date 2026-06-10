from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import os
from pathlib import Path
import sys

from .agent import AgentResult, run_agent
from .chat import run_chat
from .commands import (
    get_help_text,
    get_compact_context,
    get_context_text,
    get_cost_text,
    get_doctor_text,
    get_last_session_text,
    get_model_text,
    get_resume_context,
    get_session_text,
    get_sessions_text,
    get_status_text,
    get_usage_text,
    init_project_instructions,
    parse_local_command,
)
from .config import load_project_config_env, resolve_execution_config, save_project_config
from .providers import create_chat_client, get_provider_name
from .types import ApprovalDecision, ApprovalHandler, ApprovalPolicy, ApprovalRequest, ChatMessage


def main(argv: Sequence[str] | None = None) -> int:
    if argv is not None:
        args = parse_args(argv)
        if has_local_flag(args):
            if args.task:
                return print_error_result("Local command flags cannot be combined with a task.", args.json, exit_code=2)
            return run_local_flag(args)
        if args.task:
            return run_one_shot(
                resolve_task_text(args.task),
                request_mode="chat" if args.chat else "code",
                approval_policy=args.approval,
                resume_arg=args.resume,
                base_dir=args.cwd,
                max_iterations=args.max_iterations,
                command_timeout_ms=args.command_timeout_ms,
                output_json=args.json,
                provider_args=args,
            )
    return run_interactive()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vibeagent", description="Run VibeAgent interactively or execute one task.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--chat", action="store_true", help="Run the one-shot task in daily conversation mode.")
    mode.add_argument("--code", action="store_true", help="Run the one-shot task in coding mode. This is the default.")
    local = parser.add_mutually_exclusive_group()
    local.add_argument("--model", action="store_true", help="Show model provider configuration and exit.")
    local.add_argument("--status", action="store_true", help="Show default non-interactive status and exit.")
    local.add_argument("--context", action="store_true", help="Show project context sources and exit.")
    local.add_argument("--init", action="store_true", help="Create a starter AGENTS.md and exit.")
    local.add_argument("--doctor", action="store_true", help="Show local diagnostics and exit.")
    local.add_argument("--sessions", action="store_true", help="List recent local sessions and exit.")
    local.add_argument("--last", action="store_true", help="Show the newest session summary and exit.")
    local.add_argument("--session", metavar="RUN_ID", help="Show one compact session summary and exit.")
    local.add_argument("--usage", action="store_true", help="Show local session usage and exit.")
    local.add_argument("--cost", action="store_true", help="Show configured cost estimate and exit.")
    local.add_argument("--save-config", action="store_true", help="Save non-secret provider defaults to .vibeagent/config.json and exit.")
    parser.add_argument(
        "--approval",
        choices=("ask", "allow", "deny"),
        default="ask",
        help="Approval policy for one-shot coding tasks.",
    )
    parser.add_argument(
        "--resume",
        nargs="?",
        const="",
        metavar="RUN_ID",
        help="Load a previous session summary before a one-shot coding task. Omit RUN_ID to use the newest session.",
    )
    parser.add_argument("--cwd", help="Project directory for one-shot coding tasks.")
    parser.add_argument("--json", action="store_true", help="Print a single JSON result for one-shot or local command output.")
    parser.add_argument(
        "--provider",
        choices=("minimax", "deepseek", "openai-compatible"),
        help="Temporarily override the model provider for this command.",
    )
    parser.add_argument("--model-name", help="Temporarily override the model name for this command.")
    parser.add_argument("--base-url", help="Temporarily override the provider base URL for this command.")
    parser.add_argument("--api-key", help="Temporarily override the provider API key for this command.")
    parser.add_argument(
        "--max-iterations",
        type=positive_int,
        help="Maximum model/tool iterations for one-shot coding tasks. Defaults to project config or 20.",
    )
    parser.add_argument(
        "--command-timeout-ms",
        type=timeout_ms,
        help="Default command timeout in milliseconds for one-shot coding tasks. Defaults to project config or 30000.",
    )
    parser.add_argument("task", nargs="*", help="One-shot task text. Omit it to start the interactive prompt.")
    return parser.parse_args(list(argv))


def has_local_flag(args: argparse.Namespace) -> bool:
    return any(
        (
            args.model,
            args.status,
            args.context,
            args.init,
            args.doctor,
            args.sessions,
            args.last,
            args.session is not None,
            args.usage,
            args.cost,
            args.save_config,
        )
    )


def run_local_flag(args: argparse.Namespace) -> int:
    try:
        project_root = resolve_project_root(args.cwd)
        config_root = project_root or Path.cwd()
        if args.save_config:
            text = save_project_config_from_args(args, config_root)
        else:
            provider_env = build_provider_env(args, config_root)
            if args.model:
                text = get_model_text(provider_env)
            elif args.status:
                text = get_status_text("code", args.approval, None, chat_turns=0)
            elif args.context:
                text = get_context_text(project_root)
            elif args.init:
                text = init_project_instructions(project_root or ".")
            elif args.doctor:
                text = get_doctor_text(project_root or ".", provider_env)
            elif args.sessions:
                text = get_sessions_text(project_root or ".")
            elif args.last:
                text = get_last_session_text(project_root or ".")
            elif args.session is not None:
                text = get_session_text(args.session, project_root or ".")
            elif args.usage:
                text = get_usage_text(project_root or ".")
            elif args.cost:
                text = get_cost_text(project_root or ".")
            else:
                text = ""
        print_output({"kind": "local", "success": True, "text": text}, args.json)
        return 0
    except Exception as error:
        return print_error_result(format_error(error), args.json, prefix=True)


def resolve_task_text(parts: Sequence[str]) -> str:
    if len(parts) == 1 and parts[0] == "-":
        return sys.stdin.read().strip()
    return " ".join(parts)


def run_one_shot(
    task: str,
    request_mode: str,
    approval_policy: ApprovalPolicy,
    resume_arg: str | None = None,
    base_dir: str | None = None,
    max_iterations: int | None = None,
    command_timeout_ms: int | None = None,
    output_json: bool = False,
    provider_args: argparse.Namespace | None = None,
) -> int:
    try:
        if not task.strip():
            return print_error_result("No task provided.", output_json)
        project_root = resolve_project_root(base_dir)
        config_root = project_root or Path.cwd()
        execution_config = resolve_execution_config(
            config_root,
            max_iterations=max_iterations,
            command_timeout_ms=command_timeout_ms,
        )
        provider_env = build_provider_env(provider_args, config_root)
        if request_mode == "chat":
            client = create_chat_client(provider_env)
            response = run_chat(task, client=client, history=[])
            print_output({"kind": "chat", "success": True, "message": response}, output_json)
            return 0

        resume_context = None
        if resume_arg is not None:
            _selected, resume_context, text = get_resume_context(normalize_resume_arg(resume_arg), project_root)
            if resume_context is None:
                return print_error_result(text, output_json)
        client = create_chat_client(provider_env)
        result = run_agent(
            task,
            client=client,
            base_dir=project_root,
            max_iterations=execution_config.max_iterations,
            command_timeout_ms=execution_config.command_timeout_ms,
            approval_handler=build_approval_handler(approval_policy),
            prior_context=resume_context,
        )
        if output_json:
            print_output(
                {
                    "kind": "code",
                    "success": result.success,
                    "message": result.message,
                    "runId": result.run_id,
                    "runDir": str(result.run_dir),
                    "iterations": result.iterations,
                    "steps": len(result.steps),
                },
                True,
            )
        else:
            print_agent_result(result)
        return 0 if result.success else 1
    except Exception as error:
        return print_error_result(format_error(error), output_json, prefix=True)


def print_output(payload: dict[str, object], output_json: bool) -> None:
    if output_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    text = payload.get("text") if "text" in payload else payload.get("message")
    print("" if text is None else text)


def print_error_result(error: str, output_json: bool, exit_code: int = 1, prefix: bool = False) -> int:
    if output_json:
        print(json.dumps({"success": False, "error": error}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Error: {error}" if prefix else error)
    return exit_code


def resolve_project_root(value: str | None) -> Path | None:
    if value is None:
        return None
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory not found: {value}")
    return root


def build_provider_env(args: argparse.Namespace | None, project_root: Path | None = None) -> dict[str, str | None]:
    env: dict[str, str | None] = dict(os.environ)
    config_root = project_root or Path.cwd()
    for key, value in load_project_config_env(config_root).items():
        if not env.get(key):
            env[key] = value
    arg_provider = getattr(args, "provider", None)
    arg_model_name = getattr(args, "model_name", None)
    arg_base_url = getattr(args, "base_url", None)
    arg_api_key = getattr(args, "api_key", None)
    provider = arg_provider or get_provider_name(env)
    if arg_provider:
        env["VIBEAGENT_PROVIDER"] = arg_provider
    if arg_model_name:
        if provider == "minimax":
            env["MINIMAX_MODEL"] = arg_model_name
        else:
            env["OPENAI_COMPAT_MODEL"] = arg_model_name
            env["DEEPSEEK_MODEL"] = arg_model_name
    if arg_base_url:
        if provider == "minimax":
            env["MINIMAX_BASE_URL"] = arg_base_url
        else:
            env["OPENAI_COMPAT_BASE_URL"] = arg_base_url
            env["DEEPSEEK_BASE_URL"] = arg_base_url
    if arg_api_key:
        if provider == "minimax":
            env["MINIMAX_API_KEY"] = arg_api_key
        else:
            env["OPENAI_COMPAT_API_KEY"] = arg_api_key
            env["DEEPSEEK_API_KEY"] = arg_api_key
    return env


def save_project_config_from_args(args: argparse.Namespace, project_root: str | Path) -> str:
    if args.api_key:
        raise ValueError("--save-config does not write API keys. Use environment variables or --api-key for one command.")
    return save_project_config(
        project_root,
        provider=args.provider,
        model=args.model_name,
        base_url=args.base_url,
        max_iterations=args.max_iterations,
        command_timeout_ms=args.command_timeout_ms,
    )


def normalize_resume_arg(value: str) -> str | None:
    return value or None


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def timeout_ms(value: str) -> int:
    parsed = positive_int(value)
    if parsed < 100:
        raise argparse.ArgumentTypeError("must be at least 100")
    return parsed


def run_interactive() -> int:
    # Entry loop: parse local commands first, otherwise delegate to the agent.
    print("VibeAgent v0.1")
    print("Type a programming task, or use /chat for daily conversation. Use /help for commands.")

    client = None
    mode = "code"
    approval_policy: ApprovalPolicy = "ask"
    chat_history: list[ChatMessage] = []
    resume_run_id: str | None = None
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
        if command and command.type == "status":
            print(get_status_text(mode, approval_policy, resume_run_id, chat_turns=len(chat_history) // 2))
            continue
        if command and command.type == "context":
            print(get_context_text(resume_run_id=resume_run_id, resume_context=resume_context))
            continue
        if command and command.type == "init":
            print(init_project_instructions())
            continue
        if command and command.type == "doctor":
            print(get_doctor_text())
            continue
        if command and command.type == "clear":
            chat_history.clear()
            resume_run_id = None
            resume_context = None
            print("Cleared chat history and resume context.")
            continue
        if command and command.type == "usage":
            print(get_usage_text())
            continue
        if command and command.type == "cost":
            print(get_cost_text())
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
            selected, context, text = get_resume_context(command.argument)
            resume_run_id = selected
            resume_context = context
            print(text)
            continue
        if command and command.type == "compact":
            selected, context, text = get_compact_context(command.argument)
            resume_run_id = selected
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
            selected, next_context, _ = get_resume_context(result.run_id)
            if next_context:
                resume_run_id = selected
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
    import sys

    raise SystemExit(main(sys.argv[1:]))
