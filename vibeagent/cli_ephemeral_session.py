from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

from .project_trust import is_project_permissions_trusted
from .workspace_core import RunWorkspace, create_run_workspace, normalize_additional_roots


@dataclass(frozen=True)
class EphemeralSessionScope:
    workspace: RunWorkspace
    record_root: Path


@contextmanager
def ephemeral_session_scope(
    project_root: Path,
    *,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
    additional_roots: tuple[Path, ...] = (),
    safe_mode: bool = False,
) -> Iterator[EphemeralSessionScope]:
    with TemporaryDirectory(prefix="vibeagent-ephemeral-") as temporary:
        record_root = Path(temporary).resolve()
        temporary_workspace = create_run_workspace(record_root)
        workspace = replace(
            temporary_workspace,
            root=project_root.resolve(),
            project_config_trusted=is_project_permissions_trusted(project_root),
            mcp_config_paths=mcp_config_paths,
            strict_mcp_config=strict_mcp_config,
            additional_roots=normalize_additional_roots(project_root.resolve(), additional_roots),
            safe_mode=safe_mode,
        )
        yield EphemeralSessionScope(workspace=workspace, record_root=record_root)


__all__ = ["EphemeralSessionScope", "ephemeral_session_scope"]
