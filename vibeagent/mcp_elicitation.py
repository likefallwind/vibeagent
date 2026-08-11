from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .agent_lifecycle_hooks import run_lifecycle_hooks
from .agent_runtime_utils import append_session_event
from .mcp_elicitation_context import McpElicitationHandler
from .mcp_elicitation_protocol import (
    ElicitationRequest,
    normalize_elicitation_request,
    normalize_elicitation_response,
    prompt_for_elicitation_response,
)
from .redaction import redact_sensitive_text
from .types import AgentLogger, ApprovalHandler, ApprovalPolicy, UserInputHandler
from .workspace_core import RunWorkspace
from .workspace_hooks import ProjectHooks
from .workspace_permissions import ProjectPermissions


MAX_ELICITATION_DEPTH = 4


@dataclass
class McpElicitationRuntime:
    workspace: RunWorkspace
    hooks: ProjectHooks
    permissions: ProjectPermissions
    command_timeout_ms: int
    logger: AgentLogger | None
    approval_handler: ApprovalHandler | None
    approval_policy: ApprovalPolicy
    user_input_handler: UserInputHandler | None
    execute_action_safely: Any
    hook_model_runtime: Any = None
    iteration: int = 0
    depth: int = 0

    def handler(self) -> McpElicitationHandler:
        return self.handle

    def handle(self, server_name: str, raw_params: dict[str, Any]) -> dict[str, Any]:
        if self.depth >= MAX_ELICITATION_DEPTH:
            return {"action": "decline"}
        self.depth += 1
        try:
            request = normalize_elicitation_request(server_name, raw_params)
            _append_request_event(self.workspace, self.iteration, request)
            response = self._initial_response(request)
            response = self._apply_result_hooks(request, response)
            _append_response_event(self.workspace, self.iteration, request, response)
            return response
        except (EOFError, KeyboardInterrupt, OSError, RuntimeError, StopIteration, TypeError, ValueError) as error:
            append_session_event(
                self.workspace.session_dir,
                "mcp_elicitation_rejected",
                {
                    "iteration": self.iteration,
                    "server": server_name,
                    "message": redact_sensitive_text(str(error))[:2_000],
                },
            )
            return {"action": "decline"}
        finally:
            self.depth -= 1

    def _initial_response(self, request: ElicitationRequest) -> dict[str, Any]:
        pre = self._run_hooks("Elicitation", request.server_name, request.hook_fields)
        if pre.blocking_message is not None:
            return {"action": "decline"}
        if pre.elicitation_action is not None:
            return normalize_elicitation_response(
                request,
                pre.elicitation_action,
                pre.elicitation_content,
            )
        return prompt_for_elicitation_response(request, self.user_input_handler)

    def _apply_result_hooks(
        self,
        request: ElicitationRequest,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        result_fields: dict[str, object] = {
            "mcp_server_name": request.server_name,
            "action": response["action"],
            "mode": request.mode,
        }
        if request.elicitation_id is not None:
            result_fields["elicitation_id"] = request.elicitation_id
        if isinstance(response.get("content"), dict):
            result_fields["content"] = response["content"]
        post = self._run_hooks("ElicitationResult", request.server_name, result_fields)
        if post.blocking_message is not None:
            return {"action": "decline"}
        if post.elicitation_action is not None:
            return normalize_elicitation_response(
                request,
                post.elicitation_action,
                post.elicitation_content,
            )
        return response

    def _run_hooks(self, event: str, server_name: str, fields: dict[str, object]) -> Any:
        return run_lifecycle_hooks(
            self.workspace,
            self.hooks,
            event,
            server_name,
            fields,
            iteration=self.iteration,
            command_timeout_ms=self.command_timeout_ms,
            logger=self.logger,
            approval_handler=self.approval_handler,
            approval_policy=self.approval_policy,
            execute_action_safely_func=self.execute_action_safely,
            permissions=self.permissions,
            hook_model_runtime=self.hook_model_runtime,
        )


def _append_request_event(workspace: RunWorkspace, iteration: int, request: ElicitationRequest) -> None:
    append_session_event(
        workspace.session_dir,
        "mcp_elicitation_requested",
        {
            "iteration": iteration,
            "server": request.server_name,
            "mode": request.mode,
            "url_host": urlparse(request.url).hostname if request.url else None,
            "fields": sorted((request.schema or {}).get("properties", {})),
        },
    )


def _append_response_event(
    workspace: RunWorkspace,
    iteration: int,
    request: ElicitationRequest,
    response: dict[str, Any],
) -> None:
    append_session_event(
        workspace.session_dir,
        "mcp_elicitation_response",
        {
            "iteration": iteration,
            "server": request.server_name,
            "mode": request.mode,
            "action": response["action"],
            "fields": sorted(response.get("content", {})) if isinstance(response.get("content"), dict) else [],
        },
    )


__all__ = ["McpElicitationRuntime"]
