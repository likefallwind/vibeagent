from __future__ import annotations

from .command_safety_args import command_operands
from .command_safety_filesystem import is_raw_device_write_target


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
