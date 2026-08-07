import unittest
from unittest.mock import ANY, patch

from vibeagent import python_action_executor
from vibeagent import python_intel_action_executor
from vibeagent.types import PythonCheckAction, PythonCheckObservation, RunCommandAction


class PythonActionExecutorModuleTests(unittest.TestCase):
    def test_python_action_executor_delegates_intel_actions(self) -> None:
        action = PythonCheckAction(type="python_check", path=".", max_files=10)
        observation = PythonCheckObservation(
            kind="python_check",
            path=".",
            files=[],
            total=0,
            truncated=False,
            ok=True,
            message="Checked 0/0 Python file(s); 0 failed.",
        )

        with patch(
            "vibeagent.python_action_executor.execute_python_intel_action",
            return_value=observation,
        ) as execute_python_intel_action:
            result = python_action_executor.execute_python_action(object(), action)

        self.assertIs(result, observation)
        execute_python_intel_action.assert_called_once_with(ANY, action)

    def test_python_intel_action_executor_ignores_unrelated_actions(self) -> None:
        action = RunCommandAction(type="run_command", command="python --version")

        self.assertIsNone(python_intel_action_executor.execute_python_intel_action(object(), action))


if __name__ == "__main__":
    unittest.main()
