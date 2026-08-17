from __future__ import annotations

from pathlib import Path

from .session_id import normalize_requested_session_id
from .workspace_core import BrowserMode, RunWorkspace, create_run_workspace


def create_requested_session_workspace(
    project_root: Path,
    session_id: str | None,
    *,
    mcp_config_paths: tuple[Path, ...] = (),
    strict_mcp_config: bool = False,
    additional_roots: tuple[Path, ...] = (),
    safe_mode: bool = False,
    bare_mode: bool = False,
    disable_slash_commands: bool = False,
    browser_mode: BrowserMode = "auto",
    exclude_dynamic_system_prompt_sections: bool = False,
    bypass_permissions_available: bool = False,
    setting_sources: tuple[str, ...] = ("user", "project", "local"),
    settings_override_json: str | None = None,
    invocation_plugin_dirs: tuple[Path, ...] = (),
) -> RunWorkspace | None:
    if session_id is None:
        return None
    return create_run_workspace(
        project_root,
        normalize_requested_session_id(session_id),
        mcp_config_paths=mcp_config_paths,
        strict_mcp_config=strict_mcp_config,
        additional_roots=additional_roots,
        safe_mode=safe_mode,
        bare_mode=bare_mode,
        disable_slash_commands=disable_slash_commands,
        browser_mode=browser_mode,
        exclude_dynamic_system_prompt_sections=exclude_dynamic_system_prompt_sections,
        bypass_permissions_available=bypass_permissions_available,
        setting_sources=setting_sources,
        settings_override_json=settings_override_json,
        invocation_plugin_dirs=invocation_plugin_dirs,
        require_new=True,
    )
