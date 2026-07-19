import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

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
