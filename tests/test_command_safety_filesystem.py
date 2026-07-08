import unittest

from vibeagent import command_safety_filesystem, command_safety_shell


class CommandSafetyFilesystemTests(unittest.TestCase):
    def test_shell_module_reexports_filesystem_helpers(self) -> None:
        self.assertIs(
            command_safety_shell.command_contains_dangerous_rm,
            command_safety_filesystem.command_contains_dangerous_rm,
        )
        self.assertIs(command_safety_shell.command_writes_to_device, command_safety_filesystem.command_writes_to_device)
        self.assertIs(command_safety_shell.is_raw_device_write_target, command_safety_filesystem.is_raw_device_write_target)


if __name__ == "__main__":
    unittest.main()
