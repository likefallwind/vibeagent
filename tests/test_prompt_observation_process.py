import unittest
from types import SimpleNamespace

from vibeagent.prompt_observation_process import format_process_observation
from vibeagent.prompt_observation_runtime import format_runtime_observation


class PromptObservationProcessTests(unittest.TestCase):
    def test_runtime_observation_delegates_process_kinds_to_process_module(self) -> None:
        observation = SimpleNamespace(
            kind="read_process",
            process_id="bg-1",
            message="Process output read.",
            pid=123,
            running=False,
            exit_code=0,
            signal=None,
            max_output_chars=2000,
            stdout="ok\n",
            stderr="",
        )

        self.assertEqual(
            format_runtime_observation(1, observation),
            format_process_observation(1, observation),
        )

    def test_process_observation_ignores_non_process_kinds(self) -> None:
        observation = SimpleNamespace(kind="environment_info")

        self.assertIsNone(format_process_observation(1, observation))


if __name__ == "__main__":
    unittest.main()
