from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vibeagent import process_command_runtime, process_runtime
from vibeagent.command_output_observers import observe_command_output


class ProcessCommandRuntimeModuleTests(unittest.TestCase):
    def test_process_runtime_reexports_command_runtime_helpers(self) -> None:
        self.assertIs(process_runtime.run_command, process_command_runtime.run_command)
        self.assertIs(process_runtime.wrap_background_command, process_command_runtime.wrap_background_command)
        self.assertIs(process_runtime.relative_cwd, process_command_runtime.relative_cwd)
        self.assertIs(process_runtime.truncate_command_output, process_command_runtime.truncate_command_output)

    def test_relative_cwd_reports_project_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            child = root / "pkg" / "tests"
            child.mkdir(parents=True)

            self.assertEqual(process_command_runtime.relative_cwd(child, root), "pkg/tests")
            self.assertEqual(process_command_runtime.relative_cwd(root, root), ".")

    def test_truncate_command_output_keeps_head_and_tail(self) -> None:
        value, truncated = process_command_runtime.truncate_command_output("abcdef", 5)

        self.assertEqual(value, "abcde")
        self.assertTrue(truncated)

        longer, longer_truncated = process_command_runtime.truncate_command_output("0123456789" * 20, 80)
        self.assertTrue(longer.startswith("0123"))
        self.assertIn("[truncated to 80 chars: showing head and tail]", longer)
        self.assertTrue(longer.endswith("6789"))
        self.assertTrue(longer_truncated)

    def test_run_command_streams_stdout_and_stderr_to_scoped_observer(self) -> None:
        observed: list[tuple[str, str]] = []

        with tempfile.TemporaryDirectory() as temp, observe_command_output(
            lambda stdout, stderr: observed.append((stdout, stderr))
        ):
            result = process_command_runtime.run_command(
                temp,
                "printf 'out\\n'; printf 'err\\n' >&2",
            )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "out\n")
        self.assertEqual(result.stderr, "err\n")
        self.assertIn(("out\n", ""), observed)
        self.assertIn(("", "err\n"), observed)


if __name__ == "__main__":
    unittest.main()
