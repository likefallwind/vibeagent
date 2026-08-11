from __future__ import annotations

import json
from pathlib import Path
import sys

from .background_agent_store import write_private_text_atomic


def run_worker(payload_path: Path) -> int:
    payload = _consume_payload(payload_path)
    argv = payload.get("argv")
    exit_code_path = payload.get("exitCodePath")
    if (
        not isinstance(argv, list)
        or any(not isinstance(item, str) for item in argv)
        or not isinstance(exit_code_path, str)
    ):
        raise ValueError("Invalid background agent launch payload.")
    from .cli import main as cli_main

    exit_code = 1
    try:
        exit_code = cli_main(argv)
    finally:
        write_private_text_atomic(Path(exit_code_path), f"{exit_code}\n")
    return exit_code


def _consume_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ValueError("Invalid background agent launch payload.")
    return payload


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) != 1:
        print("Usage: python -m vibeagent.background_agent_worker <payload>", file=sys.stderr)
        return 2
    try:
        return run_worker(Path(values[0]))
    except Exception as error:
        print(f"Background agent worker failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
