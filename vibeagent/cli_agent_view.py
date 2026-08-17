from __future__ import annotations

import argparse
from collections.abc import Callable
import os
from pathlib import Path

from .agent_view import ProjectAgentViewBackend, run_agent_view
from .background_agent_memory import resolve_background_agent_memory_limit
from .cli_additional_directories import resolve_additional_directories
from .cli_background_agent_attach import attach_background_agent_from_cli
from .cli_config import model_override_from_args, resolve_project_root
from .cli_mcp_args import resolve_mcp_config_paths
from .invocation_plugins import resolve_invocation_plugin_dirs
from .invocation_settings import parse_invocation_settings


def run_agent_view_from_cli(
    args: argparse.Namespace,
    *,
    run_interactive_func: Callable[[argparse.Namespace], int],
) -> int:
    invocation_root = Path.cwd()
    project_root = resolve_project_root(args.cwd) or Path.cwd()
    memory_limit_bytes = resolve_background_agent_memory_limit(
        args.background_memory_limit,
        os.environ,
    )
    dispatch_argv = build_agent_view_dispatch_argv(
        args,
        project_root=project_root,
        invocation_root=invocation_root,
    )
    outcome = run_agent_view(
        project_root,
        backend=ProjectAgentViewBackend(
            project_root,
            invocation_root,
            dispatch_argv=dispatch_argv,
            memory_limit_bytes=memory_limit_bytes,
        ),
        screen_reader=getattr(args, "ax_screen_reader", False),
    )
    if outcome.attach_id is None:
        return 0
    attached_args = argparse.Namespace(**vars(args))
    attached_args.agent_view = False
    attached_args.attach_background_agent = outcome.attach_id
    return attach_background_agent_from_cli(
        attached_args,
        run_interactive_func=run_interactive_func,
    )


def build_agent_view_dispatch_argv(
    args: argparse.Namespace,
    *,
    project_root: Path,
    invocation_root: Path,
) -> tuple[str, ...]:
    argv: list[str] = ["--approval", args.approval]
    _append_option(argv, "--provider", args.provider)
    _append_option(argv, "--model-name", model_override_from_args(args))
    _append_option(argv, "--effort", args.effort)
    _append_option(argv, "--agent", args.agent)
    _append_option(argv, "--agents", args.agents)

    settings = parse_invocation_settings(args.settings, invocation_root)
    _append_option(argv, "--settings", settings)
    _append_option(argv, "--setting-sources", args.setting_sources)

    for directory in resolve_additional_directories(
        args.add_dir,
        invocation_root=invocation_root,
    ):
        argv.extend(["--add-dir", directory.as_posix()])
    for path in resolve_mcp_config_paths(project_root, args.mcp_config):
        argv.extend(["--mcp-config", path.as_posix()])
    if args.strict_mcp_config:
        argv.append("--strict-mcp-config")
    for directory in resolve_invocation_plugin_dirs(
        args.plugin_dir,
        invocation_root=invocation_root,
        plugin_urls=args.plugin_url,
    ):
        argv.extend(["--plugin-dir", directory.as_posix()])
    return tuple(argv)


def _append_option(argv: list[str], option: str, value: object) -> None:
    if isinstance(value, str):
        argv.extend([option, value])


__all__ = ["build_agent_view_dispatch_argv", "run_agent_view_from_cli"]
