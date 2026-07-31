import unittest

from vibeagent import observation_edit_path_types, observation_edit_types


class ObservationEditPathTypesTests(unittest.TestCase):
    def test_edit_observation_module_reexports_path_types(self) -> None:
        names = [
            "DeleteFileObservation",
            "CheckDeleteFileObservation",
            "DeleteFilesObservation",
            "CheckDeleteFilesObservation",
            "MoveFileObservation",
            "CheckMoveFileObservation",
            "MoveFilesObservation",
            "CheckMoveFilesObservation",
            "CopyFileObservation",
            "CheckCopyFileObservation",
            "CopyFilesObservation",
            "CheckCopyFilesObservation",
            "MoveDirectoryObservation",
            "CheckMoveDirectoryObservation",
            "MoveDirectoriesObservation",
            "CheckMoveDirectoriesObservation",
            "CopyDirectoryObservation",
            "CheckCopyDirectoryObservation",
            "CopyDirectoriesObservation",
            "CheckCopyDirectoriesObservation",
            "CreateDirectoryObservation",
            "CheckCreateDirectoryObservation",
            "CreateDirectoriesObservation",
            "CheckCreateDirectoriesObservation",
            "DeleteEmptyDirectoryObservation",
            "CheckDeleteEmptyDirectoryObservation",
            "DeleteEmptyDirectoriesObservation",
            "CheckDeleteEmptyDirectoriesObservation",
            "SetExecutableObservation",
            "CheckSetExecutableObservation",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(observation_edit_types, name), getattr(observation_edit_path_types, name))


if __name__ == "__main__":
    unittest.main()
