from __future__ import annotations

from threading import Event
import unittest

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


if __name__ == "__main__":
    unittest.main()
