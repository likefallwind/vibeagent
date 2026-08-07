import unittest

from vibeagent import observation_project_resource_types, observation_project_types


class ObservationProjectResourceTypesTests(unittest.TestCase):
    def test_project_types_reexports_project_resource_observations(self) -> None:
        names = [
            "ProjectManifestItem",
            "ProjectManifest",
            "ProjectManifestsObservation",
            "ProjectInstructionSource",
            "ProjectInstructionsObservation",
            "ProjectSkill",
            "ProjectSkillsObservation",
            "ProjectAgentProfile",
            "ProjectAgentsObservation",
            "SkillObservation",
            "ProjectTodo",
            "ProjectTodosObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_project_types, name),
                    getattr(observation_project_resource_types, name),
                )


if __name__ == "__main__":
    unittest.main()
