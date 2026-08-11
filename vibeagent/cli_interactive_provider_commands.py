from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .cli_interactive_model import interactive_provider_env, resolve_interactive_model_selection
from .cli_interactive_effort import (
    configure_interactive_effort,
    resolve_interactive_effort_selection,
)
from .config import resolve_execution_config
from .session_recap import has_recap_history
from .types import ChatMessage


@dataclass(frozen=True)
class InteractiveProviderCommandResult:
    client: object | None
    text: str
    model_override: str | None = None
    model_changed: bool = False
    effort_override: str | None = None
    effort_changed: bool = False
    provider_succeeded: bool = False


def run_interactive_provider_command(
    command_type: str,
    argument: str | None,
    *,
    project_root: Path,
    current_override: str | None,
    current_effort: str | None,
    effort_locked: bool = False,
    current_client: object | None,
    create_chat_client: Callable[[dict[str, str | None]], object],
    run_btw: Callable[..., str],
    run_recap: Callable[..., str],
    history: list[ChatMessage],
    system_prompt: str | None,
    append_system_prompt: str | None,
) -> InteractiveProviderCommandResult:
    def create_session_client(provider_env: dict[str, str | None]) -> object:
        return configure_interactive_effort(
            create_chat_client(provider_env),  # type: ignore[arg-type]
            current_effort,
            locked=effort_locked,
        )

    if command_type == "model":
        return run_interactive_model_command(
            argument,
            project_root=project_root,
            current_override=current_override,
            current_effort=current_effort,
            current_client=current_client,
            effort_locked=effort_locked,
            create_chat_client=create_chat_client,
        )
    if command_type == "effort":
        return run_interactive_effort_command(
            argument,
            current_override=current_effort,
            current_client=current_client,
            locked=effort_locked,
            provider_env=interactive_provider_env(project_root, current_override),
            create_chat_client=create_chat_client,
        )
    if command_type == "recap":
        return run_interactive_recap_command(
            argument,
            current_client=current_client,
            provider_env=interactive_provider_env(project_root, current_override),
            create_chat_client=create_session_client,
            run_recap=run_recap,
            history=history,
            execution_config=resolve_execution_config(project_root),
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
    return run_interactive_btw_command(
        argument,
        current_client=current_client,
        provider_env=interactive_provider_env(project_root, current_override),
        create_chat_client=create_session_client,
        run_btw=run_btw,
        history=history,
        execution_config=resolve_execution_config(project_root),
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
    )


def run_interactive_recap_command(
    argument: str | None,
    *,
    current_client: object | None,
    provider_env: dict[str, str | None],
    create_chat_client: Callable[[dict[str, str | None]], object],
    run_recap: Callable[..., str],
    history: list[ChatMessage],
    execution_config: object,
    system_prompt: str | None,
    append_system_prompt: str | None,
) -> InteractiveProviderCommandResult:
    if argument:
        return InteractiveProviderCommandResult(
            client=current_client,
            text="Usage: /recap",
        )
    if not has_recap_history(history):
        return InteractiveProviderCommandResult(
            client=current_client,
            text="No conversation is available to recap.",
        )
    client = current_client
    try:
        client = client or create_chat_client(provider_env)
        response = run_recap(
            client,
            history=history,
            max_output_tokens=execution_config.max_output_tokens,
            model_retries=execution_config.model_retries,
            model_retry_delay_ms=execution_config.model_retry_delay_ms,
            model_timeout_ms=execution_config.model_timeout_ms,
            system_prompt=system_prompt,
            append_system_prompt=append_system_prompt,
        )
        return InteractiveProviderCommandResult(client=client, text=response, provider_succeeded=True)
    except KeyboardInterrupt:
        return InteractiveProviderCommandResult(client=client, text="Interrupted.")
    except Exception as error:
        return InteractiveProviderCommandResult(
            client=client,
            text=f"Recap error: {_error_text(error)}",
        )


def run_interactive_model_command(
    argument: str | None,
    *,
    project_root: Path,
    current_override: str | None,
    current_effort: str | None,
    current_client: object | None,
    effort_locked: bool = False,
    create_chat_client: Callable[[dict[str, str | None]], object],
) -> InteractiveProviderCommandResult:
    try:
        selection = resolve_interactive_model_selection(
            project_root,
            argument,
            current_override,
        )
        client = current_client
        if selection.changed:
            client = configure_interactive_effort(
                create_chat_client(selection.provider_env),
                current_effort,
                locked=effort_locked,
            )
        return InteractiveProviderCommandResult(
            client=client,
            text=selection.text,
            model_override=selection.override,
            model_changed=selection.changed,
            effort_override=current_effort,
        )
    except KeyboardInterrupt:
        return InteractiveProviderCommandResult(
            client=current_client,
            text="Interrupted.",
            model_override=current_override,
            effort_override=current_effort,
        )
    except Exception as error:
        return InteractiveProviderCommandResult(
            client=current_client,
            text=f"Model switch error: {_error_text(error)}",
            model_override=current_override,
            effort_override=current_effort,
        )


def run_interactive_effort_command(
    argument: str | None,
    *,
    current_override: str | None,
    current_client: object | None,
    provider_env: dict[str, str | None],
    create_chat_client: Callable[[dict[str, str | None]], object],
    locked: bool = False,
) -> InteractiveProviderCommandResult:
    try:
        selection = resolve_interactive_effort_selection(argument, current_override, locked=locked)
        client = current_client
        if selection.changed:
            base_client = (
                create_chat_client(provider_env)
                if selection.override is None or current_client is None
                else current_client
            )
            client = configure_interactive_effort(base_client, selection.override, locked=locked)
        return InteractiveProviderCommandResult(
            client=client,
            text=selection.text,
            effort_override=selection.override,
            effort_changed=selection.changed,
        )
    except KeyboardInterrupt:
        return InteractiveProviderCommandResult(
            client=current_client,
            text="Interrupted.",
            effort_override=current_override,
        )
    except Exception as error:
        return InteractiveProviderCommandResult(
            client=current_client,
            text=f"Effort switch error: {_error_text(error)}",
            effort_override=current_override,
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
    "run_interactive_effort_command",
    "run_interactive_model_command",
    "run_interactive_provider_command",
    "run_interactive_recap_command",
]
