from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys


MAX_ENVIRONMENT_FILE_BYTES = 2_000_000


def read_private_environment(path: Path) -> dict[str, str]:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or metadata.st_size > MAX_ENVIRONMENT_FILE_BYTES
    ):
        raise ValueError("tool memory environment file is not a private regular file")
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = handle.read(MAX_ENVIRONMENT_FILE_BYTES + 1)
    finally:
        path.unlink(missing_ok=True)
    if len(raw.encode("utf-8")) > MAX_ENVIRONMENT_FILE_BYTES:
        raise ValueError("tool memory environment file is too large")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or any(
        not isinstance(name, str)
        or not name
        or "=" in name
        or "\x00" in name
        or not isinstance(value, str)
        or "\x00" in value
        for name, value in payload.items()
    ):
        raise ValueError("tool memory environment file has invalid content")
    return payload


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) < 3 or values[1] != "--":
        print("invalid tool memory launcher arguments", file=sys.stderr)
        return 125
    environment_path = Path(values[0])
    command = values[2:]
    try:
        environment = read_private_environment(environment_path)
        os.execvpe(command[0], command, environment)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        environment_path.unlink(missing_ok=True)
        print(f"tool memory launcher failed: {error}", file=sys.stderr)
        return 125
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
