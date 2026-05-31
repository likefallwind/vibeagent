from __future__ import annotations

from .agent import run_agent
from .commands import get_help_text, get_model_text, parse_local_command
from .minimax import MiniMaxClient, MiniMaxHttpError
from .types import AgentStatus, Observation


def main() -> int:
    print("VibeAgent v0.1")
    print("Type a programming task. Use /help for commands or Ctrl+C to exit.")

    client: MiniMaxClient | None = None
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

        try:
            client = client or MiniMaxClient()
            result = run_agent(task, client=client, logger=log_status)

            print("\nSuccess" if result.success else "\nStopped")
            print(result.message)
            print(f"Run directory: {result.run_dir}")
            print(f"Iterations: {result.iterations}")
            print_command_summary(result.observations)
        except Exception as error:
            print(f"\nError: {format_error(error)}")


def log_status(status: AgentStatus, detail: str | None = None) -> None:
    print(f"[{status}]{' ' + detail if detail else ''}")


def print_command_summary(observations: list[Observation]) -> None:
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
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}\n[truncated]"


def indent(value: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in value.splitlines())


def format_error(error: Exception) -> str:
    if isinstance(error, MiniMaxHttpError) and error.status == 401:
        return "\n".join(
            [
                str(error),
                "MiniMax rejected the configured API key. Check MINIMAX_API_KEY, MINIMAX_API, or minimax_api.",
                "If you copied a value that starts with 'Bearer ', VibeAgent strips that prefix automatically.",
            ]
        )
    return str(error)


if __name__ == "__main__":
    raise SystemExit(main())
