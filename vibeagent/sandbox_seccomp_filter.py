from __future__ import annotations

import errno
import ctypes
import os
import platform
import struct


SECCOMP_FD_TOKEN = "__VIBEAGENT_SECCOMP_FD__"
_AUDIT_ARCH_X86_64 = 0xC000003E
_AUDIT_ARCH_AARCH64 = 0xC00000B7
_SECCOMP_RET_KILL_PROCESS = 0x80000000
_SECCOMP_RET_ERRNO = 0x00050000
_SECCOMP_RET_ALLOW = 0x7FFF0000
_BPF_LOAD_WORD_ABSOLUTE = 0x20
_BPF_JUMP_EQUAL = 0x15
_BPF_RETURN = 0x06
_AF_UNIX = 1
_PR_SET_NO_NEW_PRIVS = 38
_PR_SET_SECCOMP = 22
_SECCOMP_MODE_FILTER = 2


class _SocketFilter(ctypes.Structure):
    _fields_ = (
        ("code", ctypes.c_ushort),
        ("jump_true", ctypes.c_ubyte),
        ("jump_false", ctypes.c_ubyte),
        ("value", ctypes.c_uint),
    )


class _SocketFilterProgram(ctypes.Structure):
    _fields_ = (
        ("length", ctypes.c_ushort),
        ("filter", ctypes.POINTER(_SocketFilter)),
    )


def unix_socket_filter_available() -> bool:
    return os.name == "posix" and hasattr(os, "memfd_create") and _architecture() is not None


def create_unix_socket_filter_fd() -> int:
    filter_bytes = _unix_socket_filter_bytes()
    descriptor = os.memfd_create("vibeagent-seccomp", flags=0)
    try:
        os.write(descriptor, filter_bytes)
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.set_inheritable(descriptor, True)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def install_unix_socket_filter() -> None:
    filter_bytes = _unix_socket_filter_bytes()
    instruction_size = ctypes.sizeof(_SocketFilter)
    instruction_count = len(filter_bytes) // instruction_size
    filters_type = _SocketFilter * instruction_count
    filters = filters_type.from_buffer_copy(filter_bytes)
    program = _SocketFilterProgram(instruction_count, filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    if libc.prctl(_PR_SET_SECCOMP, _SECCOMP_MODE_FILTER, ctypes.byref(program)) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _unix_socket_filter_bytes() -> bytes:
    architecture = _architecture()
    if os.name != "posix" or not hasattr(os, "memfd_create") or architecture is None:
        raise OSError("Unix socket seccomp filtering is unavailable on this platform.")
    audit_arch, socket_syscalls = architecture
    instructions = [
        _instruction(_BPF_LOAD_WORD_ABSOLUTE, value=4),
        _instruction(_BPF_JUMP_EQUAL, jump_true=1, value=audit_arch),
        _instruction(_BPF_RETURN, value=_SECCOMP_RET_KILL_PROCESS),
        _instruction(_BPF_LOAD_WORD_ABSOLUTE, value=0),
    ]
    for index, syscall in enumerate(socket_syscalls):
        remaining = len(socket_syscalls) - index
        instructions.append(
            _instruction(
                _BPF_JUMP_EQUAL,
                jump_true=remaining,
                value=syscall,
            )
        )
    instructions.extend(
        (
            _instruction(_BPF_RETURN, value=_SECCOMP_RET_ALLOW),
            _instruction(_BPF_LOAD_WORD_ABSOLUTE, value=16),
            _instruction(_BPF_JUMP_EQUAL, jump_false=1, value=_AF_UNIX),
            _instruction(
                _BPF_RETURN,
                value=_SECCOMP_RET_ERRNO | errno.EPERM,
            ),
            _instruction(_BPF_RETURN, value=_SECCOMP_RET_ALLOW),
        )
    )
    return b"".join(instructions)


def _architecture() -> tuple[int, tuple[int, ...]] | None:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return _AUDIT_ARCH_X86_64, (41, 0x40000029)
    if machine in {"aarch64", "arm64"}:
        return _AUDIT_ARCH_AARCH64, (198,)
    return None


def _instruction(
    code: int,
    *,
    jump_true: int = 0,
    jump_false: int = 0,
    value: int = 0,
) -> bytes:
    return struct.pack("=HBBI", code, jump_true, jump_false, value)


__all__ = [
    "SECCOMP_FD_TOKEN",
    "create_unix_socket_filter_fd",
    "install_unix_socket_filter",
    "unix_socket_filter_available",
]
