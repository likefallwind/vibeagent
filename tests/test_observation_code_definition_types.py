import unittest

from vibeagent import observation_code_definition_types, observation_code_intel_types


class ObservationCodeDefinitionTypesTests(unittest.TestCase):
    def test_code_intel_types_reexports_definition_observations(self) -> None:
        names = [
            "CodeDefinition",
            "CodeDefinitionsObservation",
            "PythonDefinition",
            "PythonDefinitionsObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_code_intel_types, name),
                    getattr(observation_code_definition_types, name),
                )


if __name__ == "__main__":
    unittest.main()
