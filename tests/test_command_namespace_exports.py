import unittest
from types import ModuleType

from vibeagent.command_namespace_exports import (
    command_exports_from_modules,
    install_command_exports_from_modules,
)


class CommandNamespaceExportsTests(unittest.TestCase):
    def test_merges_public_exports_and_ignores_internal_helpers(self) -> None:
        first = ModuleType("first_commands")
        second = ModuleType("second_commands")
        first.get_first = object()
        first.format_first_report_text = object()
        first.parse_local_command = object()
        first.get_blocked_command_reason = object()
        second.get_second = object()

        exports = command_exports_from_modules((first, second))

        self.assertEqual(
            exports,
            {
                "format_first_report_text": first.format_first_report_text,
                "get_first": first.get_first,
                "get_second": second.get_second,
                "parse_local_command": first.parse_local_command,
            },
        )

    def test_allows_the_same_export_object_from_multiple_modules(self) -> None:
        first = ModuleType("first_commands")
        second = ModuleType("second_commands")
        shared = object()
        first.get_shared = shared
        second.get_shared = shared

        target: dict[str, object] = {}
        names = install_command_exports_from_modules(target, (first, second))

        self.assertEqual(names, ["get_shared"])
        self.assertIs(target["get_shared"], shared)

    def test_rejects_conflicting_export_objects(self) -> None:
        first = ModuleType("first_commands")
        second = ModuleType("second_commands")
        first.get_shared = object()
        second.get_shared = object()

        with self.assertRaisesRegex(
            ValueError,
            "Conflicting command export 'get_shared' from first_commands and second_commands",
        ):
            command_exports_from_modules((first, second))


if __name__ == "__main__":
    unittest.main()
