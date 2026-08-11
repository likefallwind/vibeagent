from __future__ import annotations

import argparse
from pathlib import Path

from .cli_config import resolve_project_root
from .remote_control_server import create_remote_control_server


def run_remote_control_from_cli(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.cwd) or Path.cwd()
    server = create_remote_control_server(
        project_root,
        host=args.remote_control_host,
        port=args.remote_control_port,
        cert_path=Path(args.remote_control_cert) if args.remote_control_cert else None,
        key_path=Path(args.remote_control_key) if args.remote_control_key else None,
    )
    print("VibeAgent Remote Control")
    print(f"  project: {project_root.resolve()}")
    print(f"  open: {server.url}")
    print("  access: bearer token is stored in the URL fragment and is not sent in request logs")
    print("  stop: Ctrl+C")
    try:
        server.serve_forever()
    finally:
        server.close()
    return 0


__all__ = ["run_remote_control_from_cli"]
