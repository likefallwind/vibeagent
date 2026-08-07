import unittest

from vibeagent import observation_code_intel_types, observation_code_reference_types


class ObservationCodeReferenceTypesTests(unittest.TestCase):
    def test_code_intel_types_reexports_reference_observations(self) -> None:
        names = [
            "CodeReference",
            "CodeReferencesObservation",
            "ReferenceContextResult",
            "CodeReferenceContextsObservation",
            "PythonReference",
            "PythonReferencesObservation",
            "PythonReferenceContextsObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(observation_code_intel_types, name),
                    getattr(observation_code_reference_types, name),
                )


if __name__ == "__main__":
    unittest.main()
