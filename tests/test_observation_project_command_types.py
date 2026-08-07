import unittest

from vibeagent import observation_project_command_types, observation_project_types


class ObservationProjectCommandTypesTests(unittest.TestCase):
    def test_project_types_reexports_project_command_observations(self) -> None:
        names = [
            "ProjectCommand",
            "ProjectCommandsObservation",
            "ToolSearchObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_project_types, name),
                    getattr(observation_project_command_types, name),
                )


if __name__ == "__main__":
    unittest.main()
