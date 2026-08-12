from __future__ import annotations

from pathlib import Path

from .async_hook_runtime import close_session_async_hooks
from .dynamic_workflow_runtime import DynamicWorkflowManager
from .lsp_runtime import close_project_lsp
from .monitor_runtime import stop_session_monitors
from .peer_runtime import PeerSessionRuntime, create_peer_runtime
from .plugin_auto_update import PluginAutoUpdateNotification, PluginAutoUpdateRuntime
from .types import ApprovalPolicy
from .workspace_core import create_local_workspace


class InteractiveProjectRuntime:
    def __init__(
        self,
        project_root: Path,
        approval_policy: ApprovalPolicy,
        *,
        initial_session_id: str | None = None,
        safe_mode: bool = False,
        setting_sources: tuple[str, ...] = ("user", "project", "local"),
        settings_override_json: str | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.peer: PeerSessionRuntime | None = create_peer_runtime(
            self.project_root,
            approval_policy,
        )
        self.safe_mode = safe_mode
        self.setting_sources = setting_sources
        self.settings_override_json = settings_override_json
        self.plugin_updates = PluginAutoUpdateRuntime(self.project_root)
        if not safe_mode:
            self.plugin_updates.start()
        self.workflow: DynamicWorkflowManager | None = None
        self._owned_session_ids = (
            {initial_session_id} if initial_session_id is not None else set()
        )
        self._closed = False

    @property
    def owned_session_ids(self) -> frozenset[str]:
        return frozenset(self._owned_session_ids)

    def register_session(self, session_id: str) -> None:
        self._owned_session_ids.add(session_id)

    def collect_plugin_notifications(self) -> list[PluginAutoUpdateNotification]:
        return self.plugin_updates.collect_notifications()

    def update_approval_policy(self, approval_policy: ApprovalPolicy) -> None:
        if self.peer is not None:
            self.peer.update_approval_policy(approval_policy)

    def start_plugin_updates(self) -> bool:
        return False if self.safe_mode else self.plugin_updates.start()

    def set_workflow(self, workflow: DynamicWorkflowManager) -> DynamicWorkflowManager:
        self.close_workflow()
        self.workflow = workflow
        return workflow

    def close_workflow(self) -> None:
        if self.workflow is not None:
            self.workflow.close()
            self.workflow = None

    def close(
        self,
        additional_roots: tuple[Path, ...],
        *,
        close_lsp: bool = False,
    ) -> None:
        if self._closed:
            return
        self._closed = True
        for session_id in self._owned_session_ids:
            stop_session_monitors(self.project_root, session_id)
            close_session_async_hooks(
                create_local_workspace(
                    self.project_root,
                    session_id,
                    additional_roots=additional_roots,
                    safe_mode=self.safe_mode,
                    setting_sources=self.setting_sources,
                    settings_override_json=self.settings_override_json,
                )
            )
        self._owned_session_ids.clear()
        self.close_workflow()
        if self.peer is not None:
            self.peer.close()
            self.peer = None
        self.plugin_updates.close()
        if close_lsp:
            close_project_lsp(self.project_root)


__all__ = ["InteractiveProjectRuntime"]
