from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cli_model_stream import terminal_model_stream_scope
from .cli_output import format_error
from .config_execution import ExecutionConfig
from .debug_runtime import DebugRuntime
from .types import ChatClient, ChatMessage


@dataclass(frozen=True)
class InteractiveChatTurnRequest:
    task: str
    client: ChatClient
    history: tuple[ChatMessage, ...]
    execution_config: ExecutionConfig
    system_prompt: str | None
    append_system_prompt: str | None
    debug_runtime: DebugRuntime


@dataclass(frozen=True)
class InteractiveChatTurnResult:
    response: str
    print_response: bool


def run_interactive_chat_turn(
    request: InteractiveChatTurnRequest,
    *,
    run_chat: Callable[..., str],
) -> InteractiveChatTurnResult:
    request.debug_runtime.emit(
        "api",
        "chat_request",
        {"inputChars": len(request.task)},
    )
    with terminal_model_stream_scope(request.client) as stream_renderer:
        try:
            response = run_chat(
                request.task,
                client=request.client,
                history=list(request.history),
                max_output_tokens=request.execution_config.max_output_tokens,
                model_retries=request.execution_config.model_retries,
                model_retry_delay_ms=request.execution_config.model_retry_delay_ms,
                model_timeout_ms=request.execution_config.model_timeout_ms,
                system_prompt=request.system_prompt,
                append_system_prompt=request.append_system_prompt,
                **(
                    {"model_stream_handler": stream_renderer.chat_event}
                    if stream_renderer is not None
                    else {}
                ),
            )
        except Exception as error:
            request.debug_runtime.emit(
                "api",
                "chat_error",
                {"type": type(error).__name__, "message": format_error(error)},
            )
            raise
    request.debug_runtime.emit(
        "api",
        "chat_response",
        {"outputChars": len(response)},
    )
    return InteractiveChatTurnResult(
        response=response,
        print_response=(
            stream_renderer is None
            or not stream_renderer.matches_final_message(response)
        ),
    )


__all__ = [
    "InteractiveChatTurnRequest",
    "InteractiveChatTurnResult",
    "run_interactive_chat_turn",
]
