import unittest

from vibeagent import workspace_code_intel
from vibeagent import workspace_generic_code_intel
from vibeagent import workspace_generic_code_lookup


class WorkspaceGenericCodeIntelTests(unittest.TestCase):
    def test_workspace_code_intel_reexports_generic_code_helpers(self) -> None:
        names = [
            "read_code_outline",
            "inspect_code_dependencies",
            "find_code_references",
            "find_code_definitions",
            "preview_code_rename",
            "apply_code_rename",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertIs(getattr(workspace_code_intel, name), getattr(workspace_generic_code_intel, name))

    def test_generic_code_intel_reexports_lookup_helpers(self) -> None:
        for name in [
            "read_code_outline",
            "inspect_code_dependencies",
            "find_code_references",
            "find_code_definitions",
        ]:
            with self.subTest(name=name):
                self.assertIs(getattr(workspace_generic_code_intel, name), getattr(workspace_generic_code_lookup, name))


if __name__ == "__main__":
    unittest.main()
