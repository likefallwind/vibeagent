from __future__ import annotations

from time import monotonic
from typing import Any

from .agent_hook_agent_results import (
    agent_hook_decision_result,
    failed_agent_hook_result,
)
from .agent_hook_agent_tools import AGENT_HOOK_ALLOWED_TOOL_NAMES
from .agent_hook_prompt import (
    HookModelRuntime,
    expand_prompt_hook_arguments,
)
from .agent_hook_results import HookRunResult
from .agent_profile_client import configure_agent_profile_client
from .agent_runtime_utils import (
    append_session_event,
    content_blocks_to_text,
    normalize_assistant_content,
    to_jsonable,
)
from .redaction import redact_jsonable_payload
from .types import ChatMessage
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHook, ProjectHooks
from .workspace_permissions import ProjectPermissions


MAX_AGENT_HOOK_TURNS = 50
MAX_AGENT_HOOK_OUTPUT_TOKENS = 4_096


def run_project_agent_hook(
    workspace: RunWorkspace,
    hook: ProjectHook,
    *,
    target: str,
    hook_input: dict[str, object],
    iteration: int,
    hook_index: int,
    command_timeout_ms: int,
    permissions: ProjectPermissions,
    runtime: HookModelRuntime | None,
) -> HookRunResult:
    event_payload = {
        "iteration": iteration,
        "index": hook_index,
        "event": hook.event,
        "tool": target,
        "source": hook.source,
        "matcher": hook.matcher,
        "handler_type": "agent",
        "model": hook.model or "inherit",
    }
    if runtime is None:
        return failed_agent_hook_result(
            workspace,
            hook,
            event_payload,
            "Agent hook model runtime is unavailable.",
        )
    try:
        prompt = expand_prompt_hook_arguments(hook.prompt, hook_input)
        client = configure_agent_profile_client(
            runtime.client,
            model=hook.model,
            effort=None,
        )
    except (TypeError, ValueError) as error:
        return failed_agent_hook_result(
            workspace,
            hook,
            event_payload,
            f"Agent hook configuration was rejected: {error}",
        )

    if runtime.logger:
        runtime.logger("running hook", f"{hook.event} {target} agent hook")
    messages = _agent_messages(workspace, prompt)
    deadline = monotonic() + (hook.timeout_ms / 1000)
    observations: list[Any] = []
    steps: list[Any] = []
    auto_checkpoint_attempted = False

    # These imports are local because the delegate executor itself routes Hook
    # calls. Deferring them keeps the module dependency graph acyclic.
    from .agent_delegate_tools import (
        delegate_tool_definitions,
        execute_delegate_tool_call,
    )
    from .agent_multimodal import build_tool_result_block
    from .agent_tool_results import build_tool_result_payload

    allowed_tools = AGENT_HOOK_ALLOWED_TOOL_NAMES
    tools = delegate_tool_definitions(
        "explore",
        set(),
        "deny",
        allowed_tool_names=allowed_tools,
        nested_delegation_allowed=False,
    )
    for turn in range(1, MAX_AGENT_HOOK_TURNS + 1):
        remaining_ms = round((deadline - monotonic()) * 1000)
        if remaining_ms < 100:
            return failed_agent_hook_result(
                workspace,
                hook,
                event_payload,
                "Agent hook timed out.",
                timed_out=True,
            )
        response, model_error = runtime.complete_with_retries(
            client,
            messages,
            tools=tools,
            max_output_tokens=max(
                1, min(runtime.max_output_tokens, MAX_AGENT_HOOK_OUTPUT_TOKENS)
            ),
            model_retries=runtime.model_retries,
            model_retry_delay_ms=runtime.model_retry_delay_ms,
            model_timeout_ms=min(hook.timeout_ms, remaining_ms),
            iteration=iteration,
            session_dir=workspace.session_dir,
            logger=runtime.logger,
            error_event_type="hook_agent_model_error",
            error_event_extra={**event_payload, "turn": turn},
        )
        if response is None:
            return failed_agent_hook_result(
                workspace,
                hook,
                event_payload,
                model_error or "Agent hook model request failed.",
            )

        content = normalize_assistant_content(
            response.content if hasattr(response, "content") else response
        )
        append_session_event(
            workspace.session_dir,
            "hook_agent_model",
            {
                **event_payload,
                "turn": turn,
                "content": redact_jsonable_payload(content),
                **(
                    {"usage": to_jsonable(response.usage)}
                    if getattr(response, "usage", None) is not None
                    else {}
                ),
            },
        )
        messages.append(ChatMessage(role="assistant", content=content))
        tool_calls = [block for block in content if block.get("type") == "tool_call"]
        if not tool_calls:
            return agent_hook_decision_result(
                workspace,
                hook,
                event_payload,
                content_blocks_to_text(content).strip(),
                runtime,
            )

        tool_results: list[dict[str, object]] = []
        for block in tool_calls:
            tool_id = str(block.get("id") or "")
            tool_name = str(block.get("name") or "")
            tool_input = block.get("input") or {}
            append_session_event(
                workspace.session_dir,
                "hook_agent_tool_call",
                {
                    **event_payload,
                    "turn": turn,
                    "id": tool_id,
                    "name": tool_name,
                    "input": redact_jsonable_payload(tool_input),
                },
            )
            execution = execute_delegate_tool_call(
                workspace,
                mode="explore",
                tool_name=tool_name,
                tool_input=tool_input,
                active_tool_names=set(),
                observations=observations,
                steps=steps,
                iteration=iteration,
                command_timeout_ms=command_timeout_ms,
                logger=runtime.logger,
                approval_handler=None,
                approval_policy="deny",
                auto_checkpoint_attempted=auto_checkpoint_attempted,
                allowed_tool_names=allowed_tools,
                hooks=ProjectHooks(),
                permissions=permissions,
                tool_id=tool_id,
            )
            auto_checkpoint_attempted = execution.auto_checkpoint_attempted
            if execution.finish_action is not None:
                return agent_hook_decision_result(
                    workspace,
                    hook,
                    event_payload,
                    execution.finish_action.message,
                    runtime,
                )
            if execution.observation is None:
                return failed_agent_hook_result(
                    workspace,
                    hook,
                    event_payload,
                    f"Agent hook tool {tool_name or 'unknown'} returned no result.",
                )
            result_payload = build_tool_result_payload(execution.observation)
            append_session_event(
                workspace.session_dir,
                "hook_agent_tool_result",
                {
                    **event_payload,
                    "turn": turn,
                    "id": tool_id,
                    "name": tool_name,
                    "result": result_payload,
                },
            )
            tool_results.append(
                build_tool_result_block(
                    workspace,
                    tool_id,
                    execution.observation,
                    result_payload,
                )
            )
        messages.append(ChatMessage(role="user", content=tool_results))

    return failed_agent_hook_result(
        workspace,
        hook,
        event_payload,
        f"Agent hook reached its {MAX_AGENT_HOOK_TURNS}-turn limit.",
    )


def _agent_messages(workspace: RunWorkspace, prompt: str) -> list[ChatMessage]:
    return [
        ChatMessage(
            role="system",
            content=(
                "You are a read-only Hook verification agent. Investigate only the "
                "condition in the user prompt. You may inspect files and search the "
                f"workspace at {workspace.root}, but you cannot mutate files, run "
                "commands, delegate work, or ask the user. After investigating, "
                "return only one JSON object with boolean field ok. When ok is false, "
                "include a non-empty string field reason. You may also call finish "
                "with that exact JSON object as its message."
            ),
        ),
        ChatMessage(role="user", content=prompt),
    ]


__all__ = ["MAX_AGENT_HOOK_TURNS", "run_project_agent_hook"]
