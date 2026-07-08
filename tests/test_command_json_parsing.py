import unittest

from vibeagent.command_json_parsing import parse_json_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class CommandJsonParsingTests(unittest.TestCase):
    def test_json_parser_recognizes_config_and_json_commands(self) -> None:
        cases = {
            "/config-check pyproject.toml": LocalCommand(type="config_check", argument="pyproject.toml"),
            "/config-check": LocalCommand(type="config_check"),
            "/check-json-set --create-missing package.json /scripts/test '\"npm test\"'": LocalCommand(
                type="check_json_set",
                argument="--create-missing package.json /scripts/test '\"npm test\"'",
            ),
            "/check-json-set": LocalCommand(type="check_json_set"),
            "/json-set package.json /private true": LocalCommand(
                type="json_set",
                argument="package.json /private true",
            ),
            "/json-set": LocalCommand(type="json_set"),
            "/check-json-remove package.json /scripts/dev": LocalCommand(
                type="check_json_remove",
                argument="package.json /scripts/dev",
            ),
            "/check-json-remove": LocalCommand(type="check_json_remove"),
            "/json-remove package.json /keywords/0": LocalCommand(
                type="json_remove",
                argument="package.json /keywords/0",
            ),
            "/json-remove": LocalCommand(type="json_remove"),
            "/check-json-patch package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'": LocalCommand(
                type="check_json_patch",
                argument="package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'",
            ),
            "/check-json-patch": LocalCommand(type="check_json_patch"),
            "/json-patch package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'": LocalCommand(
                type="json_patch",
                argument="package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'",
            ),
            "/json-patch": LocalCommand(type="json_patch"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_json_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_json_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_json_local_command("/session run-1"))
        self.assertIsNone(parse_json_local_command("json-set package.json /private true"))


if __name__ == "__main__":
    unittest.main()
