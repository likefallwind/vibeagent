from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .agent_observation_utils import observation_failed
from .lsp_client import LspClient
from .lsp_config import LspServerConfig, read_lsp_server_configs, select_lsp_server_from_configs
from .lsp_result_normalization import normalize_lsp_diagnostics
from .types import LspDiagnosticsObservation, Observation
from .workspace_core import RunWorkspace
from .workspace_resolve import display_workspace_path, resolve_inside_run


ClientProvider = Callable[[RunWorkspace, LspServerConfig], LspClient]
DIAGNOSTIC_MUTATIONS = {
    "write_file", "write_files", "edit_file", "multi_edit_file", "notebook_edit",
    "replace_python_definition", "code_rename", "python_rename", "replace_lines",
    "insert_lines", "append_file", "regex_replace", "json_set", "json_remove",
    "json_patch", "patch_file", "patch_files", "move_file", "move_files",
    "copy_file", "copy_files",
}


def collect_edit_diagnostics(
    workspace: RunWorkspace,
    observation: Observation,
    client_provider: ClientProvider,
) -> tuple[LspDiagnosticsObservation, ...]:
    if observation.kind not in DIAGNOSTIC_MUTATIONS or observation_failed(observation):
        return ()
    paths = _changed_file_paths(workspace, observation)
    if not paths:
        return ()
    try:
        configs = read_lsp_server_configs(workspace)
    except (OSError, UnicodeError, ValueError) as error:
        return (_failure_observation(workspace, paths[0], "plugin LSP", error),)
    grouped: dict[str, tuple[list[str], list[dict[str, object]], int, bool]] = {}
    for path in paths:
        if not path.is_relative_to(workspace.root):
            continue
        server_name = "plugin LSP"
        try:
            config = select_lsp_server_from_configs(configs, path)
            if config is None:
                continue
            server_name = config.name
            client = client_provider(workspace, config)
            target, uri, revision = client.ensure_document(path.relative_to(workspace.root).as_posix())
            raw = client.wait_for_diagnostics(uri, revision)
            diagnostics, total, truncated = normalize_lsp_diagnostics(workspace.root, target, raw, 200)
            selected = grouped.get(config.name, ([], [], 0, False))
            selected[0].append(target.relative_to(workspace.root).as_posix())
            selected[1].extend(diagnostics[: max(200 - len(selected[1]), 0)])
            grouped[config.name] = (
                selected[0], selected[1], selected[2] + total,
                selected[3] or truncated or selected[2] + total > 200,
            )
        except (OSError, UnicodeError, ValueError, TimeoutError) as error:
            return (_failure_observation(workspace, path, server_name, error),)
    return tuple(_success_observation(server, selected) for server, selected in sorted(grouped.items()))


def _success_observation(
    server: str, selected: tuple[list[str], list[dict[str, object]], int, bool]
) -> LspDiagnosticsObservation:
    return LspDiagnosticsObservation(
        kind="lsp_diagnostics",
        ok=True,
        server=server,
        paths=selected[0],
        diagnostics=selected[1],
        total=selected[2],
        truncated=selected[3],
        message=f"Automatic LSP diagnostics found {selected[2]} issue(s) in {len(selected[0])} file(s).",
    )


def _failure_observation(
    workspace: RunWorkspace, path: Path, server: str, error: BaseException
) -> LspDiagnosticsObservation:
    return LspDiagnosticsObservation(
        kind="lsp_diagnostics",
        ok=False,
        server=server,
        paths=[display_workspace_path(workspace, path)],
        diagnostics=[],
        total=0,
        truncated=False,
        message=f"Automatic LSP diagnostics failed: {error}",
    )


def _changed_file_paths(workspace: RunWorkspace, observation: Observation) -> list[Path]:
    candidates: list[str] = []
    for attribute in ("path", "definition_path", "destination"):
        value = getattr(observation, attribute, None)
        if isinstance(value, str) and value:
            candidates.append(value)
    for item in getattr(observation, "files", []) or []:
        value = item if isinstance(item, str) else getattr(item, "path", None)
        if isinstance(value, str) and value:
            candidates.append(value)
    for transfer in getattr(observation, "transfers", []) or []:
        value = getattr(transfer, "destination", None)
        if isinstance(value, str) and value:
            candidates.append(value)
    paths: list[Path] = []
    for value in candidates:
        try:
            path = resolve_inside_run(workspace, value)
        except ValueError:
            continue
        if path.is_file() and path not in paths:
            paths.append(path)
    return paths[:100]


__all__ = ["collect_edit_diagnostics"]
