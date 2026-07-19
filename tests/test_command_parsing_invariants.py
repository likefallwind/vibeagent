import inspect
import re
import unittest
from types import UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

from vibeagent.command_parsing import LocalCommand, parse_local_command


def local_command_literal_values(annotation: object) -> set[str]:
    origin = get_origin(annotation)
    if origin is Literal:
        return set(get_args(annotation))
    if origin in (Union, UnionType):
        values: set[str] = set()
        for arg in get_args(annotation):
            values.update(local_command_literal_values(arg))
        return values
    return set()


class CommandParsingInvariantTests(unittest.TestCase):
    def test_parse_local_command_types_match_local_command_literal(self) -> None:
        source = inspect.getsource(parse_local_command)
        returned_types = set(re.findall(r'LocalCommand\(type="([^"]+)"', source))
        literal_types = local_command_literal_values(get_type_hints(LocalCommand)["type"])

        self.assertEqual(returned_types - literal_types, set())

    def test_help_text_lists_all_parseable_slash_commands(self) -> None:
        from vibeagent.commands import get_help_text

        source = inspect.getsource(parse_local_command)
        slash_commands = set(re.findall(r'trimmed == "(/[^"]+)"', source))
        help_text = get_help_text()

        missing = sorted(command for command in slash_commands if command not in help_text)

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
