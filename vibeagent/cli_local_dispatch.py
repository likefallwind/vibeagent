from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import Any


LOCAL_FLAG_HANDLER_NAMES = (
    "run_project_local_flag",
    "run_command_local_flag",
    "run_read_local_flag",
    "run_python_local_flag",
    "run_json_local_flag",
    "run_text_edit_local_flag",
    "run_edit_local_flag",
    "run_patch_local_flag",
    "run_code_intel_local_flag",
    "run_git_local_flag",
    "run_runtime_local_flag",
    "run_review_local_flag",
    "run_session_local_flag",
    "run_checkpoint_local_flag",
)


def dispatch_local_flag(
    args: argparse.Namespace,
    project_root: Path | None,
    config_root: Path,
    provider_env: dict[str, str],
    command_namespace: Mapping[str, Any],
) -> tuple[str, dict[str, object]] | None:
    for handler_name in LOCAL_FLAG_HANDLER_NAMES:
        handler = command_namespace[handler_name]
        if handler_name == "run_project_local_flag":
            result = handler(args, project_root, config_root, provider_env, command_namespace)
        elif handler_name == "run_review_local_flag":
            result = handler(args, project_root, provider_env, command_namespace)
        else:
            result = handler(args, project_root, command_namespace)
        if result is not None:
            return result
    return None


__all__ = ["LOCAL_FLAG_HANDLER_NAMES", "dispatch_local_flag"]
