from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

from .mcp_action_executor import (
    call_advertised_mcp_tool,
    list_advertised_mcp_tool_names,
)
from .mcp_config import MCP_NAME_PATTERN, read_mcp_server_configs
from .redaction import redact_sensitive_text
from .types import ApprovalDecision, ApprovalHandler, ApprovalRequest
from .workspace_core import RunWorkspace


MAX_PERMISSION_PROMPT_TEXT = 8_000
MAX_PERMISSION_DECISION_MESSAGE = 1_000


@dataclass(frozen=True)
class PermissionPromptTool:
    server: str
    name: str

    @property
    def qualified_name(self) -> str:
        return f"mcp__{self.server}__{self.name}"


def resolve_permission_prompt_tool(
    workspace: RunWorkspace,
    value: str,
    *,
    timeout_ms: int = 10_000,
    list_tools_func: Callable[..., frozenset[str]] = list_advertised_mcp_tool_names,
) -> PermissionPromptTool:
    server, name = _parse_tool_reference(value)
    if server is not None:
        names = list_tools_func(workspace, server, timeout_ms=timeout_ms)
        if name not in names:
            raise ValueError(
                f"Permission prompt MCP tool {name!r} was not advertised by server {server!r}."
            )
        return PermissionPromptTool(server, name)

    matches: list[PermissionPromptTool] = []
    for config in read_mcp_server_configs(workspace):
        names = list_tools_func(workspace, config.name, timeout_ms=timeout_ms)
        if name in names:
            matches.append(PermissionPromptTool(config.name, name))
    if not matches:
        raise ValueError(f"Permission prompt MCP tool {name!r} was not advertised by any configured server.")
    if len(matches) > 1:
        choices = ", ".join(item.qualified_name for item in matches)
        raise ValueError(
            f"Permission prompt MCP tool {name!r} is ambiguous; use one of: {choices}."
        )
    return matches[0]


def build_mcp_permission_prompt_handler(
    workspace: RunWorkspace,
    tool: PermissionPromptTool,
    *,
    timeout_ms: int = 30_000,
    call_tool_func: Callable[..., dict[str, Any]] = call_advertised_mcp_tool,
) -> ApprovalHandler:
    def handle(request: ApprovalRequest) -> ApprovalDecision:
        arguments = _request_arguments(request)
        try:
            result = call_tool_func(
                workspace,
                tool.server,
                tool.name,
                arguments,
                timeout_ms=timeout_ms,
            )
            return _parse_decision(result, arguments["input"], tool)
        except Exception as error:
            message = _bounded_message(redact_sensitive_text(str(error)))
            return ApprovalDecision(
                approved=False,
                message=f"Permission prompt tool failed closed: {message}",
            )

    return handle


def _parse_tool_reference(value: str) -> tuple[str | None, str]:
    normalized = value.strip()
    if normalized.startswith("mcp__"):
        parts = normalized.split("__", 2)
        if len(parts) != 3:
            raise ValueError("--permission-prompt-tool requires mcp__SERVER__TOOL, SERVER/TOOL, or a unique tool name.")
        server, name = parts[1], parts[2]
    elif "/" in normalized:
        parts = normalized.split("/", 1)
        server, name = parts[0], parts[1]
    else:
        server, name = None, normalized
    if not MCP_NAME_PATTERN.fullmatch(name) or (
        server is not None and not MCP_NAME_PATTERN.fullmatch(server)
    ):
        raise ValueError(
            "--permission-prompt-tool requires mcp__SERVER__TOOL, SERVER/TOOL, or a unique MCP tool name."
        )
    return server, name


def _request_arguments(request: ApprovalRequest) -> dict[str, object]:
    prompt_input: dict[str, object] = {
        "target": _bounded_text(request.target),
        "risk": _bounded_text(request.risk),
    }
    if request.preview is not None:
        prompt_input["preview"] = _bounded_text(request.preview)
    return {"tool_name": request.action_type, "input": prompt_input}


def _parse_decision(
    result: dict[str, Any],
    original_input: object,
    tool: PermissionPromptTool,
) -> ApprovalDecision:
    if bool(result.get("isError", False)):
        raise ValueError(f"{tool.qualified_name} reported an MCP tool error.")
    payload = _decision_payload(result)
    behavior = payload.get("behavior")
    if behavior == "allow":
        unknown = set(payload) - {"behavior", "updatedInput"}
        if unknown:
            raise ValueError("Permission allow response contains unsupported fields.")
        updated_input = payload.get("updatedInput", original_input)
        if updated_input != original_input:
            raise ValueError("Permission prompt tools cannot modify VibeAgent tool input.")
        return ApprovalDecision(
            approved=True,
            message=f"Approved by permission prompt tool {tool.qualified_name}.",
        )
    if behavior == "deny":
        unknown = set(payload) - {"behavior", "message"}
        message = payload.get("message")
        if unknown or not isinstance(message, str) or not message.strip():
            raise ValueError("Permission deny response requires only a non-empty message.")
        return ApprovalDecision(
            approved=False,
            message=_bounded_message(redact_sensitive_text(message.strip())),
        )
    raise ValueError("Permission prompt response behavior must be allow or deny.")


def _decision_payload(result: dict[str, Any]) -> dict[str, Any]:
    content = result.get("content")
    text_parts = [
        item["text"].strip()
        for item in content
        if isinstance(item, dict)
        and item.get("type") == "text"
        and isinstance(item.get("text"), str)
        and item["text"].strip()
    ] if isinstance(content, list) else []
    structured = result.get("structuredContent")
    if text_parts and structured is not None:
        raise ValueError("Permission prompt response cannot mix text and structured decisions.")
    if len(text_parts) > 1:
        raise ValueError("Permission prompt response must contain one JSON decision.")
    if text_parts:
        try:
            payload = json.loads(text_parts[0])
        except json.JSONDecodeError as error:
            raise ValueError("Permission prompt response text must be valid JSON.") from error
    else:
        payload = structured
    if not isinstance(payload, dict):
        raise ValueError("Permission prompt response must be a JSON object.")
    return payload


def _bounded_text(value: str) -> str:
    return redact_sensitive_text(value)[:MAX_PERMISSION_PROMPT_TEXT]


def _bounded_message(value: str) -> str:
    normalized = value.strip() or "unspecified error"
    return normalized[:MAX_PERMISSION_DECISION_MESSAGE]


__all__ = [
    "PermissionPromptTool",
    "build_mcp_permission_prompt_handler",
    "resolve_permission_prompt_tool",
]
