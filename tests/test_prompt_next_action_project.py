from __future__ import annotations

import unittest
from types import SimpleNamespace

from vibeagent.prompt_next_action_project import _available_command_labels, _command_labels


class PromptNextActionProjectTests(unittest.TestCase):
    def test_command_labels_default_cwd_and_skip_empty_commands(self) -> None:
        labels = _command_labels(
            [
                SimpleNamespace(command=" npm test ", cwd=""),
                SimpleNamespace(command="", cwd="."),
                SimpleNamespace(command="python -m unittest", cwd=" tests "),
            ]
        )

        self.assertEqual(labels, ["npm test (cwd=.)", "python -m unittest (cwd=tests)"])

    def test_available_command_labels_skip_unavailable_commands(self) -> None:
        labels = _available_command_labels(
            [
                SimpleNamespace(command="npm test", cwd=".", available=True),
                SimpleNamespace(command="npm run build", cwd="web", available=False),
                SimpleNamespace(command="python -m unittest", cwd=None),
            ]
        )

        self.assertEqual(labels, ["npm test (cwd=.)", "python -m unittest (cwd=.)"])


if __name__ == "__main__":
    unittest.main()
