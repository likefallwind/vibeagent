from __future__ import annotations

import ast
from pathlib import Path
import re
import shlex

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
    if command_launches_gui_application(lowered):
        return "GUI application launch commands are not allowed in project mode"
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


def command_invokes_high_risk_executable(command: str) -> bool:
    for segment in shell_command_segments(command):
        parts = unwrapped_shell_command_parts(segment)
        if not parts:
            continue
        executable = Path(parts[0]).name.lower()
        if executable in {"sudo", "sudoedit", "doas", "pkexec", "su", "shutdown", "reboot", "halt", "poweroff"}:
            return True
        if executable == "mkfs" or executable.startswith("mkfs."):
            return True
        if executable in {
            "blkdiscard",
            "cfdisk",
            "fdisk",
            "gdisk",
            "losetup",
            "parted",
            "sfdisk",
            "sgdisk",
            "wipefs",
        } and storage_invocation_changes_device_state(executable, parts[1:]):
            return True
        if executable in {"insmod", "modprobe", "rmmod", "kexec"}:
            return True
        if executable == "sysctl" and sysctl_invocation_changes_kernel_state(parts[1:]):
            return True
        if executable in {"mount", "umount", "swapon", "swapoff"} and len(parts) > 1:
            return True
        if executable in {"kill", "pkill", "killall", "fuser"} and process_termination_invocation_is_broad(
            executable,
            parts[1:],
        ):
            return True
        if executable in {"docker", "docker-compose", "podman", "kubectl", "helm"} and (
            container_orchestration_invocation_changes_external_state(executable, parts[1:])
        ):
            return True
        if executable == "systemctl" and systemctl_invocation_changes_system_state(parts[1:]):
            return True
        if executable == "service" and service_invocation_changes_system_state(parts[1:]):
            return True
        if executable in {"iptables", "ip6tables", "ebtables", "arptables"} and (
            iptables_invocation_changes_network_state(parts[1:])
        ):
            return True
        if executable == "nft" and nft_invocation_changes_network_state(parts[1:]):
            return True
        if executable in {"ufw", "firewall-cmd", "pfctl"} and firewall_invocation_changes_network_state(
            executable,
            parts[1:],
        ):
            return True
        if executable == "ip" and ip_invocation_changes_network_state(parts[1:]):
            return True
        if executable in {"route", "ifconfig"} and legacy_network_invocation_changes_state(
            executable,
            parts[1:],
        ):
            return True
    return False


def systemctl_invocation_changes_system_state(args: list[str]) -> bool:
    verb = first_systemctl_verb(args)
    return verb in {
        "add-requires",
        "add-wants",
        "cancel",
        "daemon-reexec",
        "daemon-reload",
        "disable",
        "edit",
        "emergency",
        "enable",
        "halt",
        "hibernate",
        "hybrid-sleep",
        "import-environment",
        "isolate",
        "kexec",
        "kill",
        "link",
        "mask",
        "poweroff",
        "preset",
        "preset-all",
        "reenable",
        "reload",
        "reload-or-restart",
        "reload-or-try-restart",
        "reset-failed",
        "rescue",
        "restart",
        "revert",
        "set-default",
        "set-environment",
        "set-property",
        "start",
        "stop",
        "suspend",
        "suspend-then-hibernate",
        "switch-root",
        "try-reload-or-restart",
        "try-restart",
        "unmask",
        "unset-environment",
    }


def first_systemctl_verb(args: list[str]) -> str | None:
    options_with_values = {
        "--boot-loader-entry",
        "--host",
        "--image",
        "--machine",
        "--property",
        "--root",
        "--signal",
        "--state",
        "--type",
        "-H",
        "-M",
        "-P",
        "-S",
        "-s",
        "-t",
    }
    verb = first_command_operand(args, options_with_values)
    return verb.lower() if verb else None


def service_invocation_changes_system_state(args: list[str]) -> bool:
    operands = command_operands(args, options_with_values=set())
    if len(operands) < 2:
        return False
    action = operands[1].lower()
    return action in {
        "condrestart",
        "force-reload",
        "reload",
        "restart",
        "start",
        "stop",
        "try-restart",
    }


def storage_invocation_changes_device_state(executable: str, args: list[str]) -> bool:
    if executable == "wipefs":
        return invocation_has_raw_device_operand(args) and any(
            token.lower() in {"-a", "--all"} for token in args
        )
    if executable == "blkdiscard":
        return invocation_has_raw_device_operand(args)
    if executable == "sgdisk":
        return invocation_has_raw_device_operand(args) and sgdisk_invocation_mutates_partition_table(args)
    if executable == "parted":
        return parted_invocation_changes_device_state(args)
    if executable in {"fdisk", "gdisk", "cfdisk", "sfdisk"}:
        return partition_editor_invocation_changes_device_state(executable, args)
    if executable == "losetup":
        return losetup_invocation_changes_device_state(args)
    return False


def container_orchestration_invocation_changes_external_state(executable: str, args: list[str]) -> bool:
    if executable in {"docker", "podman"}:
        return docker_invocation_changes_external_state(args)
    if executable == "docker-compose":
        return docker_compose_invocation_changes_external_state(args)
    if executable == "kubectl":
        return kubectl_invocation_changes_cluster_state(args)
    if executable == "helm":
        return helm_invocation_changes_cluster_state(args)
    return False


def docker_invocation_changes_external_state(args: list[str]) -> bool:
    operands = command_operands(args, docker_options_with_values())
    if not operands:
        return False
    command = operands[0].lower()
    if command == "compose":
        return docker_compose_invocation_changes_external_state(args_after_operand(args, "compose"))
    if command in {"rm", "rmi"}:
        return len(operands) > 1
    if command in {"builder", "container", "image", "network", "system", "volume"}:
        subcommand = operands[1].lower() if len(operands) > 1 else None
        return subcommand in {"prune", "rm", "remove"}
    return False


def docker_options_with_values() -> set[str]:
    return {
        "-c",
        "-H",
        "-l",
        "--config",
        "--context",
        "--host",
        "--log-level",
        "--tlscacert",
        "--tlscert",
        "--tlskey",
    }


def docker_compose_invocation_changes_external_state(args: list[str]) -> bool:
    operands = command_operands(args, docker_compose_options_with_values())
    if not operands:
        return False
    command = operands[0].lower()
    if command == "rm":
        return True
    if command == "down":
        return any(token.lower() in {"-v", "--volumes"} for token in args)
    return False


def docker_compose_options_with_values() -> set[str]:
    return {
        "-f",
        "-p",
        "--ansi",
        "--compatibility",
        "--env-file",
        "--file",
        "--parallel",
        "--profile",
        "--project-directory",
        "--project-name",
        "--progress",
    }


def kubectl_invocation_changes_cluster_state(args: list[str]) -> bool:
    operands = command_operands(args, kubectl_options_with_values())
    if not operands:
        return False
    verb = operands[0].lower()
    if verb in {
        "annotate",
        "apply",
        "autoscale",
        "cordon",
        "create",
        "delete",
        "drain",
        "edit",
        "expose",
        "label",
        "patch",
        "replace",
        "run",
        "scale",
        "taint",
        "uncordon",
    }:
        return True
    if verb == "rollout":
        subcommand = operands[1].lower() if len(operands) > 1 else None
        return subcommand in {"restart", "undo"}
    return False


def kubectl_options_with_values() -> set[str]:
    return {
        "-A",
        "-c",
        "-C",
        "-f",
        "-k",
        "-n",
        "-o",
        "-s",
        "--as",
        "--as-group",
        "--as-uid",
        "--cache-dir",
        "--certificate-authority",
        "--client-certificate",
        "--client-key",
        "--cluster",
        "--context",
        "--field-manager",
        "--filename",
        "--kubeconfig",
        "--kustomize",
        "--namespace",
        "--output",
        "--request-timeout",
        "--selector",
        "--server",
        "--token",
        "--user",
    }


def helm_invocation_changes_cluster_state(args: list[str]) -> bool:
    verb = first_command_operand(args, helm_options_with_values())
    return (verb.lower() if verb else None) in {
        "delete",
        "install",
        "rollback",
        "uninstall",
        "upgrade",
    }


def helm_options_with_values() -> set[str]:
    return {
        "-k",
        "-n",
        "--burst-limit",
        "--kube-apiserver",
        "--kube-as-group",
        "--kube-as-user",
        "--kube-ca-file",
        "--kube-context",
        "--kube-token",
        "--kubeconfig",
        "--namespace",
        "--registry-config",
        "--repository-cache",
        "--repository-config",
    }


def args_after_operand(args: list[str], operand: str) -> list[str]:
    for index, token in enumerate(args):
        if token.lower() == operand:
            return args[index + 1 :]
    return []


def invocation_has_raw_device_operand(args: list[str], options_with_values: set[str] | None = None) -> bool:
    return any(
        is_raw_device_write_target(operand)
        for operand in command_operands(args, options_with_values or set())
    )


def sgdisk_invocation_mutates_partition_table(args: list[str]) -> bool:
    mutating_long_options = {
        "--attributes",
        "--change-name",
        "--clear",
        "--delete",
        "--hybrid",
        "--largest-new",
        "--load-backup",
        "--move-second-header",
        "--new",
        "--randomize-guids",
        "--replicate",
        "--resize-table",
        "--sort",
        "--transpose",
        "--typecode",
        "--zap",
        "--zap-all",
    }
    mutating_short_flags = {
        "A",
        "c",
        "d",
        "e",
        "G",
        "h",
        "l",
        "n",
        "N",
        "o",
        "r",
        "R",
        "s",
        "t",
        "z",
        "Z",
    }
    for token in args:
        option = token.split("=", 1)[0]
        if option.lower() in mutating_long_options:
            return True
        if option.startswith("--"):
            continue
        if option.startswith("-") and option != "-":
            if any(flag in mutating_short_flags for flag in option[1:]):
                return True
    return False


def parted_invocation_changes_device_state(args: list[str]) -> bool:
    operands = command_operands(args, options_with_values={"-a", "--align"})
    for index, operand in enumerate(operands):
        if not is_raw_device_write_target(operand):
            continue
        if index + 1 >= len(operands):
            return True
        action = operands[index + 1].lower()
        return action in {
            "disk_set",
            "disk_toggle",
            "mklabel",
            "mktable",
            "mkpart",
            "name",
            "rescue",
            "resizepart",
            "rm",
            "set",
            "toggle",
        }
    return False


def partition_editor_invocation_changes_device_state(executable: str, args: list[str]) -> bool:
    if not invocation_has_raw_device_operand(args, partition_editor_options_with_values(executable)):
        return False
    lowered_options = {arg.lower().split("=", 1)[0] for arg in args if arg.startswith("-")}
    if executable == "fdisk":
        return not bool(lowered_options & {"-l", "--list"})
    if executable == "sfdisk":
        return not bool(
            lowered_options & {"-d", "--dump", "-l", "--list", "-v", "--verify", "-j", "--json"}
        )
    if executable in {"gdisk", "cfdisk"}:
        return not bool(lowered_options & {"-l", "--list"})
    return False


def partition_editor_options_with_values(executable: str) -> set[str]:
    if executable == "fdisk":
        return {
            "-b",
            "-C",
            "-H",
            "-S",
            "-u",
            "--sector-size",
            "--cylinders",
            "--heads",
            "--sectors",
        }
    if executable == "sfdisk":
        return {"-B", "-N", "-O", "-I", "-X", "--backup-file", "--partno", "--label"}
    if executable == "cfdisk":
        return {"-L", "--color", "--lock"}
    return set()


def losetup_invocation_changes_device_state(args: list[str]) -> bool:
    for token in args:
        lowered = token.lower()
        option = lowered.split("=", 1)[0]
        if option in {"--detach", "--detach-all", "--partscan", "--set-capacity"}:
            return True
        if option.startswith("--"):
            continue
        if option.startswith("-") and any(flag in {"c", "d", "D", "P"} for flag in token[1:]):
            return True
    operands = command_operands(
        args,
        options_with_values={
            "-b",
            "-j",
            "-L",
            "-o",
            "--associated",
            "--label",
            "--loop-ref",
            "--offset",
            "--sector-size",
            "--sizelimit",
        },
    )
    if any(token.lower() in {"-f", "--find"} for token in args):
        return bool(operands)
    return len(operands) >= 2


def process_termination_invocation_is_broad(executable: str, args: list[str]) -> bool:
    if executable == "kill":
        signal, targets, read_only = parse_kill_signal_and_targets(args)
        if read_only or process_signal_is_zero(signal):
            return False
        return any(kill_target_is_broad(target) for target in targets)
    if executable in {"pkill", "killall"}:
        signal = parse_matching_kill_signal(args)
        if process_signal_is_zero(signal):
            return False
        return bool(command_operands(args, options_with_values=matching_kill_options_with_values(executable)))
    if executable == "fuser":
        return fuser_invocation_kills_processes(args)
    return False


def parse_kill_signal_and_targets(args: list[str]) -> tuple[str | None, list[str], bool]:
    signal: str | None = None
    targets: list[str] = []
    signal_seen = False
    parse_options = True
    expect_signal = False
    read_only = False
    for token in args:
        lowered = token.lower()
        if expect_signal:
            signal = token
            signal_seen = True
            expect_signal = False
            continue
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and lowered in {"-l", "--list", "-L", "--table"}:
            read_only = True
            continue
        if parse_options and lowered in {"-s", "--signal", "-n"}:
            expect_signal = True
            continue
        if parse_options and lowered.startswith("--signal="):
            signal = token.split("=", 1)[1]
            signal_seen = True
            continue
        if parse_options and token.startswith("-") and not signal_seen and kill_signal_token(token):
            signal = token[1:]
            signal_seen = True
            continue
        targets.append(token)
    return signal, targets, read_only


def kill_signal_token(token: str) -> bool:
    signal = token[1:]
    if signal.isdigit():
        return True
    return signal.lower().removeprefix("sig") in {
        "hup",
        "int",
        "quit",
        "kill",
        "term",
        "usr1",
        "usr2",
        "stop",
        "cont",
        "abrt",
        "alrm",
    }


def process_signal_is_zero(signal: str | None) -> bool:
    if signal is None:
        return False
    return signal.lower().removeprefix("sig") == "0"


def kill_target_is_broad(target: str) -> bool:
    if target in {"0", "1"}:
        return True
    return target.startswith("-") and target[1:].isdigit()


def parse_matching_kill_signal(args: list[str]) -> str | None:
    expect_signal = False
    for token in args:
        lowered = token.lower()
        if expect_signal:
            return token
        if lowered in {"-s", "--signal"}:
            expect_signal = True
            continue
        if lowered.startswith("--signal="):
            return token.split("=", 1)[1]
        if token.startswith("-") and kill_signal_token(token):
            return token[1:]
    return None


def matching_kill_options_with_values(executable: str) -> set[str]:
    shared = {
        "-g",
        "-n",
        "-o",
        "-P",
        "-s",
        "-u",
        "-U",
        "--older",
        "--parent",
        "--signal",
        "--uid",
        "--user",
    }
    if executable == "pkill":
        return shared | {"-G", "-t", "--group", "--pgroup", "--terminal"}
    return shared | {
        "-e",
        "-I",
        "-i",
        "-r",
        "-y",
        "--exact",
        "--ignore-case",
        "--interactive",
        "--regexp",
        "--younger-than",
    }


def fuser_invocation_kills_processes(args: list[str]) -> bool:
    for token in args:
        lowered = token.lower()
        option = lowered.split("=", 1)[0]
        if option == "--kill":
            return True
        if option.startswith("--"):
            continue
        if option.startswith("-") and "k" in option[1:]:
            return True
    return False


def first_command_operand(args: list[str], options_with_values: set[str]) -> str | None:
    operands = command_operands(args, options_with_values)
    return operands[0] if operands else None


def command_operands(args: list[str], options_with_values: set[str]) -> list[str]:
    operands: list[str] = []
    parse_options = True
    skip_next = False
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and token.startswith("-") and token != "-":
            option = token.split("=", 1)[0]
            if "=" not in token and option in options_with_values:
                skip_next = True
            continue
        operands.append(token)
    return operands


def sysctl_invocation_changes_kernel_state(args: list[str]) -> bool:
    for token in args:
        lowered = token.lower()
        if lowered in {"-w", "--write", "-p", "--load", "--system"}:
            return True
        if lowered.startswith("--load="):
            return True
        if not lowered.startswith("-") and "=" in token:
            return True
    return False


def iptables_invocation_changes_network_state(args: list[str]) -> bool:
    mutating_long_options = {
        "--append",
        "--delete",
        "--insert",
        "--replace",
        "--flush",
        "--zero",
        "--new-chain",
        "--delete-chain",
        "--policy",
        "--rename-chain",
    }
    mutating_short_flags = {"A", "D", "I", "R", "F", "Z", "N", "X", "P", "E"}
    for token in args:
        option = token.split("=", 1)[0]
        lowered_option = option.lower()
        if lowered_option in mutating_long_options:
            return True
        if option.startswith("--"):
            continue
        if option.startswith("-") and option != "-":
            if any(flag in mutating_short_flags for flag in option[1:]):
                return True
    return False


def nft_invocation_changes_network_state(args: list[str]) -> bool:
    for token in args:
        lowered = token.lower()
        if lowered in {"-f", "--file"} or lowered.startswith("--file="):
            return True
    verb = first_command_operand(args, options_with_values={"-I", "-i", "--includepath", "--numeric", "-n"})
    return (verb.lower() if verb else None) in {
        "add",
        "create",
        "delete",
        "flush",
        "import",
        "insert",
        "rename",
        "replace",
        "reset",
    }


def firewall_invocation_changes_network_state(executable: str, args: list[str]) -> bool:
    lowered_args = [arg.lower() for arg in args]
    if executable == "ufw":
        action = first_command_operand(lowered_args, options_with_values=set())
        return action in {
            "allow",
            "default",
            "delete",
            "deny",
            "disable",
            "enable",
            "insert",
            "limit",
            "logging",
            "reject",
            "reload",
            "reset",
        }
    if executable == "firewall-cmd":
        mutating_exact = {
            "--complete-reload",
            "--lockdown-off",
            "--lockdown-on",
            "--panic-off",
            "--panic-on",
            "--reload",
        }
        mutating_prefixes = (
            "--add-",
            "--change-",
            "--delete-",
            "--new-",
            "--remove-",
            "--set-",
        )
        for token in lowered_args:
            option = token.split("=", 1)[0]
            if option in mutating_exact or option.startswith(mutating_prefixes):
                return True
        return False
    if executable == "pfctl":
        for token in args:
            if token.startswith("--"):
                continue
            if token.startswith("-") and token != "-":
                if any(flag in {"e", "d", "f", "F"} for flag in token[1:]):
                    return True
        return False
    return False


def ip_invocation_changes_network_state(args: list[str]) -> bool:
    operands = [
        operand.lower()
        for operand in command_operands(
            args,
            options_with_values={"-b", "-batch", "-f", "-family", "-n", "-netns", "-rcvbuf"},
        )
    ]
    if len(operands) < 2:
        return False
    subject, action = operands[0], operands[1]
    if subject in {"address", "addr"}:
        return action in {"add", "append", "change", "delete", "del", "flush", "replace"}
    if subject == "link":
        return action in {"add", "delete", "del", "set"}
    if subject in {
        "neighbour",
        "neighbor",
        "neigh",
        "netns",
        "route",
        "rule",
        "tunnel",
        "xfrm",
    }:
        return action in {"add", "append", "change", "delete", "del", "flush", "replace", "set"}
    return False


def legacy_network_invocation_changes_state(executable: str, args: list[str]) -> bool:
    operands = [operand.lower() for operand in command_operands(args, options_with_values=set())]
    if executable == "route":
        action = operands[0] if operands else None
        return action in {"add", "change", "delete", "del"}
    if executable == "ifconfig":
        return len(operands) > 1
    return False


def shell_command_segments(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and all(character in ";&|" for character in token):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def unwrapped_shell_executable_name(parts: list[str]) -> str | None:
    remaining = unwrapped_shell_command_parts(parts)
    return Path(remaining[0]).name.lower() if remaining else None


def unwrapped_shell_command_parts(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        executable = Path(remaining[0]).name.lower()
        if executable in {"nohup", "setsid"}:
            remaining = remaining[1:]
            continue
        if executable == "env":
            remaining = strip_env_command_prefix(remaining[1:])
            continue
        break
    return remaining


def strip_env_command_prefix(parts: list[str]) -> list[str]:
    remaining = list(parts)
    while remaining:
        token = remaining[0]
        if token == "--":
            return remaining[1:]
        if token in {"-u", "--unset", "--chdir", "-C"}:
            remaining = remaining[2:] if len(remaining) > 1 else []
            continue
        if token.startswith("-"):
            remaining = remaining[1:]
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            remaining = remaining[1:]
            continue
        break
    return remaining


def shell_wrapped_blocked_command_reason(command: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    while parts:
        executable = Path(parts[0]).name.lower()
        if executable in {"nohup", "setsid"}:
            parts = parts[1:]
            continue
        if executable == "env":
            parts = parts[1:]
            while parts and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[0]):
                parts = parts[1:]
            continue
        break
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


def command_contains_dangerous_rm(lowered_command: str) -> bool:
    for args in shell_command_invocations(lowered_command, "rm"):
        recursive = False
        force = False
        targets: list[str] = []
        parse_options = True
        for token in args:
            if parse_options and token == "--":
                parse_options = False
                continue
            if parse_options and token.startswith("--"):
                option = token.split("=", 1)[0]
                if option == "--recursive":
                    recursive = True
                elif option == "--force":
                    force = True
                continue
            if parse_options and token.startswith("-") and token != "-":
                flags = token[1:]
                if "r" in flags:
                    recursive = True
                if "f" in flags:
                    force = True
                continue
            targets.append(token)
        if not recursive or not force:
            continue
        for target in targets:
            if is_dangerous_recursive_delete_target(target):
                return True
    return False


def is_dangerous_recursive_delete_target(path: str) -> bool:
    dangerous_targets = {
        "/",
        "/*",
        ".",
        "./",
        "*",
        "~",
        "~/",
        "$home",
        "${home}",
        "/home",
        "/home/",
        "/tmp",
        "/tmp/",
        "/var",
        "/var/",
        "/usr",
        "/usr/",
    }
    target = path.strip().strip("'\"").casefold()
    normalized = target.rstrip("/") if target not in {"/", "./", "~/"} else target
    return target in dangerous_targets or normalized in dangerous_targets


def command_contains_dangerous_git_clean(lowered_command: str) -> bool:
    for args in shell_command_invocations(lowered_command, "git"):
        if not args or args[0] != "clean":
            continue
        force = False
        directories = False
        dry_run = False
        for token in args[1:]:
            if token in {"--dry-run", "-n"}:
                dry_run = True
                continue
            if token == "--force":
                force = True
                continue
            if token == "--directory":
                directories = True
                continue
            if token.startswith("-") and not token.startswith("--"):
                flags = token.lstrip("-")
                if "f" in flags:
                    force = True
                if "d" in flags:
                    directories = True
                if "n" in flags:
                    dry_run = True
        if force and directories and not dry_run:
            return True
    return False


def command_recursively_changes_broad_permissions(lowered_command: str) -> bool:
    for executable in ("chmod", "chown", "chgrp"):
        for args in shell_command_invocations(lowered_command, executable):
            if permission_invocation_targets_broad_path_recursively(args):
                return True
    return False


def permission_invocation_targets_broad_path_recursively(args: list[str]) -> bool:
    recursive = False
    uses_reference = False
    operands: list[str] = []
    parse_options = True
    skip_next_option_arg = False
    for token in args:
        if skip_next_option_arg:
            skip_next_option_arg = False
            continue
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and token == "--reference":
            uses_reference = True
            skip_next_option_arg = True
            continue
        if parse_options and token.startswith("--"):
            option = token.split("=", 1)[0]
            if option == "--recursive":
                recursive = True
            elif option == "--reference":
                uses_reference = True
            continue
        if parse_options and token.startswith("-") and token != "-":
            flags = token.lstrip("-")
            if "r" in flags:
                recursive = True
            continue
        operands.append(token)
    if not recursive:
        return False
    target_start = 0 if uses_reference else 1
    targets = operands[target_start:]
    return any(is_dangerous_recursive_delete_target(target) for target in targets)


def shell_command_invocations(lowered_command: str, executable_name: str) -> list[list[str]]:
    invocations: list[list[str]] = []
    executable_path = r"(?:[^\s;&|]*/)?"
    pattern = re.compile(rf"(^|[;&|]\s*){executable_path}{re.escape(executable_name)}(?=\s|$)(?P<args>[^;&|]*)")
    for match in pattern.finditer(lowered_command):
        try:
            invocations.append(shlex.split(match.group("args")))
        except ValueError:
            continue
    return invocations


def command_writes_to_device(lowered_command: str) -> bool:
    for target in re.findall(r"(?:^|[\s;&|])(?:\d?>|>>|>|&>)\s*(/dev/[^\s;&|]+)", lowered_command):
        if is_raw_device_write_target(target):
            return True
    for target in re.findall(r"\bof=(/dev/[^\s;&|]+)", lowered_command):
        if is_raw_device_write_target(target):
            return True
    for args in shell_command_invocations(lowered_command, "tee"):
        if any(is_raw_device_write_target(token) for token in command_path_arguments(args)):
            return True
    for args in shell_command_invocations(lowered_command, "cp"):
        paths = command_path_arguments(args)
        if paths and is_raw_device_write_target(paths[-1]):
            return True
    return False


def command_path_arguments(args: list[str]) -> list[str]:
    paths: list[str] = []
    parse_options = True
    for token in args:
        if parse_options and token == "--":
            parse_options = False
            continue
        if parse_options and token.startswith("-") and token != "-":
            continue
        paths.append(token)
    return paths


def is_raw_device_write_target(path: str) -> bool:
    normalized = path.strip().strip("'\"")
    if not normalized.startswith("/dev/"):
        return False
    safe_character_devices = {
        "/dev/null",
        "/dev/zero",
        "/dev/full",
        "/dev/random",
        "/dev/urandom",
    }
    if normalized in safe_character_devices:
        return False
    raw_device_patterns = (
        r"/dev/[svhx]d[a-z]\d*",
        r"/dev/nvme\d+n\d+(?:p\d+)?",
        r"/dev/mmcblk\d+(?:p\d+)?",
        r"/dev/loop\d+",
        r"/dev/mapper/[^/]+",
        r"/dev/disk/(?:by-id|by-path|by-uuid|by-label)/[^/]+",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in raw_device_patterns)


def command_pipes_network_script_to_shell(lowered_command: str) -> bool:
    segments = shell_pipeline_segments(lowered_command)
    if len(segments) < 2:
        return False
    for index, segment in enumerate(segments[:-1]):
        if not segment_invokes_network_fetch(segment):
            continue
        for sink in segments[index + 1 :]:
            if segment_invokes_script_interpreter(sink):
                return True
    return False


def shell_pipeline_segments(command: str) -> list[list[str]]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars="|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token and all(character == "|" for character in token):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def segment_invokes_network_fetch(parts: list[str]) -> bool:
    executable = unwrapped_shell_executable_name(parts)
    return executable in {"curl", "wget"}


def segment_invokes_script_interpreter(parts: list[str]) -> bool:
    executable = unwrapped_shell_executable_name(parts)
    return executable in {"sh", "bash", "zsh", "fish", "dash", "ksh", "python", "python3", "ruby", "perl", "node"}


def command_executes_powershell_network_script(lowered_command: str) -> bool:
    segment = r"(^|[;&|]\s*)"
    wrappers = r"(?:(?:nohup|setsid)\s+|env\s+(?:(?:--|-[A-Za-z0-9_-]+|[a-z_][a-z0-9_]*=\S+)\s+)*)*"
    executable_path = r"(?:[^\s;&|]*/)?"
    powershell = rf"{executable_path}(?:powershell|pwsh)(?:\.exe)?\b"
    fetch = r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b"
    execute = r"\|\s*(?:[^\s;&|]*/)?(?:iex|invoke-expression)\b"
    return bool(re.search(segment + wrappers + powershell + r".*" + fetch + r".*" + execute, lowered_command))


def command_launches_gui_application(lowered_command: str) -> bool:
    segment = r"(^|[;&|]\s*)"
    wrappers = r"(?:nohup\s+|setsid\s+|env\s+(?:[a-z_][a-z0-9_]*=\S+\s+)*)?"
    executable_path = r"(?:[./~]?\S*[/\\])?"
    launcher = (
        r"(?:explorer(?:\.exe)?|xdg-open|wslview|wsl-open|gio\s+open|"
        r"gnome-open|kde-open(?:5)?|open|nautilus|dolphin|thunar|nemo|pcmanfm|caja|konqueror|"
        r"code|code-insiders|cursor|windsurf|subl|mate|gedit|mousepad|kate|"
        r"firefox|google-chrome|google-chrome-stable|chromium|chromium-browser|microsoft-edge)\b"
    )
    file_protocol_handler = r"rundll32(?:\.exe)?\s+url\.dll,fileprotocolhandler\b"
    bare_start_gui = r"start\b\s+(?:\"[^\"]*\"\s+)?(?:\.|~|/|[a-z]:[\\/]|https?://|file:)"
    cmd_shell_gui = rf"{executable_path}cmd(?:\.exe)?\s+/[cs]\s+(?:{bare_start_gui}|explorer(?:\.exe)?\b|{file_protocol_handler})"
    powershell_gui = (
        rf"{executable_path}(?:powershell|pwsh)(?:\.exe)?\b.*\b"
        rf"(?:start-process|invoke-item|ii|explorer(?:\.exe)?|{file_protocol_handler})\b"
    )
    python_webbrowser = r"python(?:3(?:\.\d+)?)?\s+-m\s+webbrowser\b"
    return bool(
        re.search(segment + wrappers + executable_path + launcher, lowered_command)
        or re.search(segment + wrappers + executable_path + file_protocol_handler, lowered_command)
        or re.search(segment + wrappers + bare_start_gui, lowered_command)
        or re.search(segment + wrappers + cmd_shell_gui, lowered_command)
        or re.search(segment + wrappers + powershell_gui, lowered_command)
        or re.search(segment + wrappers + python_webbrowser, lowered_command)
    )


def python_one_liner_blocked_command_reason(command: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    while parts:
        executable = Path(parts[0]).name.lower()
        if executable in {"nohup", "setsid"}:
            parts = parts[1:]
            continue
        if executable == "env":
            parts = parts[1:]
            while parts and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[0]):
                parts = parts[1:]
            continue
        break
    if len(parts) < 2 or not re.fullmatch(r"python(?:3(?:\.\d+)?)?", Path(parts[0]).name.lower()):
        return None
    script: str | None = None
    for index, token in enumerate(parts[1:], start=1):
        if token == "-c":
            if index + 1 < len(parts):
                script = parts[index + 1]
            break
        if token.startswith("-c") and len(token) > 2:
            script = token[2:]
            break
    if not script:
        return None
    return python_script_blocked_command_reason(script, depth)


def python_script_blocked_command_reason(script: str, depth: int) -> str | None:
    if depth >= 3:
        return None
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return None

    builtins_aliases = {"builtins", "__builtins__"}
    eval_exec_aliases = {"eval", "exec"}
    compile_aliases = {"compile"}
    compiled_literal_scripts: dict[str, str] = {}
    webbrowser_aliases = {"webbrowser"}
    webbrowser_open_aliases: set[str] = set()
    webbrowser_get_aliases: set[str] = set()
    io_aliases = {"io"}
    io_open_aliases: set[str] = set()
    importlib_aliases = {"importlib"}
    import_module_aliases: set[str] = set()
    os_aliases = {"os"}
    os_open_aliases: set[str] = set()
    os_startfile_aliases: set[str] = set()
    os_exec_spawn_aliases: set[str] = set()
    asyncio_aliases = {"asyncio"}
    asyncio_subprocess_aliases: set[str] = set()
    pathlib_aliases = {"pathlib"}
    pathlib_path_aliases: set[str] = set()
    pty_aliases = {"pty"}
    pty_spawn_aliases: set[str] = set()
    shutil_aliases = {"shutil"}
    shutil_rmtree_aliases: set[str] = set()
    subprocess_aliases = {"subprocess"}
    os_launcher_aliases: set[str] = set()
    subprocess_launcher_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                asname = alias.asname or name.split(".", 1)[0]
                if name == "builtins":
                    builtins_aliases.add(asname)
                elif name == "webbrowser":
                    webbrowser_aliases.add(asname)
                elif name == "io":
                    io_aliases.add(asname)
                elif name == "importlib":
                    importlib_aliases.add(asname)
                elif name == "os":
                    os_aliases.add(asname)
                elif name == "asyncio":
                    asyncio_aliases.add(asname)
                elif name == "pathlib":
                    pathlib_aliases.add(asname)
                elif name == "pty":
                    pty_aliases.add(asname)
                elif name == "shutil":
                    shutil_aliases.add(asname)
                elif name == "subprocess":
                    subprocess_aliases.add(asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "webbrowser":
                for alias in node.names:
                    if alias.name.startswith("open"):
                        webbrowser_open_aliases.add(alias.asname or alias.name)
                    elif alias.name == "get":
                        webbrowser_get_aliases.add(alias.asname or alias.name)
            elif node.module == "os":
                for alias in node.names:
                    if alias.name == "open":
                        os_open_aliases.add(alias.asname or alias.name)
                    elif alias.name in {"system", "popen"}:
                        os_launcher_aliases.add(alias.asname or alias.name)
                    elif alias.name == "startfile":
                        os_startfile_aliases.add(alias.asname or alias.name)
                    elif python_os_exec_spawn_function_name(alias.name):
                        os_exec_spawn_aliases.add(alias.asname or alias.name)
            elif node.module == "asyncio":
                for alias in node.names:
                    if alias.name in {"create_subprocess_exec", "create_subprocess_shell"}:
                        asyncio_subprocess_aliases.add(alias.asname or alias.name)
            elif node.module == "io":
                for alias in node.names:
                    if alias.name == "open":
                        io_open_aliases.add(alias.asname or alias.name)
            elif node.module == "importlib":
                for alias in node.names:
                    if alias.name == "import_module":
                        import_module_aliases.add(alias.asname or alias.name)
            elif node.module == "pathlib":
                for alias in node.names:
                    if alias.name == "Path":
                        pathlib_path_aliases.add(alias.asname or alias.name)
            elif node.module == "pty":
                for alias in node.names:
                    if alias.name == "spawn":
                        pty_spawn_aliases.add(alias.asname or alias.name)
            elif node.module == "shutil":
                for alias in node.names:
                    if alias.name == "rmtree":
                        shutil_rmtree_aliases.add(alias.asname or alias.name)
            elif node.module == "subprocess":
                for alias in node.names:
                    if alias.name in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
                        subprocess_launcher_aliases.add(alias.asname or alias.name)
            elif node.module == "builtins":
                for alias in node.names:
                    if alias.name in {"eval", "exec"}:
                        eval_exec_aliases.add(alias.asname or alias.name)
                    elif alias.name == "compile":
                        compile_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            if python_expr_is_eval_or_exec_reference(node.value, builtins_aliases, eval_exec_aliases):
                eval_exec_aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            elif python_expr_is_compile_reference(node.value, builtins_aliases, compile_aliases):
                compile_aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
            else:
                compiled_script = python_literal_compile_script(node.value, builtins_aliases, compile_aliases)
                if compiled_script is not None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            compiled_literal_scripts[target.id] = compiled_script

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        nested_python = python_literal_eval_exec_script(
            node,
            builtins_aliases,
            eval_exec_aliases,
            compile_aliases,
            compiled_literal_scripts,
        )
        if nested_python is not None:
            nested_python_blocked = python_script_blocked_command_reason(nested_python, depth + 1)
            if nested_python_blocked:
                return nested_python_blocked
        if python_call_writes_raw_device(
            node,
            io_aliases,
            io_open_aliases,
            os_aliases,
            os_open_aliases,
            pathlib_aliases,
            pathlib_path_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return RAW_DEVICE_WRITE_BLOCK_REASON
        if python_call_deletes_broad_path(
            node,
            shutil_aliases,
            shutil_rmtree_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return RECURSIVE_DELETE_BLOCK_REASON
        if python_call_is_webbrowser_open(
            node,
            webbrowser_aliases,
            webbrowser_open_aliases,
            webbrowser_get_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return "GUI application launch commands are not allowed in project mode"
        if python_call_is_os_startfile(
            node,
            os_aliases,
            os_startfile_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        ):
            return "GUI application launch commands are not allowed in project mode"
        nested_command = python_call_shell_command(
            node,
            os_aliases,
            subprocess_aliases,
            asyncio_aliases,
            pty_aliases,
            os_launcher_aliases,
            subprocess_launcher_aliases,
            os_exec_spawn_aliases,
            asyncio_subprocess_aliases,
            pty_spawn_aliases,
            builtins_aliases,
            importlib_aliases,
            import_module_aliases,
        )
        if nested_command:
            nested_blocked = get_blocked_command_reason(nested_command, _depth=depth + 1)
            if nested_blocked:
                return nested_blocked
    return None


def python_literal_eval_exec_script(
    node: ast.Call,
    builtins_aliases: set[str],
    eval_exec_aliases: set[str],
    compile_aliases: set[str],
    compiled_literal_scripts: dict[str, str],
) -> str | None:
    if not python_call_is_eval_or_exec(node.func, builtins_aliases, eval_exec_aliases):
        return None
    if not node.args:
        return None
    source = node.args[0]
    literal = python_literal_source_text(source)
    if literal is not None:
        return literal
    if isinstance(source, ast.Name):
        return compiled_literal_scripts.get(source.id)
    return python_literal_compile_script(source, builtins_aliases, compile_aliases)


def python_call_is_eval_or_exec(func: ast.expr, builtins_aliases: set[str], eval_exec_aliases: set[str]) -> bool:
    return python_expr_is_eval_or_exec_reference(func, builtins_aliases, eval_exec_aliases)


def python_expr_is_eval_or_exec_reference(node: ast.AST, builtins_aliases: set[str], eval_exec_aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in eval_exec_aliases
    if isinstance(node, ast.Attribute) and node.attr in {"eval", "exec"}:
        return isinstance(node.value, ast.Name) and node.value.id in builtins_aliases
    getattr_target = python_static_getattr_target(node)
    if getattr_target is None:
        return False
    target, attr = getattr_target
    return attr in {"eval", "exec"} and isinstance(target, ast.Name) and target.id in builtins_aliases


def python_literal_compile_script(source: ast.AST, builtins_aliases: set[str], compile_aliases: set[str]) -> str | None:
    if not isinstance(source, ast.Call) or not python_call_is_compile(source.func, builtins_aliases, compile_aliases):
        return None
    if len(source.args) < 3:
        return None
    code = source.args[0]
    mode = source.args[2]
    literal = python_literal_source_text(code)
    if literal is None:
        return None
    if not isinstance(mode, ast.Constant) or mode.value not in {"eval", "exec", "single"}:
        return None
    return literal


def python_literal_source_text(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        try:
            return node.value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


def python_call_is_compile(func: ast.expr, builtins_aliases: set[str], compile_aliases: set[str]) -> bool:
    return python_expr_is_compile_reference(func, builtins_aliases, compile_aliases)


def python_expr_is_compile_reference(node: ast.AST, builtins_aliases: set[str], compile_aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in compile_aliases
    if isinstance(node, ast.Attribute) and node.attr == "compile":
        return isinstance(node.value, ast.Name) and node.value.id in builtins_aliases
    getattr_target = python_static_getattr_target(node)
    if getattr_target is None:
        return False
    target, attr = getattr_target
    return attr == "compile" and isinstance(target, ast.Name) and target.id in builtins_aliases


def python_call_deletes_broad_path(
    node: ast.Call,
    shutil_aliases: set[str],
    shutil_rmtree_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        if func.id not in shutil_rmtree_aliases:
            return False
    elif isinstance(func, ast.Attribute) and func.attr == "rmtree":
        if isinstance(func.value, ast.Name):
            if func.value.id not in shutil_aliases:
                return False
        elif not (
            isinstance(func.value, ast.Call)
            and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "shutil"
        ):
            return False
    else:
        return False
    target = python_call_string_argument(node, "path")
    return target is not None and is_dangerous_recursive_delete_target(target)


def python_call_string_argument(node: ast.Call, keyword_name: str) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    for keyword in node.keywords:
        if keyword.arg == keyword_name and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def python_call_writes_raw_device(
    node: ast.Call,
    io_aliases: set[str],
    io_open_aliases: set[str],
    os_aliases: set[str],
    os_open_aliases: set[str],
    pathlib_aliases: set[str],
    pathlib_path_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    if python_open_call_writes_raw_device(node, io_aliases, io_open_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return True
    if python_os_open_call_writes_raw_device(node, os_aliases, os_open_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return True
    return python_pathlib_call_writes_raw_device(
        node,
        pathlib_aliases,
        pathlib_path_aliases,
        builtins_aliases,
        importlib_aliases,
        import_module_aliases,
    )


def python_open_call_writes_raw_device(
    node: ast.Call,
    io_aliases: set[str],
    io_open_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if not python_call_is_text_open(func, io_aliases, io_open_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return False
    if not node.args:
        return False
    path_arg = node.args[0]
    if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
        return False
    if not is_raw_device_write_target(path_arg.value):
        return False
    mode = "r"
    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
        mode = node.args[1].value
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            mode = keyword.value.value
            break
    return any(flag in mode for flag in ("w", "a", "+", "x"))


def python_call_is_text_open(
    func: ast.expr,
    io_aliases: set[str],
    io_open_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    if isinstance(func, ast.Name):
        return func.id == "open" or func.id in io_open_aliases
    if not isinstance(func, ast.Attribute) or func.attr != "open":
        return False
    if isinstance(func.value, ast.Name) and func.value.id in io_aliases:
        return True
    return isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "io"


def python_os_open_call_writes_raw_device(
    node: ast.Call,
    os_aliases: set[str],
    os_open_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        if func.id not in os_open_aliases:
            return False
    elif isinstance(func, ast.Attribute) and func.attr == "open":
        if isinstance(func.value, ast.Name):
            if func.value.id not in os_aliases:
                return False
        elif not (
            isinstance(func.value, ast.Call)
            and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "os"
        ):
            return False
    else:
        return False
    if len(node.args) < 2:
        return False
    path_arg = node.args[0]
    if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
        return False
    if not is_raw_device_write_target(path_arg.value):
        return False
    return python_os_open_flags_write(node.args[1])


def python_os_open_flags_write(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return (node.value & 0b11) in {1, 2}
    if isinstance(node, ast.Attribute) and node.attr in {"O_WRONLY", "O_RDWR"}:
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return python_os_open_flags_write(node.left) or python_os_open_flags_write(node.right)
    return False


def python_pathlib_call_writes_raw_device(
    node: ast.Call,
    pathlib_aliases: set[str],
    pathlib_path_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in {"open", "write_bytes", "write_text"}:
        return False
    path = python_pathlib_call_path(func.value, pathlib_aliases, pathlib_path_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
    if path is None or not is_raw_device_write_target(path):
        return False
    if func.attr in {"write_bytes", "write_text"}:
        return True
    mode = "r"
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        mode = node.args[0].value
    for keyword in node.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            mode = keyword.value.value
            break
    return any(flag in mode for flag in ("w", "a", "+", "x"))


def python_pathlib_call_path(
    node: ast.AST,
    pathlib_aliases: set[str],
    pathlib_path_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> str | None:
    if not isinstance(node, ast.Call) or not node.args:
        return None
    path_arg = node.args[0]
    if not isinstance(path_arg, ast.Constant) or not isinstance(path_arg.value, str):
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id in pathlib_path_aliases:
        return path_arg.value
    if isinstance(func, ast.Attribute) and func.attr == "Path":
        if isinstance(func.value, ast.Name) and func.value.id in pathlib_aliases:
            return path_arg.value
        if isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "pathlib":
            return path_arg.value
    return None


def python_call_is_webbrowser_open(
    node: ast.Call,
    module_aliases: set[str],
    function_aliases: set[str],
    get_function_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in function_aliases:
        return True
    if isinstance(func, ast.Call):
        attr = python_getattr_attribute(func, module_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        return attr is not None and attr.startswith("open")
    if not isinstance(func, ast.Attribute) or not func.attr.startswith("open"):
        return False
    if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
        return True
    if not isinstance(func.value, ast.Call):
        return False
    if python_call_is_webbrowser_get(func.value, module_aliases, get_function_aliases, builtins_aliases, importlib_aliases, import_module_aliases):
        return True
    return python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "webbrowser"


def python_call_is_webbrowser_get(
    node: ast.Call,
    module_aliases: set[str],
    function_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in function_aliases:
        return True
    if isinstance(func, ast.Call):
        return python_getattr_attribute(func, module_aliases, builtins_aliases, importlib_aliases, import_module_aliases) == "get"
    if isinstance(func, ast.Attribute) and func.attr == "get":
        if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
            return True
        if isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "webbrowser":
            return True
    return False


def python_call_is_os_startfile(
    node: ast.Call,
    module_aliases: set[str],
    function_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in function_aliases:
        return True
    if isinstance(func, ast.Call):
        return python_getattr_attribute(func, module_aliases, builtins_aliases, importlib_aliases, import_module_aliases) == "startfile"
    if not isinstance(func, ast.Attribute) or func.attr != "startfile":
        return False
    if isinstance(func.value, ast.Name) and func.value.id in module_aliases:
        return True
    if isinstance(func.value, ast.Call) and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "os":
        return True
    return False


def python_dynamic_import_name(
    node: ast.Call,
    builtins_aliases: set[str] | None = None,
    importlib_aliases: set[str] | None = None,
    import_module_aliases: set[str] | None = None,
) -> str | None:
    importer = node
    builtins_aliases = builtins_aliases or {"builtins", "__builtins__"}
    importlib_aliases = importlib_aliases or {"importlib"}
    import_module_aliases = import_module_aliases or set()
    module_name = python_first_string_argument(importer)
    if module_name is None:
        return None
    if (
        isinstance(importer.func, ast.Name)
        and importer.func.id == "__import__"
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "__import__"
        and isinstance(importer.func.value, ast.Name)
        and importer.func.value.id in builtins_aliases
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Name)
        and importer.func.id in import_module_aliases
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "import_module"
        and isinstance(importer.func.value, ast.Name)
        and importer.func.value.id in importlib_aliases
    ):
        return module_name
    if (
        isinstance(importer.func, ast.Attribute)
        and importer.func.attr == "import_module"
        and isinstance(importer.func.value, ast.Call)
        and python_dynamic_import_name(importer.func.value, builtins_aliases, importlib_aliases, import_module_aliases) == "importlib"
    ):
        return module_name
    getattr_target = python_static_getattr_target(importer.func)
    if getattr_target is None:
        return None
    target, attr = getattr_target
    if attr == "__import__" and isinstance(target, ast.Name) and target.id in builtins_aliases:
        return module_name
    if attr == "import_module" and isinstance(target, ast.Call):
        target_name = python_dynamic_import_name(target, builtins_aliases, importlib_aliases, import_module_aliases)
        if target_name == "importlib":
            return module_name
    return None


def python_first_string_argument(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def python_static_getattr_target(node: ast.AST) -> tuple[ast.AST, str] | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "getattr" or len(node.args) < 2:
        return None
    attr = node.args[1]
    if not isinstance(attr, ast.Constant) or not isinstance(attr.value, str):
        return None
    return node.args[0], attr.value


def python_call_shell_command(
    node: ast.Call,
    os_aliases: set[str],
    subprocess_aliases: set[str],
    asyncio_aliases: set[str],
    pty_aliases: set[str],
    os_launcher_aliases: set[str],
    subprocess_launcher_aliases: set[str],
    os_exec_spawn_aliases: set[str],
    asyncio_subprocess_aliases: set[str],
    pty_spawn_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> str | None:
    func = node.func
    if isinstance(func, ast.Call):
        os_attr = python_getattr_attribute(func, os_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if os_attr in {"system", "popen"}:
            return python_command_argument(node)
        if os_attr and python_os_exec_spawn_function_name(os_attr):
            return python_os_exec_spawn_command(node, os_attr)
        subprocess_attr = python_getattr_attribute(func, subprocess_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if subprocess_attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
            return python_command_argument(node)
        asyncio_attr = python_getattr_attribute(func, asyncio_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if asyncio_attr in {"create_subprocess_exec", "create_subprocess_shell"}:
            return python_asyncio_subprocess_command(node, asyncio_attr)
        pty_attr = python_getattr_attribute(func, pty_aliases, builtins_aliases, importlib_aliases, import_module_aliases)
        if pty_attr == "spawn":
            return python_command_argument(node)
        return None
    if isinstance(func, ast.Name):
        if func.id in os_launcher_aliases or func.id in subprocess_launcher_aliases:
            return python_command_argument(node)
        if func.id in os_exec_spawn_aliases:
            return python_os_exec_spawn_command(node, func.id)
        if func.id in asyncio_subprocess_aliases:
            return python_asyncio_subprocess_command(node, func.id)
        if func.id in pty_spawn_aliases:
            return python_command_argument(node)
        return None
    if not isinstance(func, ast.Attribute):
        return None
    if isinstance(func.value, ast.Name):
        if func.value.id in os_aliases and func.attr in {"system", "popen"}:
            return python_command_argument(node)
        if func.value.id in os_aliases and python_os_exec_spawn_function_name(func.attr):
            return python_os_exec_spawn_command(node, func.attr)
        if func.value.id in subprocess_aliases and func.attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}:
            return python_command_argument(node)
        if func.value.id in asyncio_aliases and func.attr in {"create_subprocess_exec", "create_subprocess_shell"}:
            return python_asyncio_subprocess_command(node, func.attr)
        if func.value.id in pty_aliases and func.attr == "spawn":
            return python_command_argument(node)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in os_aliases
        and func.attr in {"system", "popen"}
    ):
        return python_command_argument(node)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in os_aliases
        and python_os_exec_spawn_function_name(func.attr)
    ):
        return python_os_exec_spawn_command(node, func.attr)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in subprocess_aliases
        and func.attr in {"run", "call", "Popen", "check_call", "check_output", "getoutput", "getstatusoutput"}
    ):
        return python_command_argument(node)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in asyncio_aliases
        and func.attr in {"create_subprocess_exec", "create_subprocess_shell"}
    ):
        return python_asyncio_subprocess_command(node, func.attr)
    if (
        isinstance(func.value, ast.Call)
        and python_dynamic_import_name(func.value, builtins_aliases, importlib_aliases, import_module_aliases) in pty_aliases
        and func.attr == "spawn"
    ):
        return python_command_argument(node)
    return None


def python_getattr_attribute(
    node: ast.Call,
    module_aliases: set[str],
    builtins_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> str | None:
    getattr_target = python_static_getattr_target(node)
    if getattr_target is None:
        return None
    target, attr_value = getattr_target
    if isinstance(target, ast.Name):
        target_name = target.id
    elif isinstance(target, ast.Call):
        target_name = python_dynamic_import_name(target, builtins_aliases, importlib_aliases, import_module_aliases)
    else:
        return None
    if target_name not in module_aliases:
        return None
    return attr_value


def python_asyncio_subprocess_command(node: ast.Call, name: str) -> str | None:
    if name == "create_subprocess_shell":
        return python_command_argument(node)
    if name == "create_subprocess_exec":
        return python_executable_command_from_args(node.args, path_index=0, argv_index=None)
    return None


def python_os_exec_spawn_function_name(name: str) -> str | None:
    lowered = name.lower()
    if lowered in {
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "posix_spawn",
        "posix_spawnp",
    }:
        return lowered
    return None


def python_os_exec_spawn_command(node: ast.Call, name: str) -> str | None:
    function_name = python_os_exec_spawn_function_name(name)
    if function_name is None:
        return None
    path_index = 1 if function_name.startswith("spawn") and not function_name.startswith("posix_spawn") else 0
    argv_index: int | None = None
    if function_name.startswith(("execv", "spawnv")):
        argv_index = path_index + 1
    elif function_name.startswith("posix_spawn"):
        argv_index = 1
    return python_executable_command_from_args(node.args, path_index=path_index, argv_index=argv_index)


def python_executable_command_from_args(args: list[ast.expr], path_index: int, argv_index: int | None) -> str | None:
    if len(args) <= path_index:
        return None
    path = python_string_constant(args[path_index])
    if path is None:
        return None
    parts = [path]
    if argv_index is not None:
        if len(args) <= argv_index:
            return shlex.join(parts)
        argv = python_string_sequence(args[argv_index])
        if argv:
            parts.extend(argv)
        return shlex.join(parts)
    for arg in args[path_index + 1 :]:
        value = python_string_constant(arg)
        if value is None:
            break
        parts.append(value)
    return shlex.join(parts)


def python_string_constant(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def python_string_sequence(node: ast.expr) -> list[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[str] = []
    for item in node.elts:
        value = python_string_constant(item)
        if value is None:
            return None
        values.append(value)
    return values


def python_command_argument(node: ast.Call) -> str | None:
    command_arg = node.args[0] if node.args else None
    if command_arg is None:
        for keyword in node.keywords:
            if keyword.arg == "args":
                command_arg = keyword.value
                break
    if command_arg is None:
        return None
    if isinstance(command_arg, ast.Constant) and isinstance(command_arg.value, str):
        return command_arg.value
    if isinstance(command_arg, (ast.List, ast.Tuple)):
        parts: list[str] = []
        for item in command_arg.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            parts.append(item.value)
        return shlex.join(parts)
    return None



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
    "shell_pipeline_segments",
    "shell_wrapped_blocked_command_reason",
    "storage_invocation_changes_device_state",
    "strip_env_command_prefix",
    "sysctl_invocation_changes_kernel_state",
    "systemctl_invocation_changes_system_state",
    "unwrapped_shell_command_parts",
    "unwrapped_shell_executable_name",
]
