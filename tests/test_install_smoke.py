from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "install_smoke.py"
SPEC = importlib.util.spec_from_file_location("install_smoke", SCRIPT_PATH)
assert SPEC is not None
install_smoke = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = install_smoke
SPEC.loader.exec_module(install_smoke)


class InstallSmokeScriptTests(unittest.TestCase):
    def test_run_install_smoke_installs_and_checks_entrypoints_from_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-install-smoke-test-") as base:
            root = Path(base) / "repo"
            root.mkdir()
            (root / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
            (root / "README.md").write_text("# Test\n", encoding="utf-8")
            (root / "vibeagent").mkdir()
            (root / "vibeagent" / "__init__.py").write_text("", encoding="utf-8")
            calls: list[tuple[list[str], Path]] = []

            def fake_run(args, *, cwd, check, text, stdout, stderr, env):
                calls.append((list(args), Path(cwd)))
                self.assertNotIn("PYTHONHOME", env)
                self.assertNotIn("PYTHONPATH", env)
                self.assertEqual(env["PYTHONNOUSERSITE"], "1")
                self.assertEqual(env["PIP_DISABLE_PIP_VERSION_CHECK"], "1")
                if "wheel" in args:
                    wheel_dir = Path(args[args.index("--wheel-dir") + 1])
                    (wheel_dir / "vibeagent-1.0.0-py3-none-any.whl").write_bytes(b"wheel")
                if args[-2:-1] == ["-c"]:
                    module = Path(base) / "smoke" / "venv" / "lib" / "site-packages" / "vibeagent" / "__init__.py"
                    module.parent.mkdir(parents=True)
                    module.write_text("", encoding="utf-8")
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout=f"{module}\n", stderr="")
                if args[-1] == "--version":
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout="vibeagent 1.0.0\n", stderr="")
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

            with patch.object(install_smoke.tempfile, "mkdtemp", return_value=str(Path(base) / "smoke")):
                with patch.object(install_smoke.subprocess, "run", side_effect=fake_run):
                    result = install_smoke.run_install_smoke(root, keep=True)

        venv = result.venv
        outside = result.workdir
        python = install_smoke.venv_bin(venv, "python")
        executable = install_smoke.venv_bin(venv, "vibeagent")
        source = Path(base) / "smoke" / "source"
        wheel_dir = Path(base) / "smoke" / "wheelhouse"
        wheel = wheel_dir / "vibeagent-1.0.0-py3-none-any.whl"
        self.assertEqual(result.module_output, "vibeagent 1.0.0")
        self.assertEqual(result.script_output, "vibeagent 1.0.0")
        self.assertEqual(result.wheel, wheel)
        self.assertNotEqual(result.module_path, root / "vibeagent" / "__init__.py")
        self.assertEqual(
            calls,
            [
                ([sys.executable, "-m", "venv", "--system-site-packages", venv.as_posix()], root),
                (
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
                    outside,
                ),
                (
                    [
                        python.as_posix(),
                        "-m",
                        "pip",
                        "install",
                        "--no-deps",
                        "--force-reinstall",
                        wheel.as_posix(),
                    ],
                    outside,
                ),
                (
                    [
                        python.as_posix(),
                        "-c",
                        "import pathlib, vibeagent; print(pathlib.Path(vibeagent.__file__).resolve())",
                    ],
                    outside,
                ),
                ([python.as_posix(), "-m", "vibeagent", "--version"], outside),
                ([executable.as_posix(), "--version"], outside),
            ],
        )

    def test_select_built_wheel_requires_exactly_one_wheel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-wheel-select-") as base:
            root = Path(base)
            with self.assertRaisesRegex(RuntimeError, "produced 0 wheel files"):
                install_smoke.select_built_wheel(root)
            (root / "one.whl").write_bytes(b"one")
            self.assertEqual(install_smoke.select_built_wheel(root), root / "one.whl")
            (root / "two.whl").write_bytes(b"two")
            with self.assertRaisesRegex(RuntimeError, "produced 2 wheel files"):
                install_smoke.select_built_wheel(root)

    def test_validate_installed_module_path_rejects_source_or_outside_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-wheel-location-") as base:
            root = Path(base) / "repo"
            venv = Path(base) / "venv"
            source_module = root / "vibeagent" / "__init__.py"
            outside_module = Path(base) / "global" / "vibeagent" / "__init__.py"
            source_module.parent.mkdir(parents=True)
            outside_module.parent.mkdir(parents=True)
            source_module.write_text("", encoding="utf-8")
            outside_module.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "source checkout"):
                install_smoke.validate_installed_module_path(str(source_module), venv, root)
            with self.assertRaisesRegex(RuntimeError, "outside the smoke venv"):
                install_smoke.validate_installed_module_path(str(outside_module), venv, root)

    def test_run_install_smoke_cleans_private_tree_after_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-install-smoke-cleanup-") as base:
            root = Path(base) / "repo"
            temp_root = Path(base) / "smoke"
            root.mkdir()
            with (
                patch.object(install_smoke.tempfile, "mkdtemp", return_value=str(temp_root)),
                patch.object(
                    install_smoke,
                    "prepare_build_source",
                    side_effect=RuntimeError("build source failed"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "build source failed"):
                    install_smoke.run_install_smoke(root)

            self.assertFalse(temp_root.exists())

    def test_require_success_raises_with_command_error_detail(self) -> None:
        result = subprocess.CompletedProcess(args=["cmd"], returncode=1, stdout="", stderr="bad")

        with self.assertRaisesRegex(RuntimeError, "install failed: bad"):
            install_smoke.require_success(result, "install")


if __name__ == "__main__":
    unittest.main()
