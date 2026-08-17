from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from vibeagent.command_output_observers import observe_command_output
from vibeagent.process_command_capture import (
    BoundedTextCapture,
    OUTPUT_READ_CHUNK_CHARS,
)
from vibeagent.process_command_runtime import run_command, truncate_command_output


class ProcessCommandCaptureTests(unittest.TestCase):
    def test_capture_matches_head_tail_truncation_and_tracks_utf8_bytes(self) -> None:
        raw = "start-" + "\u00e9" * 200 + "-end"
        capture = BoundedTextCapture(80, preserve_complete=True)
        try:
            for offset in range(0, len(raw), 17):
                capture.append(raw[offset : offset + 17])

            self.assertEqual(capture.render(), truncate_command_output(raw, 80))
            self.assertEqual(capture.total_chars, len(raw))
            self.assertEqual(capture.total_bytes, len(raw.encode("utf-8")))
            stream = capture.complete_stream
            self.assertIsNotNone(stream)
            assert stream is not None
            self.assertEqual(stream.read(), raw.encode("utf-8"))
        finally:
            capture.close()

    def test_capture_renders_prefix_suffix_and_discards_oversized_spool(self) -> None:
        raw = "0123456789" * 20
        prefix = "warning\n"
        suffix = "\nlimit exceeded\n"
        capture = BoundedTextCapture(80, preserve_complete=True, max_complete_bytes=32)
        try:
            capture.append(raw)

            self.assertEqual(
                capture.render(prefix=prefix, suffix=suffix),
                truncate_command_output(f"{prefix}{raw}{suffix}", 80),
            )
            self.assertTrue(capture.complete_overflow)
            self.assertIsNone(capture.complete_stream)
        finally:
            capture.close()

    def test_run_command_bounds_unbroken_dual_streams_with_and_without_observer(self) -> None:
        stdout = "A" * 200_000
        stderr = "B" * 180_000
        script = "import sys;sys.stdout.write('A'*200000);sys.stderr.write('B'*180000)"
        with tempfile.TemporaryDirectory() as temp:
            unobserved = run_command(
                temp,
                "large dual stream",
                argv=(sys.executable, "-c", script),
                max_output_chars=1_000,
            )
            observed: list[tuple[str, str]] = []
            with observe_command_output(lambda out, err: observed.append((out, err))):
                streamed = run_command(
                    temp,
                    "large observed dual stream",
                    argv=(sys.executable, "-c", script),
                    max_output_chars=1_000,
                )

        for result in (unobserved, streamed):
            self.assertEqual(result.exit_code, 0)
            self.assertEqual((result.stdout, result.stdout_truncated), truncate_command_output(stdout, 1_000))
            self.assertEqual((result.stderr, result.stderr_truncated), truncate_command_output(stderr, 1_000))
            self.assertEqual(result.stdout_total_bytes, len(stdout))
            self.assertEqual(result.stderr_total_bytes, len(stderr))
        self.assertTrue(observed)
        self.assertTrue(
            all(max(len(out), len(err)) <= OUTPUT_READ_CHUNK_CHARS for out, err in observed)
        )

    def test_observer_failure_terminates_command_without_waiting_for_timeout(self) -> None:
        def fail_observer(_stdout: str, _stderr: str) -> None:
            raise RuntimeError("observer failed")

        script = "import sys,time;print('ready', flush=True);time.sleep(10)"
        with tempfile.TemporaryDirectory() as temp, observe_command_output(fail_observer):
            started = time.monotonic()
            with self.assertRaisesRegex(RuntimeError, "observer failed"):
                run_command(
                    temp,
                    "observer failure",
                    argv=(sys.executable, "-c", script),
                    timeout_ms=5_000,
                )
            duration = time.monotonic() - started

        self.assertLess(duration, 3)

    @unittest.skipIf(os.name == "nt", "POSIX process-group behavior")
    def test_timeout_covers_child_that_keeps_pipe_open_after_parent_exit(self) -> None:
        child = "import time; time.sleep(10)"
        script = f"import subprocess, sys; subprocess.Popen([sys.executable, '-c', {child!r}])"

        with tempfile.TemporaryDirectory() as temp:
            started = time.monotonic()
            result = run_command(
                Path(temp),
                "detached pipe holder",
                argv=(sys.executable, "-c", script),
                timeout_ms=200,
            )
            duration = time.monotonic() - started

        self.assertTrue(result.timed_out)
        self.assertLess(duration, 3)


if __name__ == "__main__":
    unittest.main()
