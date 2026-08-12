from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .sandbox_network_proxy import SandboxNetworkProxy
from .sandbox_network_policy import normalize_sandbox_domains


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--policy-json", required=True)
    parser.add_argument("--proxy-source-token", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        parser.error("a sandbox command is required")
    try:
        policy = json.loads(args.policy_json)
        if not isinstance(policy, dict):
            raise ValueError("network policy must be an object")
        raw_allowed = policy.get("allowedDomains")
        raw_denied = policy.get("deniedDomains")
        if not isinstance(raw_allowed, list) or not all(
            isinstance(value, str) for value in raw_allowed
        ):
            raise ValueError("allowedDomains must be a string list")
        if not isinstance(raw_denied, list) or not all(
            isinstance(value, str) for value in raw_denied
        ):
            raise ValueError("deniedDomains must be a string list")
        allowed = normalize_sandbox_domains(raw_allowed, field="allowedDomains")
        denied = normalize_sandbox_domains(raw_denied, field="deniedDomains")
    except (json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    proxy_dir = Path(tempfile.mkdtemp(prefix="vibeagent-sandbox-network-"))
    os.chmod(proxy_dir, 0o700)
    socket_path = proxy_dir / "proxy.sock"
    resolved_command = [
        proxy_dir.as_posix() if value == args.proxy_source_token else value
        for value in command
    ]
    try:
        with SandboxNetworkProxy(
            socket_path.as_posix(),
            allowed_domains=allowed,
            denied_domains=denied,
        ):
            return subprocess.run(resolved_command, check=False).returncode
    finally:
        shutil.rmtree(proxy_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
