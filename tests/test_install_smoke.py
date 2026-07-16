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
            calls: list[tuple[list[str], Path]] = []

            def fake_run(args, *, cwd, check, text, stdout, stderr):
                calls.append((list(args), Path(cwd)))
                if args[-1] == "--version":
                    return subprocess.CompletedProcess(args=args, returncode=0, stdout="vibeagent 0.1.0\n", stderr="")
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

            with patch.object(install_smoke.tempfile, "mkdtemp", return_value=str(Path(base) / "smoke")):
                with patch.object(install_smoke.subprocess, "run", side_effect=fake_run):
                    result = install_smoke.run_install_smoke(root, keep=True)

        venv = result.venv
        outside = result.workdir
        python = install_smoke.venv_bin(venv, "python")
        executable = install_smoke.venv_bin(venv, "vibeagent")
        self.assertEqual(result.module_output, "vibeagent 0.1.0")
        self.assertEqual(result.script_output, "vibeagent 0.1.0")
        self.assertEqual(
            calls,
            [
                ([sys.executable, "-m", "venv", "--system-site-packages", venv.as_posix()], root),
                (
                    [python.as_posix(), "-m", "pip", "install", "--no-build-isolation", "-e", root.as_posix()],
                    outside,
                ),
                ([python.as_posix(), "-m", "vibeagent", "--version"], outside),
                ([executable.as_posix(), "--version"], outside),
            ],
        )

    def test_require_success_raises_with_command_error_detail(self) -> None:
        result = subprocess.CompletedProcess(args=["cmd"], returncode=1, stdout="", stderr="bad")

        with self.assertRaisesRegex(RuntimeError, "install failed: bad"):
            install_smoke.require_success(result, "install")


if __name__ == "__main__":
    unittest.main()
