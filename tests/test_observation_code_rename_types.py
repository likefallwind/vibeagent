import unittest

from vibeagent import observation_code_intel_types, observation_code_rename_types


class ObservationCodeRenameTypesTests(unittest.TestCase):
    def test_code_intel_types_reexports_rename_observations(self) -> None:
        names = [
            "CodeRenameReplacement",
            "CodeRenamePreviewFile",
            "CodeRenamePreviewObservation",
            "CodeRenameObservation",
            "PythonRenameReplacement",
            "PythonRenamePreviewFile",
            "PythonRenamePreviewObservation",
            "PythonRenameObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(observation_code_intel_types, name), getattr(observation_code_rename_types, name))


if __name__ == "__main__":
    unittest.main()
