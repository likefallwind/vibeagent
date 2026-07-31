import unittest
from types import SimpleNamespace

from vibeagent.prompt_observation_git import format_git_observation
from vibeagent.prompt_observation_git_sync import (
    format_git_fetch_observation,
    format_git_switch_observation,
)


class PromptObservationGitSyncTests(unittest.TestCase):
    def test_git_observation_delegates_fetch_to_sync_module(self) -> None:
        observation = SimpleNamespace(
            kind="check_git_fetch",
            remote="origin",
            message="Fetch preview ready.",
            ok=True,
            remote_url="git@example.com:repo.git",
            branch="main",
            upstream="origin/main",
            ahead=1,
            behind=2,
        )

        self.assertEqual(format_git_observation(1, observation), format_git_fetch_observation(1, observation))

    def test_git_switch_observation_formats_branch_state(self) -> None:
        observation = SimpleNamespace(
            kind="git_switch",
            branch="feature/demo",
            message="Switched branch.",
            ok=True,
            create=False,
            current_before="main",
            current_after="feature/demo",
            status="",
        )

        text = format_git_switch_observation(2, observation)

        self.assertIn("git_switch feature/demo", text)
        self.assertIn("currentBefore: main", text)
        self.assertIn("currentAfter: feature/demo", text)


if __name__ == "__main__":
    unittest.main()
