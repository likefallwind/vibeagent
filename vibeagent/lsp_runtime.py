from __future__ import annotations

import atexit
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from .lsp_client import LspClient
from .lsp_config import LspServerConfig, read_lsp_server_configs, select_lsp_server
from .lsp_edit_diagnostics import collect_edit_diagnostics
from .lsp_result_normalization import normalize_lsp_query_result
from .types import LspDiagnosticsObservation, LspQueryAction, LspQueryObservation, Observation
from .workspace_core import RunWorkspace
from .workspace_resolve import resolve_inside_run


_METHODS = {
    "goToDefinition": "textDocument/definition",
    "goToImplementation": "textDocument/implementation",
    "findReferences": "textDocument/references",
    "hover": "textDocument/hover",
    "documentSymbol": "textDocument/documentSymbol",
    "workspaceSymbol": "workspace/symbol",
}


@dataclass
class _ClientEntry:
    client: LspClient
    restarts: int = 0


_LOCK = RLock()
_CLIENTS: dict[tuple[Path, str], _ClientEntry] = {}


def execute_plugin_lsp_query(
    workspace: RunWorkspace, action: LspQueryAction
) -> LspQueryObservation | None:
    configs = _query_configs(workspace, action)
    if not configs:
        return None
    combined: list[dict[str, object]] = []
    total = 0
    truncated = False
    for config in configs:
        client = _client_for(workspace, config)
        params = _query_params(client, action)
        raw = client.request(_METHODS[action.operation], params)
        results, selected_total, selected_truncated = normalize_lsp_query_result(
            workspace.root, action.operation, raw, action.max_results
        )
        remaining = max(action.max_results - len(combined), 0)
        combined.extend(results[:remaining])
        total += selected_total
        truncated = truncated or selected_truncated or total > action.max_results
    servers = ", ".join(config.name for config in configs)
    return LspQueryObservation(
        kind="lsp_query",
        ok=True,
        server=servers,
        operation=action.operation,
        path=action.path,
        results=combined,
        total=total,
        truncated=truncated,
        message=f"LSP {action.operation} returned {total} result(s) from {servers}.",
    )


def automatic_lsp_diagnostics(
    workspace: RunWorkspace, observation: Observation
) -> tuple[LspDiagnosticsObservation, ...]:
    return collect_edit_diagnostics(workspace, observation, _client_for)


def close_project_lsp(project_root: Path) -> None:
    selected_root = project_root.resolve()
    with _LOCK:
        entries = [(_key, entry) for _key, entry in _CLIENTS.items() if _key[0] == selected_root]
        for key, _entry in entries:
            _CLIENTS.pop(key, None)
    for _key, entry in entries:
        entry.client.close()


def close_all_lsp_clients() -> None:
    with _LOCK:
        entries = list(_CLIENTS.values())
        _CLIENTS.clear()
    for entry in entries:
        entry.client.close()


def _query_configs(workspace: RunWorkspace, action: LspQueryAction) -> list[LspServerConfig]:
    if action.operation == "workspaceSymbol" and action.path is None:
        return read_lsp_server_configs(workspace)
    if action.path is None:
        return []
    target = resolve_inside_run(workspace, action.path)
    if not target.is_relative_to(workspace.root):
        return []
    selected = select_lsp_server(workspace, target)
    return [selected] if selected is not None else []


def _query_params(client: LspClient, action: LspQueryAction) -> dict[str, object]:
    if action.operation == "workspaceSymbol":
        return {"query": action.symbol or ""}
    assert action.path is not None
    _target, uri, _revision = client.ensure_document(action.path)
    document = {"uri": uri}
    if action.operation == "documentSymbol":
        return {"textDocument": document}
    line = action.line if action.line == 0 else (action.line or 1) - 1
    params: dict[str, object] = {
        "textDocument": document,
        "position": {"line": line, "character": action.character or 0},
    }
    if action.operation == "findReferences":
        params["context"] = {"includeDeclaration": True}
    return params


def _client_for(workspace: RunWorkspace, config: LspServerConfig) -> LspClient:
    key = (workspace.root.resolve(), config.name)
    with _LOCK:
        entry = _CLIENTS.get(key)
        if entry is not None and entry.client.config != config:
            _CLIENTS.pop(key)
            entry.client.close()
            entry = None
        if entry is not None and entry.client.running:
            return entry.client
        if entry is not None:
            if not config.restart_on_crash or entry.restarts >= config.max_restarts:
                raise ValueError(f"LSP server {config.name} exited and restart policy is exhausted.")
            restarts = entry.restarts + 1
            entry.client.close()
        else:
            restarts = 0
        client = LspClient(workspace.root, config)
        client.start()
        _CLIENTS[key] = _ClientEntry(client=client, restarts=restarts)
        return client


atexit.register(close_all_lsp_clients)


__all__ = [
    "automatic_lsp_diagnostics",
    "close_all_lsp_clients",
    "close_project_lsp",
    "execute_plugin_lsp_query",
]
