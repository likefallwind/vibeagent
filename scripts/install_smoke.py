#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
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
    wheel: Path
    module_path: Path
    module_output: str
    script_output: str


def run_command(
    args: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )


def require_success(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{action} failed: {detail}")


def venv_bin(venv: Path, name: str) -> Path:
    return venv / ("Scripts" if sys.platform == "win32" else "bin") / name


def prepare_build_source(root: Path, destination: Path) -> Path:
    source = destination / "source"
    source.mkdir(parents=True)
    for name in ("pyproject.toml", "README.md"):
        path = root / name
        if not path.is_file():
            raise RuntimeError(f"package source is missing {name}")
        shutil.copy2(path, source / name)
    package = root / "vibeagent"
    if not package.is_dir():
        raise RuntimeError("package source is missing vibeagent/")
    shutil.copytree(
        package,
        source / "vibeagent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    return source


def select_built_wheel(directory: Path) -> Path:
    wheels = sorted(path for path in directory.glob("*.whl") if path.is_file())
    if len(wheels) != 1:
        raise RuntimeError(f"wheel build produced {len(wheels)} wheel files; expected exactly 1")
    return wheels[0]


def validate_installed_module_path(raw_path: str, venv: Path, root: Path) -> Path:
    value = raw_path.strip()
    if not value:
        raise RuntimeError("installed package did not report its module path")
    module_path = Path(value).resolve()
    try:
        module_path.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError(f"installed package still resolves to the source checkout: {module_path}")
    try:
        module_path.relative_to(venv.resolve())
    except ValueError as error:
        raise RuntimeError(f"installed package resolved outside the smoke venv: {module_path}") from error
    if not module_path.is_file():
        raise RuntimeError(f"installed package module is missing: {module_path}")
    return module_path


def clean_python_environment(venv: Path | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment.pop("VIRTUAL_ENV", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    if venv is not None:
        environment["VIRTUAL_ENV"] = str(venv)
    return environment


def run_install_smoke(root: Path = ROOT, *, keep: bool = False) -> InstallSmokeResult:
    temp_root = Path(tempfile.mkdtemp(prefix="vibeagent-install-smoke-"))
    venv = temp_root / "venv"
    workdir = temp_root / "outside"
    wheel_dir = temp_root / "wheelhouse"
    workdir.mkdir(parents=True)
    wheel_dir.mkdir()
    try:
        source = prepare_build_source(root.resolve(), temp_root)
        require_success(
            run_command(
                [sys.executable, "-m", "venv", "--system-site-packages", venv.as_posix()],
                cwd=root,
                environment=clean_python_environment(),
            ),
            "create venv",
        )
        python = venv_bin(venv, "python")
        executable = venv_bin(venv, "vibeagent")
        environment = clean_python_environment(venv)
        require_success(
            run_command(
                [
                    python.as_posix(),
                    "-m",
                    "pip",
                    "wheel",
                    "--no-build-isolation",
                    "--no-deps",
                    "--wheel-dir",
                    wheel_dir.as_posix(),
                    source.as_posix(),
                ],
                cwd=workdir,
                environment=environment,
            ),
            "build package wheel",
        )
        wheel = select_built_wheel(wheel_dir)
        require_success(
            run_command(
                [
                    python.as_posix(),
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--force-reinstall",
                    wheel.as_posix(),
                ],
                cwd=workdir,
                environment=environment,
            ),
            "install package wheel",
        )
        location = run_command(
            [
                python.as_posix(),
                "-c",
                "import pathlib, vibeagent; print(pathlib.Path(vibeagent.__file__).resolve())",
            ],
            cwd=workdir,
            environment=environment,
        )
        require_success(location, "resolve installed package location outside repo")
        module_path = validate_installed_module_path(location.stdout, venv, root)
        module = run_command(
            [python.as_posix(), "-m", "vibeagent", "--version"],
            cwd=workdir,
            environment=environment,
        )
        require_success(module, "run python -m vibeagent --version outside repo")
        script = run_command(
            [executable.as_posix(), "--version"],
            cwd=workdir,
            environment=environment,
        )
        require_success(script, "run vibeagent --version outside repo")
        return InstallSmokeResult(
            venv=venv,
            workdir=workdir,
            wheel=wheel,
            module_path=module_path,
            module_output=module.stdout.strip(),
            script_output=script.stdout.strip(),
        )
    finally:
        if not keep:
            shutil.rmtree(temp_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and install a VibeAgent wheel in a temporary venv, then smoke-test CLI entrypoints."
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
    print(f"wheel: {result.wheel.name}")
    print(f"module: {result.module_path}")
    if args.keep:
        print(f"venv: {result.venv}")
        print(f"workdir: {result.workdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
