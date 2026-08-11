from __future__ import annotations

from collections.abc import Callable

from .cli_one_shot_output import build_one_shot_chat_payload, emit_one_shot_chat_payload
from .cli_stream_output import JsonEventStream
from .config import ExecutionConfig
from .model_effort import ModelEffortSetting, configure_model_effort


def run_one_shot_chat(
    task: str,
    *,
    provider_env: dict[str, str | None],
    execution_config: ExecutionConfig,
    system_prompt: str | None,
    append_system_prompt: str | None,
    machine_output: bool,
    output_json: bool,
    elapsed_ms: int,
    stream: JsonEventStream | None,
    effort: str | None = None,
    effort_locked: bool = False,
    include_partial_messages: bool = False,
    create_chat_client_func: Callable[[dict[str, str | None]], object],
    run_chat_func: Callable[..., str],
) -> int:
    client = configure_model_effort(
        create_chat_client_func(provider_env),  # type: ignore[arg-type]
        ModelEffortSetting(effort, locked=effort_locked),
    )
    run_kwargs: dict[str, object] = {}
    if include_partial_messages:
        if stream is None:
            raise ValueError("Partial messages require stream-json output.")
        run_kwargs["model_stream_handler"] = stream.chat_stream_event
    response = run_chat_func(
        task,
        client=client,
        history=[],
        max_output_tokens=execution_config.max_output_tokens,
        model_retries=execution_config.model_retries,
        model_retry_delay_ms=execution_config.model_retry_delay_ms,
        model_timeout_ms=execution_config.model_timeout_ms,
        system_prompt=system_prompt,
        append_system_prompt=append_system_prompt,
        **run_kwargs,
    )
    payload = build_one_shot_chat_payload(
        response,
        machine_output=machine_output,
        elapsed_ms=elapsed_ms,
    )
    emit_one_shot_chat_payload(payload, stream=stream, output_json=output_json)
    return 0
