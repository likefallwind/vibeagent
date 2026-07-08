import unittest

from vibeagent.command_inspection_parsing import parse_inspection_local_command
from vibeagent.command_parsing import LocalCommand, parse_local_command


class CommandInspectionParsingTests(unittest.TestCase):
    def test_inspection_parser_recognizes_inspection_commands(self) -> None:
        cases = {
            "/overview": LocalCommand(type="overview"),
            "/overview --max-files 7": LocalCommand(type="overview", argument="--max-files 7"),
            "/repo-map": LocalCommand(type="repo_map"),
            "/repo-map src": LocalCommand(type="repo_map", argument="src"),
            "/search needle": LocalCommand(type="search", argument="needle"),
            "/search": LocalCommand(type="search"),
            "/search-contexts needle": LocalCommand(type="search_contexts", argument="needle"),
            "/search-contexts": LocalCommand(type="search_contexts"),
            "/find-files app.py": LocalCommand(type="find_files", argument="app.py"),
            "/find-files": LocalCommand(type="find_files"),
            "/glob **/*.py": LocalCommand(type="glob", argument="**/*.py"),
            "/glob": LocalCommand(type="glob"),
            "/tree src": LocalCommand(type="tree", argument="src"),
            "/tree": LocalCommand(type="tree"),
            "/symbols src/app.py web/app.ts": LocalCommand(type="symbols", argument="src/app.py web/app.ts"),
            "/symbols": LocalCommand(type="symbols"),
            "/file-info src/app.py asset.bin": LocalCommand(type="file_info", argument="src/app.py asset.bin"),
            "/file-info": LocalCommand(type="file_info"),
            "/image-info assets/logo.png": LocalCommand(type="image_info", argument="assets/logo.png"),
            "/image-info": LocalCommand(type="image_info"),
            "/read src/app.py 2:4": LocalCommand(type="read", argument="src/app.py 2:4"),
            "/read": LocalCommand(type="read"),
            "/around src/app.py 42 8": LocalCommand(type="around", argument="src/app.py 42 8"),
            "/around": LocalCommand(type="around"),
            "/around-many src/app.py:42:8 tests/test_app.py:17": LocalCommand(
                type="around_many",
                argument="src/app.py:42:8 tests/test_app.py:17",
            ),
            "/around-many": LocalCommand(type="around_many"),
            "/output-contexts src/app.py:42:8": LocalCommand(
                type="output_contexts",
                argument="src/app.py:42:8",
            ),
            "/output-contexts": LocalCommand(type="output_contexts"),
            "/output-diagnostics src/app.py:42:8 error": LocalCommand(
                type="output_diagnostics",
                argument="src/app.py:42:8 error",
            ),
            "/output-diagnostics": LocalCommand(type="output_diagnostics"),
            "/python-traceback Traceback": LocalCommand(type="python_traceback", argument="Traceback"),
            "/python-traceback": LocalCommand(type="python_traceback"),
            "/tail logs/app.log 40": LocalCommand(type="tail", argument="logs/app.log 40"),
            "/tail": LocalCommand(type="tail"),
            "/read-files src/app.py tests/test_app.py": LocalCommand(
                type="read_files",
                argument="src/app.py tests/test_app.py",
            ),
            "/read-files": LocalCommand(type="read_files"),
            "/read-ranges src/app.py:2:4 tests/test_app.py:1": LocalCommand(
                type="read_ranges",
                argument="src/app.py:2:4 tests/test_app.py:1",
            ),
            "/read-ranges": LocalCommand(type="read_ranges"),
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_inspection_local_command(raw), expected)
                self.assertEqual(parse_local_command(raw), expected)

    def test_inspection_parser_ignores_other_commands(self) -> None:
        self.assertIsNone(parse_inspection_local_command("/session run-1"))
        self.assertIsNone(parse_inspection_local_command("read src/app.py"))


if __name__ == "__main__":
    unittest.main()
