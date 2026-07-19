import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import call, patch

from vibeagent.cli import main


class CliProjectInspectionFlagTests(unittest.TestCase):
    def test_main_inspection_local_flags_exit_nonzero_for_failed_results(self) -> None:
        cases = [
            (
                ["--tree", "missing-dir"],
                "vibeagent.cli.get_tree_text",
                "Tree:\n  ok: no\n  message: Path does not exist: missing-dir",
                (Path, "missing-dir"),
            ),
            (
                ["--image-info", "missing.png"],
                "vibeagent.cli.get_image_info_text",
                "Image info:\n  images: 0/1",
                (Path, ["missing.png"]),
            ),
        ]

        for argv_tail, patch_target, text, expected_args in cases:
            with self.subTest(argv=argv_tail), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(patch_target, return_value=text) as getter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--cwd", base, *argv_tail])

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), f"{text}\n")
            resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
            getter.assert_called_once_with(*resolved_args)
            create_chat_client.assert_not_called()

    def test_main_runs_symbols_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--symbols", "src/app.py", "web/app.ts"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", stdout.getvalue())
        get_symbols_text.assert_called_once_with(Path(base).resolve(), ["src/app.py", "web/app.ts"])
        create_chat_client.assert_not_called()

    def test_main_runs_symbols_local_flag_with_max_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--symbols", "src/app.py", "web/app.ts", "--symbols-max", "12"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", stdout.getvalue())
        get_symbols_text.assert_called_once_with(Path(base).resolve(), ["src/app.py", "web/app.ts"], max_symbols=12)
        create_chat_client.assert_not_called()

    def test_main_project_inspection_json_outputs_structured_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            root = Path(base)
            (root / "src").mkdir()
            (root / "src" / "pkg").mkdir()
            (root / "web").mkdir()
            (root / "src" / "app.py").write_text(
                "import os\n\nclass App:\n    pass\n\ndef main():\n    return os.getcwd()\n",
                encoding="utf-8",
            )
            (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "web" / "app.ts").write_text(
                "import { readFile } from 'fs';\nexport class View {}\nexport function render() {}\n",
                encoding="utf-8",
            )

            def run_json(*argv: str) -> tuple[int, dict[str, object]]:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(["--json", "--cwd", base, *argv])
                return exit_code, json.loads(stdout.getvalue())

            with patch("vibeagent.cli.create_chat_client") as create_chat_client:
                glob_exit, glob_payload = run_json("--glob", "**/*.py", "--glob-max-matches", "5", "--glob-include-dirs")
                tree_exit, tree_payload = run_json("--tree", "src", "--tree-max-depth", "3", "--tree-max-entries", "20")
                symbols_exit, symbols_payload = run_json("--symbols", "src/app.py", "web/app.ts", "--symbols-max", "20")

        self.assertEqual(glob_exit, 0)
        self.assertEqual(glob_payload["glob"]["pattern"], "**/*.py")
        self.assertTrue(glob_payload["glob"]["includeDirs"])
        self.assertEqual(glob_payload["glob"]["matches"]["shown"], 2)
        self.assertIn("src/app.py", glob_payload["glob"]["matches"]["files"])
        self.assertEqual(tree_exit, 0)
        self.assertEqual(tree_payload["tree"]["path"], "src")
        self.assertEqual(tree_payload["tree"]["entries"]["shown"], 3)
        self.assertIn("src/pkg/", tree_payload["tree"]["entries"]["items"])
        self.assertEqual(symbols_exit, 0)
        self.assertEqual(symbols_payload["symbols"]["files"]["ok"], 2)
        self.assertEqual(symbols_payload["symbols"]["counts"], {"symbols": 4, "imports": 2})
        self.assertEqual(symbols_payload["symbols"]["files"]["items"][0]["symbols"][0]["name"], "App")
        self.assertEqual(symbols_payload["symbols"]["files"]["items"][1]["language"], "typescript")
        create_chat_client.assert_not_called()

    def test_main_rejects_symbols_max_without_symbols_local_flag(self) -> None:
        stdout = io.StringIO()

        with (
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            redirect_stdout(stdout),
        ):
            exit_code = main(["--symbols-max", "12"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "--symbols-max can only be used with --symbols.\n")
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_glob_tree_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/glob --max-matches 7 --include-dirs -- **/*.py",
                    "/tree src --max-depth 2 --max-entries 30",
                    "/tree --max-depth=0 --max-entries=5",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1") as get_glob_text,
            patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1") as get_tree_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Glob:", output)
        self.assertIn("Tree:", output)
        get_glob_text.assert_called_once_with(pattern="**/*.py", max_matches=7, include_dirs=True)
        self.assertEqual(
            get_tree_text.call_args_list,
            [
                call(path="src", max_depth=2, max_entries=30),
                call(path=None, max_depth=0, max_entries=5),
            ],
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_glob_tree_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/glob --max-matches 0 -- **/*.py",
                    "/glob --max-matches 5",
                    "/glob --include-dirs=maybe -- **/*.py",
                    "/glob --unknown 1 -- **/*.py",
                    "/tree --max-depth -1",
                    "/tree src --max-entries 0",
                    "/tree src other --max-depth 1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_glob_text") as get_glob_text,
            patch("vibeagent.cli.get_tree_text") as get_tree_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /glob [--max-matches N] [--include-dirs] -- <pattern>", output)
        self.assertIn("--max-matches must be a positive integer.", output)
        self.assertIn("pattern is required.", output)
        self.assertIn("--include-dirs must be a boolean.", output)
        self.assertIn("Unknown option: --unknown", output)
        self.assertIn("Usage: /tree [path] [--max-depth N] [--max-entries N]", output)
        self.assertIn("--max-depth must be a non-negative integer.", output)
        self.assertIn("--max-entries must be a positive integer.", output)
        get_glob_text.assert_not_called()
        get_tree_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_symbols_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/symbols --max-symbols 12 -- src/app.py web/app.ts",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1") as get_symbols_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Symbols:", output)
        get_symbols_text.assert_called_once_with(argument=["src/app.py", "web/app.ts"], max_symbols=12)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_symbols_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/symbols --max-symbols 0 -- src/app.py",
                    "/symbols --max-symbols 12",
                    "/symbols --unknown 1 -- src/app.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_symbols_text") as get_symbols_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /symbols [--max-symbols N] -- <path...>", output)
        self.assertIn("--max-symbols must be a positive integer.", output)
        self.assertIn("at least one path is required.", output)
        self.assertIn("Unknown option: --unknown", output)
        get_symbols_text.assert_not_called()
        create_chat_client.assert_not_called()
