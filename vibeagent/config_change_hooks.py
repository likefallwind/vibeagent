from __future__ import annotations

from dataclasses import dataclass

from .agent_lifecycle_runtime import AgentLifecycleRuntime
from .agent_runtime_utils import append_session_event
from .redaction import redact_sensitive_text
from .session_config_state import (
    capture_config_target,
    config_targets,
    fingerprint_config_target,
    initialize_config_state,
    write_config_state,
)
from .workspace_core import RunWorkspace


@dataclass(frozen=True)
class ConfigChangeEvent:
    source: str
    file_path: str | None
    blocked: bool
    reason: str | None = None


@dataclass(frozen=True)
class ConfigChangePollResult:
    events: tuple[ConfigChangeEvent, ...] = ()
    system_messages: tuple[str, ...] = ()


class ConfigChangeHookRuntime:
    def __init__(
        self,
        workspace: RunWorkspace,
        lifecycle: AgentLifecycleRuntime,
    ) -> None:
        self.workspace = workspace
        self.lifecycle = lifecycle
        self._state = initialize_config_state(workspace)

    def poll(
        self,
        *,
        workspace: RunWorkspace | None = None,
        iteration: int = 0,
    ) -> ConfigChangePollResult:
        if workspace is not None and workspace != self.workspace:
            self.workspace = workspace
            self._state = initialize_config_state(workspace)
        events: list[ConfigChangeEvent] = []
        messages: list[str] = []
        dirty = False
        for target in config_targets(self.workspace):
            entry = self._state.setdefault(target.key, {})
            try:
                current = fingerprint_config_target(target)
            except (OSError, UnicodeDecodeError, ValueError) as error:
                message = f"ConfigChange could not inspect {target.path}: {redact_sensitive_text(str(error))}"
                messages.append(message)
                append_session_event(
                    self.workspace.session_dir,
                    "config_change_error",
                    {"source": target.source, "message": redact_sensitive_text(str(error))[:2_000]},
                )
                continue
            if current == entry.get("observed"):
                continue
            result = self.lifecycle.config_change(
                self.workspace,
                target.source,
                file_path=str(target.path),
                iteration=iteration,
            )
            messages.extend(result.system_messages)
            blocked = result.blocking_message is not None and target.source != "policy_settings"
            entry["observed"] = current
            reason = result.blocking_message if blocked else None
            if not blocked:
                try:
                    entry["accepted"] = capture_config_target(target)
                except (OSError, UnicodeDecodeError, ValueError) as error:
                    blocked = True
                    reason = f"Could not apply changed configuration: {redact_sensitive_text(str(error))}"
            if blocked and reason:
                messages.append(f"Config change blocked ({target.source}): {reason}")
            events.append(
                ConfigChangeEvent(
                    source=target.source,
                    file_path=str(target.path),
                    blocked=blocked,
                    reason=reason,
                )
            )
            append_session_event(
                self.workspace.session_dir,
                "config_changed",
                {
                    "source": target.source,
                    "file_path": str(target.path),
                    "blocked": blocked,
                    "reason": redact_sensitive_text(reason)[:2_000] if reason else None,
                },
            )
            dirty = True
        if dirty:
            write_config_state(self.workspace, self._state)
        return ConfigChangePollResult(tuple(events), tuple(messages))


__all__ = [
    "ConfigChangeEvent",
    "ConfigChangeHookRuntime",
    "ConfigChangePollResult",
]
