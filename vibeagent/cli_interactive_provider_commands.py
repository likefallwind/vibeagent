from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .cli_interactive_model import interactive_provider_env, resolve_interactive_model_selection
from .config import resolve_execution_config
from .types import ChatMessage


@dataclass(frozen=True)
class InteractiveProviderCommandResult:
    client: object | None
    text: str
    model_override: str | None = None
    model_changed: bool = False


def run_interactive_provider_command(
    command_type: str,
    argument: str | None,
    *,
    project_root: Path,
    current_override: str | None,
    current_client: object | None,
    create_chat_client: Callable[[dict[str, str | None]], object],
    run_btw: Callable[..., str],
    history: list[ChatMessage],
    system_prompt: str | None,
    append_system_prompt: str | None,
) -> InteractiveProviderCommandResult:
    if command_type == "model":
        return run_interactive_model_command(
            argument,
            project_root=project_root,
            current_override=current_override,
            current_client=current_client,
            create_chat_client=create_chat_client,
        )
    return run_interactive_btw_command(
        argument,
        current_client=current_client,
        provider_env=interactive_provider_env(project_root, current_override),
        create_chat_client=create_chat_client,
        run_btw=run_btw,
        history=history,
        execution_config=resolve_execution_config(project_root),
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
    )


def run_interactive_model_command(
    argument: str | None,
    *,
    project_root: Path,
    current_override: str | None,
    current_client: object | None,
    create_chat_client: Callable[[dict[str, str | None]], object],
) -> InteractiveProviderCommandResult:
    try:
        selection = resolve_interactive_model_selection(
            project_root,
            argument,
            current_override,
        )
        client = (
            create_chat_client(selection.provider_env)
            if selection.changed
            else current_client
        )
        return InteractiveProviderCommandResult(
            client=client,
            text=selection.text,
            model_override=selection.override,
            model_changed=selection.changed,
        )
    except KeyboardInterrupt:
        return InteractiveProviderCommandResult(
            client=current_client,
            text="Interrupted.",
            model_override=current_override,
        )
    except Exception as error:
        return InteractiveProviderCommandResult(
            client=current_client,
            text=f"Model switch error: {_error_text(error)}",
            model_override=current_override,
        )


def run_interactive_btw_command(
    argument: str | None,
    *,
    current_client: object | None,
    provider_env: dict[str, str | None],
    create_chat_client: Callable[[dict[str, str | None]], object],
    run_btw: Callable[..., str],
    history: list[ChatMessage],
    execution_config: object,
    system_prompt: str | None,
    append_system_prompt: str | None,
) -> InteractiveProviderCommandResult:
    if not argument:
        return InteractiveProviderCommandResult(
            client=current_client,
            text="Usage: /btw <question>",
        )
    client = current_client
    try:
        client = client or create_chat_client(provider_env)
        response = run_btw(
            argument,
            client=client,
            history=history,
            max_output_tokens=execution_config.max_output_tokens,
            model_retries=execution_config.model_retries,
            model_retry_delay_ms=execution_config.model_retry_delay_ms,
            model_timeout_ms=execution_config.model_timeout_ms,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
        return InteractiveProviderCommandResult(client=client, text=f"\n{response}")
    except KeyboardInterrupt:
        return InteractiveProviderCommandResult(client=client, text="\nInterrupted.")
    except Exception as error:
        return InteractiveProviderCommandResult(
            client=client,
            text=f"\nBTW error: {_error_text(error)}",
        )


def _error_text(error: Exception) -> str:
    text = str(error).strip()
    return text or type(error).__name__


__all__ = [
    "InteractiveProviderCommandResult",
    "run_interactive_btw_command",
    "run_interactive_model_command",
    "run_interactive_provider_command",
]
