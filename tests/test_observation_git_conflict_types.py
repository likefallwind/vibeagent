import unittest

from vibeagent import observation_git_conflict_types, observation_git_types


class ObservationGitConflictTypesTests(unittest.TestCase):
    def test_git_types_reexports_conflict_observations(self) -> None:
        names = [
            "GitConflictStatus",
            "GitConflictMarker",
            "GitConflictsObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(observation_git_types, name), getattr(observation_git_conflict_types, name))


if __name__ == "__main__":
    unittest.main()
