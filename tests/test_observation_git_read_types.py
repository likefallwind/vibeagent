import unittest

from vibeagent import observation_git_read_types, observation_git_types


class ObservationGitReadTypesTests(unittest.TestCase):
    def test_git_observation_module_reexports_read_types(self) -> None:
        self.assertIs(observation_git_types.GitDiffHunk, observation_git_read_types.GitDiffHunk)
        self.assertIs(observation_git_types.UntrackedFilePreview, observation_git_read_types.UntrackedFilePreview)
        self.assertIs(observation_git_types.GitDiffObservation, observation_git_read_types.GitDiffObservation)
        self.assertIs(observation_git_types.GitDiffHunksObservation, observation_git_read_types.GitDiffHunksObservation)
        self.assertIs(observation_git_types.GitDiffContext, observation_git_read_types.GitDiffContext)
        self.assertIs(observation_git_types.GitDiffContextsObservation, observation_git_read_types.GitDiffContextsObservation)
        self.assertIs(observation_git_types.GitLogObservation, observation_git_read_types.GitLogObservation)
        self.assertIs(observation_git_types.GitShowObservation, observation_git_read_types.GitShowObservation)
        self.assertIs(observation_git_types.GitBlameObservation, observation_git_read_types.GitBlameObservation)


if __name__ == "__main__":
    unittest.main()
