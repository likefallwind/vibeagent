import unittest

from vibeagent import observation_code_dependency_types, observation_code_intel_types


class ObservationCodeDependencyTypesTests(unittest.TestCase):
    def test_code_intel_types_reexports_dependency_observations(self) -> None:
        names = [
            "PythonImportRef",
            "PythonDependenciesResult",
            "PythonDependenciesObservation",
            "CodeImportRef",
            "CodeDependenciesResult",
            "CodeDependenciesObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_code_intel_types, name),
                    getattr(observation_code_dependency_types, name),
                )


if __name__ == "__main__":
    unittest.main()
