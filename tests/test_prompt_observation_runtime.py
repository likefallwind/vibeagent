import unittest

from vibeagent.prompts import format_observations
from vibeagent.types import CheckWriteProcessObservation


class PromptObservationRuntimeTests(unittest.TestCase):
    def test_write_process_observation_renders_stdin_file_source(self) -> None:
        text = format_observations(
            [
                CheckWriteProcessObservation(
                    kind="check_write_process",
                    process_id="proc-1",
                    pid=123,
                    ok=True,
                    running=True,
                    command="python repl.py",
                    cwd=".",
                    content_chars=12,
                    message="Can write process input.",
                    stdin_file="input.txt",
                )
            ]
        )

        self.assertIn("stdinFile: input.txt", text)
        self.assertIn("contentChars: 12", text)


if __name__ == "__main__":
    unittest.main()
