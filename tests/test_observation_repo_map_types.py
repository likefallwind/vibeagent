import unittest

from vibeagent import observation_code_intel_types, observation_repo_map_types


class ObservationRepoMapTypesTests(unittest.TestCase):
    def test_code_intel_types_reexports_repo_map_observations(self) -> None:
        names = [
            "RepoMapPythonFile",
            "RepoMapObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_code_intel_types, name),
                    getattr(observation_repo_map_types, name),
                )


if __name__ == "__main__":
    unittest.main()
