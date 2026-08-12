from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
from threading import Thread

from .credential_output_redactor import StreamingCredentialRedactor


MAX_MASKED_CREDENTIAL_FILE_BYTES = 128_000
MAX_MASKED_CREDENTIAL_TOTAL_BYTES = 1_000_000
MAX_MASKED_CREDENTIAL_ENTRIES = 200


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config-json", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        parser.error("a command is required")
    try:
        environment_names, file_paths = _parse_config(args.config_json)
        secrets = _load_secrets(environment_names, file_paths)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"Credential masking failed: {error}", file=sys.stderr)
        return 126
    try:
        process = subprocess.Popen(
            command,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        print(f"Could not start masked command: {error}", file=sys.stderr)
        return 126
    readers = (
        Thread(
            target=_copy_redacted,
            args=(process.stdout, sys.stdout.buffer, secrets),
            daemon=True,
        ),
        Thread(
            target=_copy_redacted,
            args=(process.stderr, sys.stderr.buffer, secrets),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()
    return_code = process.wait()
    for reader in readers:
        reader.join()
    if return_code < 0:
        signal_number = -return_code
        signal.signal(signal_number, signal.SIG_DFL)
        os.kill(os.getpid(), signal_number)
    return return_code


def _parse_config(value: str) -> tuple[tuple[str, ...], tuple[Path, ...]]:
    payload = json.loads(value)
    if not isinstance(payload, dict) or set(payload) != {"env", "files"}:
        raise ValueError("mask configuration must contain env and files lists")
    environment = payload["env"]
    files = payload["files"]
    if not isinstance(environment, list) or not all(
        isinstance(item, str) for item in environment
    ):
        raise ValueError("mask env must be a string list")
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise ValueError("mask files must be a string list")
    if len(environment) + len(files) > MAX_MASKED_CREDENTIAL_ENTRIES:
        raise ValueError(
            f"mask configuration exceeds {MAX_MASKED_CREDENTIAL_ENTRIES} entries"
        )
    return tuple(dict.fromkeys(environment)), tuple(
        Path(item) for item in dict.fromkeys(files)
    )


def _load_secrets(
    environment_names: tuple[str, ...],
    file_paths: tuple[Path, ...],
) -> tuple[bytes, ...]:
    values: list[bytes] = []
    total = 0
    for name in environment_names:
        value = os.environ.get(name)
        if value:
            encoded = value.encode("utf-8")
            if len(encoded) > MAX_MASKED_CREDENTIAL_FILE_BYTES:
                raise ValueError(
                    "masked credential environment value exceeds "
                    f"{MAX_MASKED_CREDENTIAL_FILE_BYTES} bytes: {name}"
                )
            total += len(encoded)
            if total > MAX_MASKED_CREDENTIAL_TOTAL_BYTES:
                raise ValueError(
                    "masked credentials exceed "
                    f"{MAX_MASKED_CREDENTIAL_TOTAL_BYTES} total bytes"
                )
            values.append(encoded)
    for path in file_paths:
        value, size = _read_secret_file(path)
        if size > MAX_MASKED_CREDENTIAL_FILE_BYTES:
            raise ValueError(
                f"masked credential file exceeds {MAX_MASKED_CREDENTIAL_FILE_BYTES} bytes: {path}"
            )
        total += size
        if total > MAX_MASKED_CREDENTIAL_TOTAL_BYTES:
            raise ValueError(
                "masked credentials exceed "
                f"{MAX_MASKED_CREDENTIAL_TOTAL_BYTES} total bytes"
            )
        if value:
            values.append(value)
            stripped = value.strip()
            if stripped and stripped != value:
                values.append(stripped)
    return tuple(values)


def _read_secret_file(path: Path) -> tuple[bytes, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(
            f"masked credential path is not a readable regular file: {path}"
        ) from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"masked credential path is not a regular file: {path}")
        if metadata.st_size > MAX_MASKED_CREDENTIAL_FILE_BYTES:
            return b"", metadata.st_size
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            value = handle.read(MAX_MASKED_CREDENTIAL_FILE_BYTES + 1)
            return value, max(metadata.st_size, len(value))
    finally:
        os.close(descriptor)


def _copy_redacted(source: object, destination: object, secrets: tuple[bytes, ...]) -> None:
    if source is None or not hasattr(source, "read") or not hasattr(destination, "write"):
        return
    redactor = StreamingCredentialRedactor(secrets)
    while True:
        chunk = (
            source.read1(8_192)
            if hasattr(source, "read1")
            else source.read(8_192)
        )
        if not chunk:
            break
        output = redactor.feed(chunk)
        if output:
            destination.write(output)
            destination.flush()
    output = redactor.feed(b"", final=True)
    if output:
        destination.write(output)
        destination.flush()


if __name__ == "__main__":
    raise SystemExit(main())
