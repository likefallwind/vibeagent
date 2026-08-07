import unittest

from vibeagent import observation_project_overview_types, observation_project_types


class ObservationProjectOverviewTypesTests(unittest.TestCase):
    def test_project_types_reexports_project_overview_observation(self) -> None:
        self.assertIs(
            observation_project_types.ProjectOverviewObservation,
            observation_project_overview_types.ProjectOverviewObservation,
        )


if __name__ == "__main__":
    unittest.main()
