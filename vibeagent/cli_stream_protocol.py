from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from .cli_stream_output import JsonEventStream
from .config import resolve_provider_config
from .mcp_config import read_mcp_server_configs
from .plugin_store import enabled_plugin_manifests
from .redaction import redact_sensitive_text
from .workspace_core import RunWorkspace


MAX_STREAM_INIT_ITEMS = 100
MAX_STREAM_INIT_ERROR_CHARS = 1_000
STREAM_CAPABILITIES = (
    "api_retry_v1",
    "session_events_v1",
    "system_init_v1",
)


@dataclass
class StreamSessionObserver:
    stream: JsonEventStream
    workspace: RunWorkspace
    provider_env: Mapping[str, str | None]
    init_emitted: bool = False
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __call__(self, session_dir: Path, event: dict[str, Any]) -> None:
        with self._lock:
            event_type = str(event.get("type") or "")
            if event_type == "tool_catalog_initialized" and not self.init_emitted:
                self.init_emitted = True
                self.stream.system_init(
                    session_dir,
                    build_stream_init_payload(self.workspace, self.provider_env, event),
                )
            if event_type == "model_error" and event.get("will_retry") is True:
                self.stream.api_retry(session_dir, build_api_retry_payload(event))
            self.stream.session_event(session_dir, event)


def build_stream_init_payload(
    workspace: RunWorkspace,
    provider_env: Mapping[str, str | None],
    tool_event: Mapping[str, Any],
) -> dict[str, object]:
    tools = _bounded_strings(tool_event.get("tools"))
    payload: dict[str, object] = {
        "cwd": _bounded_text(workspace.root, limit=2_000),
        "tools": tools,
        "permissionMode": _bounded_text(tool_event.get("approval_policy") or "ask", limit=100),
        "capabilities": list(STREAM_CAPABILITIES),
    }
    raw_tools = tool_event.get("tools")
    if isinstance(raw_tools, list) and len(raw_tools) > MAX_STREAM_INIT_ITEMS:
        payload["tools_truncated"] = True
    try:
        provider = resolve_provider_config(provider_env)
    except Exception as error:
        payload["provider"] = _bounded_env_value(provider_env, "VIBEAGENT_PROVIDER") or "unknown"
        payload["model"] = _bounded_env_value(provider_env, "VIBEAGENT_MODEL") or "unknown"
        payload["provider_errors"] = [_bounded_error(error)]
    else:
        payload["provider"] = _bounded_text(provider.provider, limit=200)
        payload["model"] = _bounded_text(provider.model, limit=200)
    try:
        servers = read_mcp_server_configs(workspace)
    except Exception as error:
        payload["mcp_servers"] = []
        payload["mcp_server_errors"] = [_bounded_error(error)]
    else:
        payload["mcp_servers"] = [
            {"name": _bounded_text(server.name, limit=200), "status": "configured"}
            for server in servers[:MAX_STREAM_INIT_ITEMS]
        ]
        if len(servers) > MAX_STREAM_INIT_ITEMS:
            payload["mcp_servers_truncated"] = True
    try:
        manifests = enabled_plugin_manifests(workspace.root, workspace=workspace)
    except Exception as error:
        payload["plugins"] = []
        payload["plugin_errors"] = [_bounded_error(error)]
    else:
        payload["plugins"] = [
            {
                "name": _bounded_text(manifest.name, limit=200),
                "path": _bounded_text(manifest.root, limit=2_000),
                **(
                    {"version": _bounded_text(manifest.version, limit=200)}
                    if manifest.version is not None
                    else {}
                ),
            }
            for manifest in manifests[:MAX_STREAM_INIT_ITEMS]
        ]
        if len(manifests) > MAX_STREAM_INIT_ITEMS:
            payload["plugins_truncated"] = True
    return payload


def build_api_retry_payload(event: Mapping[str, Any]) -> dict[str, object]:
    attempts = _nonnegative_int(event.get("attempts"), default=1)
    payload: dict[str, object] = {
        "attempt": _nonnegative_int(event.get("attempt"), default=1),
        "max_retries": max(0, attempts - 1),
        "retry_delay_ms": _nonnegative_int(event.get("retry_delay_ms")),
        "error": _error_category(event.get("error")),
        "error_status": _optional_status(event),
        "uuid": str(uuid4()),
    }
    retry_reason = event.get("retry_reason")
    if isinstance(retry_reason, str) and retry_reason:
        payload["retry_reason"] = _bounded_text(retry_reason, limit=100)
    return payload


def _bounded_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_bounded_text(item, limit=200) for item in value[:MAX_STREAM_INIT_ITEMS]]


def _bounded_text(value: object, *, limit: int) -> str:
    return redact_sensitive_text(str(value))[:limit]


def _bounded_env_value(env: Mapping[str, str | None], key: str) -> str | None:
    value = env.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return _bounded_text(value.strip(), limit=200)


def _bounded_error(error: Exception) -> dict[str, str]:
    return {
        "type": type(error).__name__,
        "message": redact_sensitive_text(str(error))[:MAX_STREAM_INIT_ERROR_CHARS],
    }


def _nonnegative_int(value: object, *, default: int = 0) -> int:
    return value if isinstance(value, int) and value >= 0 else default


def _optional_status(event: Mapping[str, Any]) -> int | None:
    for key in ("error_status", "status", "status_code"):
        value = event.get(key)
        if isinstance(value, int) and 100 <= value <= 599:
            return value
    return None


def _error_category(value: object) -> str:
    normalized = str(value or "unknown")
    allowed = {
        "authentication_failed",
        "billing_error",
        "invalid_request",
        "max_output_tokens",
        "model_not_found",
        "oauth_org_not_allowed",
        "overloaded",
        "rate_limit",
        "server_error",
        "unknown",
    }
    return normalized if normalized in allowed else "unknown"


__all__ = [
    "STREAM_CAPABILITIES",
    "StreamSessionObserver",
    "build_api_retry_payload",
    "build_stream_init_payload",
]
