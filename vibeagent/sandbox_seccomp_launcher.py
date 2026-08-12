from __future__ import annotations

import os
import sys

from .sandbox_seccomp_filter import (
    SECCOMP_FD_TOKEN,
    create_unix_socket_filter_fd,
    install_unix_socket_filter,
)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    install_directly = bool(arguments and arguments[0] == "--install")
    if install_directly:
        arguments.pop(0)
    if not arguments or arguments[0] != "--" or len(arguments) == 1:
        print("sandbox seccomp launcher requires [--install] -- COMMAND", file=sys.stderr)
        return 2
    if install_directly:
        try:
            install_unix_socket_filter()
        except OSError as error:
            print(f"Could not install sandbox seccomp filter: {error}", file=sys.stderr)
            return 126
        return _exec(arguments[1:])
    try:
        descriptor = create_unix_socket_filter_fd()
    except OSError as error:
        print(f"Could not create sandbox seccomp filter: {error}", file=sys.stderr)
        return 126
    command = [
        str(descriptor) if value == SECCOMP_FD_TOKEN else value
        for value in arguments[1:]
    ]
    if SECCOMP_FD_TOKEN not in arguments[1:]:
        os.close(descriptor)
        print("sandbox seccomp command is missing its FD token", file=sys.stderr)
        return 2
    return _exec(command, descriptor=descriptor)


def _exec(command: list[str], *, descriptor: int | None = None) -> int:
    try:
        os.execvp(command[0], command)
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        print(f"Could not start sandbox command: {error}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
