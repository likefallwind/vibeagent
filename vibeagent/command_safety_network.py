from __future__ import annotations

from .command_safety_args import command_operands, first_command_operand


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
