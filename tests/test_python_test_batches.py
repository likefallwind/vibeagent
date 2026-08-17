from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from scripts.run_python_test_batches import (
    ProcessSample,
    discover_test_modules,
    partition_modules,
    run_test_batch,
    update_tracked_processes,
)


class PythonTestBatchRunnerTests(unittest.TestCase):
    def test_discovers_sorted_importable_test_modules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batched-tests-") as base:
            root = Path(base)
            tests = root / "tests"
            nested = tests / "nested"
            nested.mkdir(parents=True)
            for path in (tests / "__init__.py", nested / "__init__.py"):
                path.write_text("", encoding="utf-8")
            (tests / "test_zeta.py").write_text("", encoding="utf-8")
            (nested / "test_alpha.py").write_text("", encoding="utf-8")
            (tests / "test_bad-name.py").write_text("", encoding="utf-8")

            modules = discover_test_modules(root)

        self.assertEqual(modules, ["tests.nested.test_alpha", "tests.test_zeta"])

    def test_partitions_modules_and_rejects_invalid_size(self) -> None:
        self.assertEqual(
            partition_modules(["tests.a", "tests.b", "tests.c"], 2),
            [("tests.a", "tests.b"), ("tests.c",)],
        )
        with self.assertRaisesRegex(ValueError, "positive"):
            partition_modules(["tests.a"], 0)

    def test_tracks_nested_descendants_and_drops_reused_pids(self) -> None:
        snapshot = {
            10: ProcessSample(parent_pid=1, start_ticks=100, rss_bytes=10),
            11: ProcessSample(parent_pid=10, start_ticks=110, rss_bytes=20),
            12: ProcessSample(parent_pid=11, start_ticks=120, rss_bytes=30),
            13: ProcessSample(parent_pid=1, start_ticks=130, rss_bytes=40),
        }

        tracked, rss = update_tracked_processes(10, {99: 1}, snapshot)

        self.assertEqual(tracked, {10: 100, 11: 110, 12: 120})
        self.assertEqual(rss, 60)

    def test_runs_one_isolated_passing_batch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batched-tests-") as base:
            root = Path(base)
            tests = root / "tests"
            tests.mkdir()
            (tests / "__init__.py").write_text("", encoding="utf-8")
            (tests / "test_sample.py").write_text(
                "import unittest\n\n"
                "class SampleTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertEqual(2 + 2, 4)\n",
                encoding="utf-8",
            )

            result = run_test_batch(
                ("tests.test_sample",),
                cwd=root,
                python_executable=sys.executable,
                memory_limit_bytes=256 * 1024 * 1024,
                timeout_seconds=10,
                poll_interval_seconds=0.01,
                quiet=True,
            )

        self.assertTrue(result.ok, result.reason)
        if Path("/proc").is_dir():
            self.assertGreater(result.peak_rss_bytes, 0)

    @unittest.skipUnless(Path("/proc").is_dir(), "requires Linux /proc monitoring")
    def test_stops_a_batch_that_exceeds_memory_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batched-tests-") as base:
            root = Path(base)
            tests = root / "tests"
            tests.mkdir()
            (tests / "__init__.py").write_text("", encoding="utf-8")
            (tests / "test_memory.py").write_text(
                "import time\nimport unittest\n\n"
                "class MemoryTests(unittest.TestCase):\n"
                "    def test_wait(self):\n"
                "        time.sleep(2)\n",
                encoding="utf-8",
            )

            result = run_test_batch(
                ("tests.test_memory",),
                cwd=root,
                python_executable=sys.executable,
                memory_limit_bytes=1024 * 1024,
                timeout_seconds=10,
                poll_interval_seconds=0.01,
                quiet=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("memory limit exceeded", result.reason or "")

    def test_stops_a_batch_that_exceeds_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-batched-tests-") as base:
            root = Path(base)
            tests = root / "tests"
            tests.mkdir()
            (tests / "__init__.py").write_text("", encoding="utf-8")
            (tests / "test_timeout.py").write_text(
                "import time\nimport unittest\n\n"
                "class TimeoutTests(unittest.TestCase):\n"
                "    def test_wait(self):\n"
                "        time.sleep(2)\n",
                encoding="utf-8",
            )

            result = run_test_batch(
                ("tests.test_timeout",),
                cwd=root,
                python_executable=sys.executable,
                memory_limit_bytes=256 * 1024 * 1024,
                timeout_seconds=0.05,
                poll_interval_seconds=0.01,
                quiet=True,
            )

        self.assertFalse(result.ok)
        self.assertIn("timeout exceeded", result.reason or "")


if __name__ == "__main__":
    unittest.main()
