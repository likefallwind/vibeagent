import unittest

from vibeagent import observation_code_intel_types, observation_python_call_types


class ObservationPythonCallTypesTests(unittest.TestCase):
    def test_code_intel_types_reexports_python_call_observations(self) -> None:
        names = [
            "PythonCall",
            "PythonCallsObservation",
            "PythonCallGraphObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_code_intel_types, name),
                    getattr(observation_python_call_types, name),
                )


if __name__ == "__main__":
    unittest.main()
