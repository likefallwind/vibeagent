#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibeagent.session_commands import get_session_handoff_report
from vibeagent.session_handoff_details import extract_session_handoff_details


DEFAULT_ROOT = Path("/tmp/vibeagent-live-dogfood")
DOGFOOD_TASK = "inspect this repo, fix the failing test, verify, review, and commit"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def require_success(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(f"{action} failed: {result.stderr.strip() or result.stdout.strip()}")


def prepare_repo(root: Path, *, force: bool = False) -> None:
    if root.exists() and any(root.iterdir()):
        if not force:
            raise RuntimeError(f"{root} already exists and is not empty; pass --force to recreate it.")
        for child in sorted(root.iterdir(), reverse=True):
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    root.mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "calc.py").write_text("def add(left, right):\n    return left - right\n", encoding="utf-8")
    (root / "tests" / "test_calc.py").write_text(
        "import unittest\n\n"
        "from calc import add\n\n\n"
        "class CalcTests(unittest.TestCase):\n"
        "    def test_adds_two_numbers(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n",
        encoding="utf-8",
    )
    require_success(run_command(["git", "init"], cwd=root), "git init")
    require_success(run_command(["git", "config", "user.email", "vibeagent@example.invalid"], cwd=root), "git config user.email")
    require_success(run_command(["git", "config", "user.name", "VibeAgent Dogfood"], cwd=root), "git config user.name")
    require_success(run_command(["git", "add", "-A"], cwd=root), "git add")
    require_success(run_command(["git", "commit", "-m", "initial broken calculator"], cwd=root), "git commit")


def dogfood_command(root: Path) -> list[str]:
    return [
        "python3",
        "-m",
        "vibeagent",
        "--cwd",
        str(root),
        "--approval",
        "ask",
        "--max-iterations",
        "20",
        DOGFOOD_TASK,
    ]


def audit_repo(root: Path, *, run_id: str | None) -> list[CheckResult]:
    results: list[CheckResult] = []
    status = run_command(["git", "status", "--short"], cwd=root)
    results.append(CheckResult("git status clean", status.returncode == 0 and status.stdout == "", status.stdout.strip() or status.stderr.strip() or "clean"))

    commit_count = run_command(["git", "rev-list", "--count", "HEAD"], cwd=root)
    results.append(CheckResult("one intentional commit after initial", commit_count.returncode == 0 and commit_count.stdout.strip() == "2", commit_count.stdout.strip()))

    calc_text = (root / "calc.py").read_text(encoding="utf-8") if (root / "calc.py").exists() else ""
    results.append(CheckResult("calculator implementation fixed", "return left + right" in calc_text, "calc.py contains expected sum" if "return left + right" in calc_text else "calc.py missing expected sum"))

    tests = run_command(["python3", "-B", "-m", "unittest", "discover", "-s", "tests"], cwd=root)
    results.append(CheckResult("tests pass", tests.returncode == 0, (tests.stderr or tests.stdout).strip()))

    if run_id:
        report = get_session_handoff_report(root, run_id, max_files=50, max_commands=10, max_checks=50, max_text=500)
        handoff = extract_session_handoff_details(report)
        results.append(CheckResult("session handoff ready", handoff.ready, f"status={handoff.status} blockers={handoff.blockers}"))
    return results


def print_command(root: Path) -> None:
    print(" ".join(dogfood_command(root)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare and audit the VibeAgent 1.0 live-provider dogfood repo.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Throwaway dogfood repository path.")
    parser.add_argument("--force", action="store_true", help="Recreate --root if it already contains files.")
    parser.add_argument("--prepare", action="store_true", help="Create the throwaway broken calculator repository.")
    parser.add_argument("--print-command", action="store_true", help="Print the live-provider VibeAgent command.")
    parser.add_argument("--audit", action="store_true", help="Audit a completed dogfood run.")
    parser.add_argument("--run-id", help="Completed VibeAgent run id for session handoff audit.")
    args = parser.parse_args(argv)

    if not (args.prepare or args.print_command or args.audit):
        parser.error("choose at least one of --prepare, --print-command, or --audit")

    try:
        if args.prepare:
            prepare_repo(args.root, force=args.force)
        if args.print_command:
            print_command(args.root)
        if args.audit:
            checks = audit_repo(args.root, run_id=args.run_id)
            for check in checks:
                marker = "ok" if check.ok else "fail"
                print(f"{marker}: {check.name}: {check.detail}")
            if not all(check.ok for check in checks):
                return 1
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
