import unittest

from vibeagent import observation_git_sync_types, observation_git_types


class ObservationGitSyncTypesTests(unittest.TestCase):
    def test_git_types_reexports_sync_observations(self) -> None:
        names = [
            "CheckGitFetchObservation",
            "GitFetchObservation",
            "CheckGitPullObservation",
            "GitPullObservation",
            "CheckGitPushObservation",
            "GitPushObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(observation_git_types, name), getattr(observation_git_sync_types, name))


if __name__ == "__main__":
    unittest.main()
