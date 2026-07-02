from __future__ import annotations

from .command_safety_args import command_operands, first_command_operand


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
