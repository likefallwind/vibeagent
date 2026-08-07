import unittest

from vibeagent import observation_project_check_types, observation_project_types


class ObservationProjectCheckTypesTests(unittest.TestCase):
    def test_project_types_reexports_project_check_observations(self) -> None:
        names = [
            "SuggestedCheck",
            "SuggestChecksObservation",
            "CheckSuggestedChecksObservation",
            "RunSuggestedChecksObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_project_types, name),
                    getattr(observation_project_check_types, name),
                )


if __name__ == "__main__":
    unittest.main()
