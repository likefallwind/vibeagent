from __future__ import annotations

from pathlib import Path

from .command_safety_network import (
    firewall_invocation_changes_network_state,
    ip_invocation_changes_network_state,
    iptables_invocation_changes_network_state,
    legacy_network_invocation_changes_state,
    nft_invocation_changes_network_state,
    sysctl_invocation_changes_kernel_state,
)
from .command_safety_orchestration import container_orchestration_invocation_changes_external_state
from .command_safety_process import process_termination_invocation_is_broad
from .command_safety_storage import storage_invocation_changes_device_state
from .command_safety_system import (
    service_invocation_changes_system_state,
    systemctl_invocation_changes_system_state,
)
from .command_safety_wrappers import shell_command_segments, unwrapped_shell_command_parts


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


__all__ = ["command_invokes_high_risk_executable"]
