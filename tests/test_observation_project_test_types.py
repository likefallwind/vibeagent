import unittest

from vibeagent import observation_project_test_types, observation_project_types


class ObservationProjectTestTypesTests(unittest.TestCase):
    def test_project_types_reexports_project_test_observations(self) -> None:
        names = [
            "RelatedTestCandidate",
            "RelatedTestsObservation",
            "FocusedTestCommand",
            "FocusedTestCommandsObservation",
            "CheckFocusedTestCommandsObservation",
            "RunFocusedTestCommandsObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_project_types, name),
                    getattr(observation_project_test_types, name),
                )


if __name__ == "__main__":
    unittest.main()
