#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class InstallSmokeResult:
    venv: Path
    workdir: Path
    module_output: str
    script_output: str


def run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def require_success(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{action} failed: {detail}")


def venv_bin(venv: Path, name: str) -> Path:
    return venv / ("Scripts" if sys.platform == "win32" else "bin") / name


def run_install_smoke(root: Path = ROOT, *, keep: bool = False) -> InstallSmokeResult:
    temp_root = Path(tempfile.mkdtemp(prefix="vibeagent-install-smoke-"))
    venv = temp_root / "venv"
    workdir = temp_root / "outside"
    workdir.mkdir(parents=True)
    try:
        require_success(
            run_command([sys.executable, "-m", "venv", "--system-site-packages", venv.as_posix()], cwd=root),
            "create venv",
        )
        python = venv_bin(venv, "python")
        executable = venv_bin(venv, "vibeagent")
        require_success(
            run_command(
                [python.as_posix(), "-m", "pip", "install", "--no-build-isolation", "-e", root.as_posix()],
                cwd=workdir,
            ),
            "install editable package",
        )
        module = run_command([python.as_posix(), "-m", "vibeagent", "--version"], cwd=workdir)
        require_success(module, "run python -m vibeagent --version outside repo")
        script = run_command([executable.as_posix(), "--version"], cwd=workdir)
        require_success(script, "run vibeagent --version outside repo")
        return InstallSmokeResult(
            venv=venv,
            workdir=workdir,
            module_output=module.stdout.strip(),
            script_output=script.stdout.strip(),
        )
    finally:
        if not keep:
            shutil.rmtree(temp_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install VibeAgent into a temporary venv and smoke-test CLI entrypoints."
    )
    parser.add_argument("--keep", action="store_true", help="Keep the temporary venv for inspection.")
    args = parser.parse_args(argv)
    try:
        result = run_install_smoke(keep=args.keep)
    except RuntimeError as error:
        print(f"install smoke failed: {error}", file=sys.stderr)
        return 1
    print(f"python -m vibeagent: {result.module_output}")
    print(f"vibeagent: {result.script_output}")
    if args.keep:
        print(f"venv: {result.venv}")
        print(f"workdir: {result.workdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
