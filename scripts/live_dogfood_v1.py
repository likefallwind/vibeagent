#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibeagent.session import summarize_session
from vibeagent.session_commands import get_session_handoff_report
from vibeagent.session_handoff_details import extract_session_handoff_details


DEFAULT_ROOT = Path("/tmp/vibeagent-live-dogfood")
DOGFOOD_TASK = "inspect this repo, fix the failing test, verify, review, and commit"
READ_TOOL_NAMES = {
    "project_overview",
    "repo_map",
    "read_file",
    "read_file_context",
    "search",
    "git_status",
    "git_diff",
    "LS",
    "Glob",
    "Grep",
    "Read",
}
SIDE_EFFECT_TOOL_NAMES = {
    "write_file",
    "edit_file",
    "multi_edit_file",
    "run_command",
    "run_commands",
    "run_suggested_checks",
    "run_session_verification",
    "git_stage",
    "git_commit",
    "Write",
    "Edit",
    "MultiEdit",
    "Bash",
}


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


def load_session_events(root: Path, run_id: str) -> list[dict[str, object]]:
    events_path = root / ".vibeagent" / "sessions" / run_id / "events.jsonl"
    if not events_path.exists():
        raise RuntimeError(f"session events not found: {events_path}")
    events: list[dict[str, object]] = []
    for line_number, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"session events contain malformed JSON at line {line_number}: {error}") from error
        if isinstance(row, dict):
            events.append(row)
    return events


def _tool_result_kind(event: dict[str, object]) -> str:
    result = event.get("result")
    if isinstance(result, dict):
        return str(result.get("kind") or "")
    return ""


def _tool_event_name(event: dict[str, object]) -> str:
    return str(event.get("name") or _tool_result_kind(event))


def _event_command(event: dict[str, object]) -> str:
    result = event.get("result")
    if not isinstance(result, dict):
        return ""
    command = result.get("command")
    if isinstance(command, str):
        return command
    nested = result.get("result")
    if isinstance(nested, dict) and isinstance(nested.get("command"), str):
        return str(nested.get("command"))
    return ""


def _event_succeeded(event: dict[str, object]) -> bool | None:
    result = event.get("result")
    if not isinstance(result, dict):
        return None
    if isinstance(result.get("ok"), bool):
        return bool(result.get("ok"))
    nested = result.get("result")
    if isinstance(nested, dict):
        exit_code = nested.get("exit_code")
        timed_out = nested.get("timed_out")
        if isinstance(exit_code, int):
            return exit_code == 0 and timed_out is not True
    return None


def audit_session_events(root: Path, *, run_id: str) -> list[CheckResult]:
    events = load_session_events(root, run_id)
    results: list[CheckResult] = []
    task_events = [event for event in events if event.get("type") == "task"]
    task_event = task_events[0] if task_events else {}
    results.append(
        CheckResult(
            "live run used ask approval policy",
            task_event.get("approval_policy") == "ask",
            f"approval_policy={task_event.get('approval_policy') or 'missing'}",
        )
    )

    tool_events = [event for event in events if event.get("type") in {"tool_call", "tool_result"}]
    first_read_index = next((index for index, event in enumerate(tool_events) if _tool_event_name(event) in READ_TOOL_NAMES), None)
    first_side_effect_index = next((index for index, event in enumerate(tool_events) if _tool_event_name(event) in SIDE_EFFECT_TOOL_NAMES), None)
    results.append(
        CheckResult(
            "repository inspected before side effects",
            first_read_index is not None and first_side_effect_index is not None and first_read_index < first_side_effect_index,
            f"first_read={first_read_index} first_side_effect={first_side_effect_index}",
        )
    )

    approval_requests = [event for event in events if event.get("type") == "approval_requested"]
    approval_decisions = [event for event in events if event.get("type") == "approval_decision"]
    denied = [
        event
        for event in approval_decisions
        if isinstance(event.get("decision"), dict) and event["decision"].get("approved") is False
    ]
    results.append(CheckResult("side effects requested approval", bool(approval_requests), f"requests={len(approval_requests)}"))
    results.append(
        CheckResult(
            "approval decisions allowed requested actions",
            bool(approval_requests)
            and len(approval_decisions) >= len(approval_requests)
            and not denied,
            f"requests={len(approval_requests)} denied={len(denied)} approved={len(approval_decisions) - len(denied)}",
        )
    )

    command_events = [event for event in events if event.get("type") == "tool_result" and _tool_result_kind(event) in {"run_command", "run_commands"}]
    unittest_events = [event for event in command_events if "unittest" in _event_command(event)]
    failed_unittest = [event for event in unittest_events if _event_succeeded(event) is False]
    passed_unittest = [event for event in unittest_events if _event_succeeded(event) is True]
    results.append(
        CheckResult(
            "agent ran failing and passing unittest verification",
            bool(failed_unittest) and bool(passed_unittest),
            f"failed={len(failed_unittest)} passed={len(passed_unittest)}",
        )
    )

    summary = summarize_session(root, run_id)
    results.append(CheckResult("final review ready", summary.final_review_ready is True, f"final_review_ready={summary.final_review_ready}"))
    results.append(CheckResult("session completion ready", summary.completion_ready is True, f"completion_ready={summary.completion_ready} status={'completed' if summary.completed else 'blocked' if summary.blocked else 'failed' if summary.failed else 'unknown'}"))
    return results


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
        results.extend(audit_session_events(root, run_id=run_id))
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
