import unittest

from vibeagent import action_file_edit_types, action_file_path_types, types


class ActionFilePathTypesTests(unittest.TestCase):
    def test_file_edit_types_reexports_path_action_types(self) -> None:
        for name in [
            "DeleteFileAction",
            "MoveFileAction",
            "MoveFileTransfer",
            "MoveDirectoryAction",
            "DirectoryTransfer",
            "CreateDirectoryAction",
            "SetExecutableAction",
        ]:
            with self.subTest(name=name):
                self.assertIs(getattr(action_file_edit_types, name), getattr(action_file_path_types, name))
                self.assertIs(getattr(types, name), getattr(action_file_path_types, name))


if __name__ == "__main__":
    unittest.main()
