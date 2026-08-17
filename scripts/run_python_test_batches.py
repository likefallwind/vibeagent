#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_SIZE = 25
DEFAULT_MEMORY_LIMIT_MB = 2_048
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_POLL_INTERVAL_SECONDS = 0.02


@dataclass(frozen=True)
class ProcessSample:
    parent_pid: int
    start_ticks: int
    rss_bytes: int


@dataclass(frozen=True)
class BatchResult:
    modules: tuple[str, ...]
    returncode: int
    peak_rss_bytes: int
    duration_seconds: float
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.reason is None


def discover_test_modules(
    root: Path = ROOT,
    *,
    tests_dir: str = "tests",
    pattern: str = "test_*.py",
) -> list[str]:
    directory = root / tests_dir
    modules = []
    for path in sorted(directory.rglob(pattern)):
        if not path.is_file() or path.name == "__init__.py":
            continue
        relative = path.relative_to(root).with_suffix("")
        if all(part.isidentifier() for part in relative.parts):
            modules.append(".".join(relative.parts))
    return modules


def partition_modules(modules: Iterable[str], batch_size: int) -> list[tuple[str, ...]]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    values = tuple(modules)
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def read_process_snapshot(proc_root: Path = Path("/proc")) -> dict[int, ProcessSample] | None:
    if not proc_root.is_dir():
        return None
    page_size = os.sysconf("SC_PAGE_SIZE")
    snapshot: dict[int, ProcessSample] = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            fields = stat[stat.rfind(")") + 2 :].split()
            snapshot[int(entry.name)] = ProcessSample(
                parent_pid=int(fields[1]),
                start_ticks=int(fields[19]),
                rss_bytes=max(0, int(fields[21])) * page_size,
            )
        except (FileNotFoundError, PermissionError, OSError, ValueError, IndexError):
            continue
    return snapshot


def update_tracked_processes(
    root_pid: int,
    tracked: dict[int, int],
    snapshot: dict[int, ProcessSample],
) -> tuple[dict[int, int], int]:
    root = snapshot.get(root_pid)
    if root is not None:
        tracked.setdefault(root_pid, root.start_ticks)

    changed = True
    while changed:
        changed = False
        parents = set(tracked)
        for pid, sample in snapshot.items():
            if pid not in tracked and sample.parent_pid in parents:
                tracked[pid] = sample.start_ticks
                changed = True

    alive = {
        pid: start_ticks
        for pid, start_ticks in tracked.items()
        if (sample := snapshot.get(pid)) is not None
        and sample.start_ticks == start_ticks
    }
    rss = sum(snapshot[pid].rss_bytes for pid in alive)
    return alive, rss


def _signal_tracked(
    tracked: dict[int, int],
    sig: signal.Signals,
    *,
    proc_root: Path = Path("/proc"),
) -> None:
    snapshot = read_process_snapshot(proc_root) or {}
    for pid, start_ticks in tracked.items():
        sample = snapshot.get(pid)
        if sample is None or sample.start_ticks != start_ticks or pid == os.getpid():
            continue
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            continue


def terminate_batch_process(
    process: subprocess.Popen[bytes],
    tracked: dict[int, int],
    *,
    grace_seconds: float = 0.5,
) -> None:
    if os.name == "posix" and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    _signal_tracked(tracked, signal.SIGTERM)
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        pass
    _signal_tracked(tracked, getattr(signal, "SIGKILL", signal.SIGTERM))
    if process.poll() is None:
        process.kill()
        process.wait()


def run_test_batch(
    modules: tuple[str, ...],
    *,
    cwd: Path = ROOT,
    python_executable: str = sys.executable,
    memory_limit_bytes: int = DEFAULT_MEMORY_LIMIT_MB * 1024 * 1024,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    quiet: bool = False,
) -> BatchResult:
    command = [python_executable, "-m", "unittest"]
    if quiet:
        command.append("-q")
    command.extend(modules)
    started_at = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        start_new_session=os.name == "posix",
    )
    tracked: dict[int, int] = {}
    peak_rss_bytes = 0
    reason: str | None = None
    monitoring_supported = read_process_snapshot() is not None

    while process.poll() is None:
        snapshot = read_process_snapshot()
        if snapshot is not None:
            tracked, rss_bytes = update_tracked_processes(process.pid, tracked, snapshot)
            peak_rss_bytes = max(peak_rss_bytes, rss_bytes)
            if memory_limit_bytes > 0 and rss_bytes > memory_limit_bytes:
                reason = (
                    f"memory limit exceeded: {format_bytes(rss_bytes)} > "
                    f"{format_bytes(memory_limit_bytes)}"
                )
        if reason is None and time.monotonic() - started_at > timeout_seconds:
            reason = f"timeout exceeded: {timeout_seconds:g}s"
        if reason is not None:
            terminate_batch_process(process, tracked)
            break
        time.sleep(poll_interval_seconds)

    returncode = process.wait()
    if monitoring_supported:
        time.sleep(min(0.1, poll_interval_seconds))
        snapshot = read_process_snapshot() or {}
        tracked, rss_bytes = update_tracked_processes(process.pid, tracked, snapshot)
        peak_rss_bytes = max(peak_rss_bytes, rss_bytes)
        leftovers = {pid: started for pid, started in tracked.items() if pid != process.pid}
        if leftovers:
            _signal_tracked(leftovers, signal.SIGTERM)
            time.sleep(0.1)
            _signal_tracked(
                leftovers,
                getattr(signal, "SIGKILL", signal.SIGTERM),
            )
            reason = reason or f"left {len(leftovers)} child process(es) running"

    return BatchResult(
        modules=modules,
        returncode=returncode,
        peak_rss_bytes=peak_rss_bytes,
        duration_seconds=time.monotonic() - started_at,
        reason=reason,
    )


def format_bytes(value: int) -> str:
    return f"{value / (1024 * 1024):.1f} MiB"


def run_test_batches(
    modules: list[str],
    *,
    cwd: Path = ROOT,
    python_executable: str = sys.executable,
    batch_size: int = DEFAULT_BATCH_SIZE,
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    quiet: bool = False,
) -> list[BatchResult]:
    results: list[BatchResult] = []
    batches = partition_modules(modules, batch_size)
    for index, batch in enumerate(batches, start=1):
        print(f"[python-tests] batch {index}/{len(batches)} ({len(batch)} modules)", flush=True)
        result = run_test_batch(
            batch,
            cwd=cwd,
            python_executable=python_executable,
            memory_limit_bytes=memory_limit_mb * 1024 * 1024,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            quiet=quiet,
        )
        results.append(result)
        print(
            f"[python-tests] batch {index}: "
            f"{'ok' if result.ok else 'failed'}, "
            f"peak={format_bytes(result.peak_rss_bytes)}, "
            f"duration={result.duration_seconds:.1f}s"
            + (f", reason={result.reason}" if result.reason else ""),
            flush=True,
        )
        if not result.ok:
            break
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run unittest modules in resource-monitored process batches."
    )
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--memory-limit-mb", type=int, default=DEFAULT_MEMORY_LIMIT_MB)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--module", action="append", dest="modules")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if args.memory_limit_mb < 1:
        parser.error("--memory-limit-mb must be positive")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")

    modules = args.modules or discover_test_modules(pattern=args.pattern)
    if not modules:
        print("No Python test modules found.", file=sys.stderr)
        return 2
    results = run_test_batches(
        modules,
        batch_size=args.batch_size,
        memory_limit_mb=args.memory_limit_mb,
        timeout_seconds=args.timeout_seconds,
        quiet=args.quiet,
    )
    if not results or not all(result.ok for result in results):
        return 1
    print(
        f"[python-tests] {len(modules)} modules passed in {len(results)} batches; "
        f"max peak={format_bytes(max(result.peak_rss_bytes for result in results))}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
