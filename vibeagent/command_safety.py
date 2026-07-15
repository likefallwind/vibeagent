from __future__ import annotations

from pathlib import Path
import re
import shlex

from .command_safety_args import args_after_operand, command_operands, first_command_operand
from .command_safety_gui import command_launches_gui_application
from .command_safety_heredoc import (
    interpreter_heredoc_blocked_command_reason,
    interpreter_stdin_script_args,
    shell_heredoc_script,
)
from .command_safety_high_risk import command_invokes_high_risk_executable
from .command_safety_network import (
    firewall_invocation_changes_network_state,
    ip_invocation_changes_network_state,
    iptables_invocation_changes_network_state,
    legacy_network_invocation_changes_state,
    nft_invocation_changes_network_state,
    sysctl_invocation_changes_kernel_state,
)
from .command_safety_node import (
    javascript_skip_ws,
    javascript_string_array_literal,
    javascript_string_literal,
    node_child_process_nested_command,
    node_destructured_binding_alias,
    node_import_default_aliases,
    node_import_named_aliases,
    node_one_liner_blocked_command_reason,
    node_require_assignment_aliases,
    node_require_destructured_aliases,
    node_script_blocked_command_reason,
)
from .command_safety_orchestration import (
    container_orchestration_invocation_changes_external_state,
    docker_compose_invocation_changes_external_state,
    docker_compose_options_with_values,
    docker_invocation_changes_external_state,
    docker_options_with_values,
    helm_invocation_changes_cluster_state,
    helm_options_with_values,
    kubectl_invocation_changes_cluster_state,
    kubectl_options_with_values,
)
from .command_safety_process import (
    fuser_invocation_kills_processes,
    kill_signal_token,
    kill_target_is_broad,
    matching_kill_options_with_values,
    parse_kill_signal_and_targets,
    parse_matching_kill_signal,
    process_signal_is_zero,
    process_termination_invocation_is_broad,
)
from .command_safety_python import (
    python_asyncio_subprocess_command,
    python_call_deletes_broad_path,
    python_call_is_compile,
    python_call_is_eval_or_exec,
    python_call_is_os_startfile,
    python_call_is_text_open,
    python_call_is_webbrowser_get,
    python_call_is_webbrowser_open,
    python_call_shell_command,
    python_call_string_argument,
    python_call_writes_raw_device,
    python_command_argument,
    python_dynamic_import_name,
    python_executable_command_from_args,
    python_expr_is_compile_reference,
    python_expr_is_eval_or_exec_reference,
    python_first_string_argument,
    python_getattr_attribute,
    python_literal_compile_script,
    python_literal_eval_exec_script,
    python_literal_source_text,
    python_one_liner_blocked_command_reason,
    python_open_call_writes_raw_device,
    python_os_exec_spawn_command,
    python_os_exec_spawn_function_name,
    python_os_open_call_writes_raw_device,
    python_os_open_flags_write,
    python_pathlib_call_path,
    python_pathlib_call_writes_raw_device,
    python_script_blocked_command_reason,
    python_static_getattr_target,
    python_string_constant,
    python_string_sequence,
)
from .command_safety_shell import (
    command_contains_dangerous_git_clean,
    command_contains_dangerous_rm,
    command_executes_powershell_network_script,
    command_path_arguments,
    command_pipes_network_script_to_shell,
    command_recursively_changes_broad_permissions,
    command_writes_to_device,
    is_dangerous_recursive_delete_target,
    is_raw_device_write_target,
    permission_invocation_targets_broad_path_recursively,
    segment_invokes_network_fetch,
    segment_invokes_script_interpreter,
    shell_command_invocations,
    shell_command_segments,
    shell_pipeline_segments,
    strip_env_command_prefix,
    unwrapped_shell_command_parts,
    unwrapped_shell_executable_name,
)
from .command_safety_storage import (
    invocation_has_raw_device_operand,
    losetup_invocation_changes_device_state,
    parted_invocation_changes_device_state,
    partition_editor_invocation_changes_device_state,
    partition_editor_options_with_values,
    sgdisk_invocation_mutates_partition_table,
    storage_invocation_changes_device_state,
)
from .command_safety_system import (
    first_systemctl_verb,
    service_invocation_changes_system_state,
    systemctl_invocation_changes_system_state,
)


def get_blocked_command_reason(command: str, _depth: int = 0) -> str | None:
    compact = " ".join(command.strip().split())
    lowered = compact.lower()
    if command_invokes_high_risk_executable(compact):
        return HIGH_RISK_COMMAND_BLOCK_REASON
    if command_contains_dangerous_rm(lowered):
        return RECURSIVE_DELETE_BLOCK_REASON
    if command_contains_dangerous_git_clean(lowered):
        return "forced git clean of untracked directories is not allowed in project mode"
    if command_recursively_changes_broad_permissions(lowered):
        return RECURSIVE_PERMISSION_BLOCK_REASON
    if command_writes_to_device(lowered):
        return RAW_DEVICE_WRITE_BLOCK_REASON
    if command_pipes_network_script_to_shell(lowered):
        return "network script piping is not allowed in project mode"
    if command_launches_gui_application(compact):
        return "GUI application launch commands are not allowed in project mode"
    heredoc_blocked = interpreter_heredoc_blocked_command_reason(command, _depth)
    if heredoc_blocked:
        return heredoc_blocked
    nested_python_blocked = python_one_liner_blocked_command_reason(compact, _depth)
    if nested_python_blocked:
        return nested_python_blocked
    nested_node_blocked = node_one_liner_blocked_command_reason(compact, _depth)
    if nested_node_blocked:
        return nested_node_blocked
    if command_executes_powershell_network_script(lowered):
        return "network script execution is not allowed in project mode"
    nested_blocked = shell_wrapped_blocked_command_reason(compact, _depth)
    if nested_blocked:
        return nested_blocked
    if ":(){:|:&};:" in lowered.replace(" ", ""):
        return "fork bomb pattern is not allowed in project mode"
    return None


RAW_DEVICE_WRITE_BLOCK_REASON = "raw device writes are not allowed in project mode"
HIGH_RISK_COMMAND_BLOCK_REASON = "high-risk command requires an explicit user-controlled approval flow"
RECURSIVE_DELETE_BLOCK_REASON = "recursive forced deletion of broad paths is not allowed in project mode"
RECURSIVE_PERMISSION_BLOCK_REASON = (
    "recursive permission or ownership changes of broad paths are not allowed in project mode"
)


def shell_wrapped_blocked_command_reason(command: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    parts = unwrapped_shell_command_parts(parts)
    if len(parts) < 3:
        return None
    executable = Path(parts[0]).name.lower()
    if executable not in {"bash", "sh", "zsh", "fish", "dash", "ksh"}:
        return None
    command_index = None
    for index, token in enumerate(parts[1:], start=1):
        if token == "--":
            continue
        if token.startswith("--"):
            continue
        if token.startswith("-") and "c" in token:
            command_index = index + 1
            break
    if command_index is None or command_index >= len(parts):
        return None
    nested_command = parts[command_index].strip()
    if not nested_command:
        return None
    return get_blocked_command_reason(nested_command, _depth=depth + 1)


__all__ = [
    "HIGH_RISK_COMMAND_BLOCK_REASON",
    "RAW_DEVICE_WRITE_BLOCK_REASON",
    "RECURSIVE_DELETE_BLOCK_REASON",
    "RECURSIVE_PERMISSION_BLOCK_REASON",
    "args_after_operand",
    "command_contains_dangerous_git_clean",
    "command_contains_dangerous_rm",
    "command_executes_powershell_network_script",
    "command_invokes_high_risk_executable",
    "command_launches_gui_application",
    "command_operands",
    "command_path_arguments",
    "command_pipes_network_script_to_shell",
    "command_recursively_changes_broad_permissions",
    "command_writes_to_device",
    "container_orchestration_invocation_changes_external_state",
    "docker_compose_invocation_changes_external_state",
    "docker_compose_options_with_values",
    "docker_invocation_changes_external_state",
    "docker_options_with_values",
    "firewall_invocation_changes_network_state",
    "first_command_operand",
    "first_systemctl_verb",
    "fuser_invocation_kills_processes",
    "get_blocked_command_reason",
    "helm_invocation_changes_cluster_state",
    "helm_options_with_values",
    "invocation_has_raw_device_operand",
    "interpreter_heredoc_blocked_command_reason",
    "interpreter_stdin_script_args",
    "ip_invocation_changes_network_state",
    "iptables_invocation_changes_network_state",
    "is_dangerous_recursive_delete_target",
    "is_raw_device_write_target",
    "javascript_skip_ws",
    "javascript_string_array_literal",
    "javascript_string_literal",
    "kill_signal_token",
    "kill_target_is_broad",
    "kubectl_invocation_changes_cluster_state",
    "kubectl_options_with_values",
    "legacy_network_invocation_changes_state",
    "losetup_invocation_changes_device_state",
    "matching_kill_options_with_values",
    "nft_invocation_changes_network_state",
    "node_child_process_nested_command",
    "node_destructured_binding_alias",
    "node_import_default_aliases",
    "node_import_named_aliases",
    "node_one_liner_blocked_command_reason",
    "node_require_assignment_aliases",
    "node_require_destructured_aliases",
    "node_script_blocked_command_reason",
    "parse_kill_signal_and_targets",
    "parse_matching_kill_signal",
    "parted_invocation_changes_device_state",
    "partition_editor_invocation_changes_device_state",
    "partition_editor_options_with_values",
    "permission_invocation_targets_broad_path_recursively",
    "process_signal_is_zero",
    "process_termination_invocation_is_broad",
    "python_asyncio_subprocess_command",
    "python_call_deletes_broad_path",
    "python_call_is_compile",
    "python_call_is_eval_or_exec",
    "python_call_is_os_startfile",
    "python_call_is_text_open",
    "python_call_is_webbrowser_get",
    "python_call_is_webbrowser_open",
    "python_call_shell_command",
    "python_call_string_argument",
    "python_call_writes_raw_device",
    "python_command_argument",
    "python_dynamic_import_name",
    "python_executable_command_from_args",
    "python_expr_is_compile_reference",
    "python_expr_is_eval_or_exec_reference",
    "python_first_string_argument",
    "python_getattr_attribute",
    "python_literal_compile_script",
    "python_literal_eval_exec_script",
    "python_literal_source_text",
    "python_one_liner_blocked_command_reason",
    "python_open_call_writes_raw_device",
    "python_os_exec_spawn_command",
    "python_os_exec_spawn_function_name",
    "python_os_open_call_writes_raw_device",
    "python_os_open_flags_write",
    "python_pathlib_call_path",
    "python_pathlib_call_writes_raw_device",
    "python_script_blocked_command_reason",
    "python_static_getattr_target",
    "python_string_constant",
    "python_string_sequence",
    "segment_invokes_network_fetch",
    "segment_invokes_script_interpreter",
    "service_invocation_changes_system_state",
    "sgdisk_invocation_mutates_partition_table",
    "shell_command_invocations",
    "shell_command_segments",
    "shell_heredoc_script",
    "shell_pipeline_segments",
    "shell_wrapped_blocked_command_reason",
    "storage_invocation_changes_device_state",
    "strip_env_command_prefix",
    "sysctl_invocation_changes_kernel_state",
    "systemctl_invocation_changes_system_state",
    "unwrapped_shell_command_parts",
    "unwrapped_shell_executable_name",
]
