from __future__ import annotations

import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from vibeagent.bounded_subprocess import run_bounded_subprocess


class BoundedSubprocessTests(unittest.TestCase):
    def test_drains_large_stdout_and_stderr_with_exact_totals(self) -> None:
        stdout = "o" * 2_000_000
        stderr = "e" * 1_000_000

        result = run_bounded_subprocess(
            (
                sys.executable,
                "-c",
                "import sys;sys.stdout.write('o'*2000000);sys.stderr.write('e'*1000000)",
            ),
            timeout_ms=5_000,
            max_output_chars=1_000,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout), 1_000)
        self.assertEqual(len(result.stderr), 1_000)
        self.assertTrue(result.stdout_truncated)
        self.assertTrue(result.stderr_truncated)
        self.assertEqual(result.stdout_total_chars, len(stdout))
        self.assertEqual(result.stderr_total_chars, len(stderr))

    def test_raises_timeout_after_terminating_process(self) -> None:
        started = time.monotonic()

        with self.assertRaises(subprocess.TimeoutExpired):
            run_bounded_subprocess(
                (sys.executable, "-c", "import time;time.sleep(30)"),
                timeout_ms=50,
                max_output_chars=1_000,
            )

        self.assertLess(time.monotonic() - started, 2)

    def test_rejects_invalid_limits_before_starting_process(self) -> None:
        with patch("vibeagent.bounded_subprocess.subprocess.Popen") as popen:
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                run_bounded_subprocess((), timeout_ms=1, max_output_chars=1)
            with self.assertRaisesRegex(ValueError, "timeout"):
                run_bounded_subprocess(("tool",), timeout_ms=0, max_output_chars=1)
            with self.assertRaisesRegex(ValueError, "output character"):
                run_bounded_subprocess(("tool",), timeout_ms=1, max_output_chars=0)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
