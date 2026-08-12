from __future__ import annotations

from dataclasses import dataclass
import json

from .agent_hook_results import HookRunResult


MAX_UPDATED_TOOL_OUTPUT_BYTES = 128_000


@dataclass(frozen=True)
class ParsedPostToolHookOutput:
    additional_context: str | None = None
    updated_tool_output: object | None = None
    updated_tool_output_set: bool = False


class PostToolHookOutputError(ValueError):
    pass


def parse_post_tool_hook_output(result: HookRunResult) -> ParsedPostToolHookOutput:
    stdout = result.stdout.strip()
    if not result.ok or not stdout:
        return ParsedPostToolHookOutput()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as error:
        if stdout.startswith(("{", "[")):
            raise PostToolHookOutputError(
                f"PostToolUse hook returned invalid JSON: {error.msg}."
            ) from error
        return ParsedPostToolHookOutput()
    if not isinstance(payload, dict):
        raise PostToolHookOutputError("PostToolUse hook JSON output must be an object.")

    specific_value = payload.get("hookSpecificOutput")
    if specific_value is not None and not isinstance(specific_value, dict):
        raise PostToolHookOutputError("hookSpecificOutput must be an object.")
    specific = specific_value if isinstance(specific_value, dict) else {}
    event_name = specific.get("hookEventName")
    if event_name is not None and event_name != "PostToolUse":
        raise PostToolHookOutputError(
            "hookSpecificOutput.hookEventName must be 'PostToolUse'."
        )

    additional_context = specific.get(
        "additionalContext", payload.get("additionalContext")
    )
    if additional_context is not None and not isinstance(additional_context, str):
        raise PostToolHookOutputError("additionalContext must be a string.")
    updated_set = "updatedToolOutput" in specific
    updated_output = specific.get("updatedToolOutput")
    if updated_set:
        try:
            encoded = json.dumps(
                updated_output,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise PostToolHookOutputError(
                "updatedToolOutput must be a finite JSON value."
            ) from error
        if len(encoded) > MAX_UPDATED_TOOL_OUTPUT_BYTES:
            raise PostToolHookOutputError(
                f"updatedToolOutput exceeds {MAX_UPDATED_TOOL_OUTPUT_BYTES} bytes."
            )
    return ParsedPostToolHookOutput(
        additional_context=(
            additional_context.strip()
            if isinstance(additional_context, str) and additional_context.strip()
            else None
        ),
        updated_tool_output=updated_output,
        updated_tool_output_set=updated_set,
    )


__all__ = [
    "MAX_UPDATED_TOOL_OUTPUT_BYTES",
    "ParsedPostToolHookOutput",
    "PostToolHookOutputError",
    "parse_post_tool_hook_output",
]
