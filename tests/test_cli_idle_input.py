from __future__ import annotations

from threading import Event, get_ident
import unittest
from unittest.mock import patch

from vibeagent.cli_idle_input import input_with_idle_callback


class CliIdleInputTests(unittest.TestCase):
    def test_runs_idle_callback_until_input_arrives(self) -> None:
        release = Event()
        calls: list[str] = []

        def delayed_input(prompt: str) -> str:
            release.wait(timeout=1)
            return "continue"

        def on_idle() -> None:
            calls.append("idle")
            release.set()

        result = input_with_idle_callback(
            "prompt",
            on_idle,
            input_func=delayed_input,
            interval_seconds=0.01,
        )

        self.assertEqual(result, "continue")
        self.assertEqual(calls, ["idle"])

    def test_propagates_input_exceptions(self) -> None:
        def failed_input(prompt: str) -> str:
            raise EOFError

        with self.assertRaises(EOFError):
            input_with_idle_callback(
                "prompt",
                lambda: None,
                input_func=failed_input,
                interval_seconds=0.01,
            )

    def test_terminal_path_keeps_input_on_caller_and_runs_idle_callback_in_worker(self) -> None:
        release = Event()
        caller_thread = get_ident()
        input_threads: list[int] = []
        idle_threads: list[int] = []

        def terminal_input(prompt: str) -> str:
            input_threads.append(get_ident())
            release.wait(timeout=1)
            return "continue"

        def on_idle() -> None:
            idle_threads.append(get_ident())
            release.set()

        with patch("vibeagent.cli_idle_input._can_use_main_thread_terminal_input", return_value=True):
            result = input_with_idle_callback(
                "prompt",
                on_idle,
                input_func=terminal_input,
                interval_seconds=0.01,
            )

        self.assertEqual(result, "continue")
        self.assertEqual(input_threads, [caller_thread])
        self.assertEqual(len(idle_threads), 1)
        self.assertNotEqual(idle_threads[0], caller_thread)

    def test_terminal_path_propagates_idle_callback_error_after_input_finishes(self) -> None:
        release = Event()

        def terminal_input(prompt: str) -> str:
            release.wait(timeout=1)
            return "continue"

        def on_idle() -> None:
            release.set()
            raise RuntimeError("idle failed")

        with (
            patch("vibeagent.cli_idle_input._can_use_main_thread_terminal_input", return_value=True),
            self.assertRaisesRegex(RuntimeError, "idle failed"),
        ):
            input_with_idle_callback(
                "prompt",
                on_idle,
                input_func=terminal_input,
                interval_seconds=0.01,
            )


if __name__ == "__main__":
    unittest.main()
