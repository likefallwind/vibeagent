from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from typing import Any

from .agent_hook_results import HookRunResult
from .agent_profile_client import configure_agent_profile_client
from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    normalize_assistant_content,
    to_jsonable,
)
from .redaction import redact_sensitive_text
from .types import AgentLogger, ChatClient, ChatMessage
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHook


MAX_PROMPT_HOOK_INPUT_CHARS = 200_000
MAX_PROMPT_HOOK_OUTPUT_TOKENS = 1_024
MAX_PROMPT_HOOK_REASON_CHARS = 4_000
_ESCAPED_DOLLAR = "\x00vibeagent-escaped-dollar\x00"
CompleteWithRetries = Callable[..., tuple[Any | None, str | None]]


@dataclass(frozen=True)
class HookModelRuntime:
    client: ChatClient
    complete_with_retries: CompleteWithRetries
    max_output_tokens: int
    model_retries: int
    model_retry_delay_ms: int
    logger: AgentLogger | None = None


def run_project_prompt_hook(
    workspace: RunWorkspace,
    hook: ProjectHook,
    *,
    target: str,
    hook_input: dict[str, object],
    iteration: int,
    hook_index: int,
    runtime: HookModelRuntime | None,
) -> HookRunResult:
    event_payload = {
        "iteration": iteration,
        "index": hook_index,
        "event": hook.event,
        "tool": target,
        "source": hook.source,
        "matcher": hook.matcher,
        "handler_type": "prompt",
        "model": hook.model or "inherit",
    }
    if runtime is None:
        return _failed_result(
            workspace,
            hook,
            event_payload,
            "Prompt hook model runtime is unavailable.",
        )
    try:
        prompt = expand_prompt_hook_arguments(hook.prompt, hook_input)
        client = configure_agent_profile_client(
            runtime.client,
            model=hook.model,
            effort=None,
        )
    except (TypeError, ValueError) as error:
        return _failed_result(
            workspace,
            hook,
            event_payload,
            f"Prompt hook configuration was rejected: {error}",
        )

    if runtime.logger:
        runtime.logger("running hook", f"{hook.event} {target} prompt hook")
    response, model_error = runtime.complete_with_retries(
        client,
        [ChatMessage(role="user", content=_evaluation_prompt(prompt))],
        tools=None,
        max_output_tokens=max(
            1, min(runtime.max_output_tokens, MAX_PROMPT_HOOK_OUTPUT_TOKENS)
        ),
        model_retries=runtime.model_retries,
        model_retry_delay_ms=runtime.model_retry_delay_ms,
        model_timeout_ms=hook.timeout_ms,
        iteration=iteration,
        session_dir=workspace.session_dir,
        logger=runtime.logger,
        error_event_type="hook_model_error",
        error_event_extra=event_payload,
    )
    if response is None:
        return _failed_result(
            workspace,
            hook,
            event_payload,
            model_error or "Prompt hook model request failed.",
        )

    content = normalize_assistant_content(
        response.content if hasattr(response, "content") else response
    )
    text = content_blocks_to_text(content).strip()
    append_session_event(
        workspace.session_dir,
        "hook_model",
        {
            **event_payload,
            "content": content,
            **(
                {"usage": to_jsonable(response.usage)}
                if getattr(response, "usage", None) is not None
                else {}
            ),
        },
    )
    try:
        allowed, reason = parse_prompt_hook_decision(text)
    except ValueError as error:
        return _failed_result(
            workspace,
            hook,
            event_payload,
            f"Prompt hook response was rejected: {error}",
        )

    safe_reason = redact_sensitive_text(reason)
    safe_output = json.dumps(
        {"ok": allowed, **({"reason": safe_reason} if safe_reason else {})},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    result = HookRunResult(
        event=hook.event,
        command="prompt",
        source=hook.source,
        status="passed" if allowed else "blocked",
        ok=allowed,
        exit_code=None,
        timed_out=False,
        stdout=safe_output,
        stderr="",
        message=(
            f"{hook.event} prompt hook allowed execution."
            if allowed
            else safe_reason
        ),
        handler_type="prompt",
    )
    append_session_event(
        workspace.session_dir,
        "hook_completed",
        {**event_payload, "result": result},
    )
    if runtime.logger:
        runtime.logger("hook passed" if allowed else "hook blocked", result.message)
    return result


def expand_prompt_hook_arguments(
    prompt: str, hook_input: dict[str, object]
) -> str:
    encoded = json.dumps(
        hook_input,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    protected = prompt.replace("\\$", _ESCAPED_DOLLAR)
    expanded = (
        protected.replace("$ARGUMENTS", encoded)
        if "$ARGUMENTS" in protected
        else f"{protected}\n\n{encoded}"
    ).replace(_ESCAPED_DOLLAR, "$")
    if len(expanded) > MAX_PROMPT_HOOK_INPUT_CHARS:
        raise ValueError(
            f"Prompt hook expanded input exceeds {MAX_PROMPT_HOOK_INPUT_CHARS} characters."
        )
    return expanded


def parse_prompt_hook_decision(text: str) -> tuple[bool, str]:
    try:
        payload = json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_json_object,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError("response must be one JSON object.") from error
    if not isinstance(payload, dict) or type(payload.get("ok")) is not bool:
        raise ValueError("response must contain a boolean ok field.")
    allowed = payload["ok"]
    reason = payload.get("reason", "")
    if not isinstance(reason, str) or len(reason) > MAX_PROMPT_HOOK_REASON_CHARS:
        raise ValueError(
            f"response reason must be a string of at most {MAX_PROMPT_HOOK_REASON_CHARS} characters."
        )
    if not allowed and not reason.strip():
        raise ValueError(
            f"blocked response reason must contain 1-{MAX_PROMPT_HOOK_REASON_CHARS} characters."
        )
    return allowed, reason.strip()


def _evaluation_prompt(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Return only one JSON object with boolean field ok. "
        "When ok is false, include a non-empty string field reason."
    )


def _failed_result(
    workspace: RunWorkspace,
    hook: ProjectHook,
    event_payload: dict[str, object],
    message: str,
) -> HookRunResult:
    bounded = redact_sensitive_text(message)
    if len(bounded) > 1_000:
        bounded = bounded[:997] + "..."
    result = HookRunResult(
        event=hook.event,
        command="prompt",
        source=hook.source,
        status="failed",
        ok=False,
        exit_code=None,
        timed_out=False,
        stdout="",
        stderr="",
        message=f"{bounded} The hook error is non-blocking.",
        handler_type="prompt",
        non_blocking_error=True,
    )
    append_session_event(
        workspace.session_dir,
        "hook_completed",
        {**event_payload, "result": result},
    )
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


__all__ = [
    "HookModelRuntime",
    "expand_prompt_hook_arguments",
    "parse_prompt_hook_decision",
    "run_project_prompt_hook",
]
