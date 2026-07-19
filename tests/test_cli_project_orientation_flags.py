import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from vibeagent.cli import main


class CliProjectOrientationFlagTests(unittest.TestCase):
    def test_main_runs_overview_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1") as get_overview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--overview"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Overview:", stdout.getvalue())
        get_overview_text.assert_called_once_with(Path(base).resolve())
        create_chat_client.assert_not_called()

    def test_main_runs_overview_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1") as get_overview_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--overview",
                        "--overview-max-files",
                        "7",
                        "--overview-max-commands",
                        "3",
                        "--overview-max-checks",
                        "2",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Overview:", stdout.getvalue())
        get_overview_text.assert_called_once_with(Path(base).resolve(), max_files=7, max_commands=3, max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_runs_repo_map_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1") as get_repo_map_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--repo-map", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Repo map:", stdout.getvalue())
        get_repo_map_text.assert_called_once_with(Path(base).resolve(), "src")
        create_chat_client.assert_not_called()

    def test_main_runs_repo_map_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1") as get_repo_map_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--repo-map",
                        "src",
                        "--repo-map-max-depth",
                        "2",
                        "--repo-map-max-files",
                        "8",
                        "--repo-map-max-symbols",
                        "9",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Repo map:", stdout.getvalue())
        get_repo_map_text.assert_called_once_with(Path(base).resolve(), "src", max_depth=2, max_files=8, max_symbols=9)
        create_chat_client.assert_not_called()

    def test_main_rejects_overview_repo_map_bounds_without_matching_local_flag(self) -> None:
        cases = [
            (["--overview-max-files", "7"], "--overview-max-files can only be used with --overview."),
            (["--overview-max-commands", "3"], "--overview-max-commands can only be used with --overview."),
            (["--overview-max-checks", "2"], "--overview-max-checks can only be used with --overview."),
            (["--repo-map-max-depth", "2"], "--repo-map-max-depth can only be used with --repo-map."),
            (["--repo-map-max-files", "8"], "--repo-map-max-files can only be used with --repo-map."),
            (["--repo-map-max-symbols", "9"], "--repo-map-max-symbols can only be used with --repo-map."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_runs_search_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1") as get_search_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--search", "needle", "--search-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Search:", stdout.getvalue())
        get_search_text.assert_called_once_with(Path(base).resolve(), "needle", "src")
        create_chat_client.assert_not_called()

    def test_main_runs_search_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1") as get_search_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--search",
                        "needle.+",
                        "--search-path",
                        "src",
                        "--search-max-matches",
                        "5",
                        "--search-regex",
                        "--search-ignore-case",
                        "--search-context-lines",
                        "1",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Search:", stdout.getvalue())
        get_search_text.assert_called_once_with(
            Path(base).resolve(),
            "needle.+",
            "src",
            max_matches=5,
            regex=True,
            case_sensitive=False,
            context_lines=1,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_search_contexts_local_flag_without_creating_client(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1") as get_search_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base, "--search-contexts", "needle", "--search-path", "src"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Search contexts:", stdout.getvalue())
        get_search_contexts_text.assert_called_once_with(Path(base).resolve(), "needle", "src")
        create_chat_client.assert_not_called()

    def test_main_runs_search_contexts_local_flag_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1") as get_search_contexts_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--search-contexts",
                        "needle.+",
                        "--search-path",
                        "src",
                        "--search-max-matches",
                        "4",
                        "--search-regex",
                        "--search-ignore-case",
                        "--search-context-lines",
                        "2",
                        "--search-context-max-bytes",
                        "1000",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Search contexts:", stdout.getvalue())
        get_search_contexts_text.assert_called_once_with(
            Path(base).resolve(),
            "needle.+",
            "src",
            max_matches=4,
            regex=True,
            case_sensitive=False,
            context_lines=2,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_find_files_local_flag_with_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()

            with (
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_find_files_text", return_value="Find Files:\n  matches: 1/1") as get_find_files_text,
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "--cwd",
                        base,
                        "--find-files",
                        "app.+",
                        "--find-files-path",
                        "src",
                        "--find-files-max-matches",
                        "5",
                        "--find-files-regex",
                        "--find-files-case-sensitive",
                        "--find-files-include-dirs",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Find Files:", stdout.getvalue())
        get_find_files_text.assert_called_once_with(
            Path(base).resolve(),
            "app.+",
            path="src",
            max_matches=5,
            regex=True,
            case_sensitive=True,
            include_dirs=True,
        )
        create_chat_client.assert_not_called()

    def test_main_runs_project_orientation_local_flags_as_json_without_creating_client(self) -> None:
        cases = [
            (
                ["--overview", "--overview-max-files", "7"],
                "vibeagent.cli.get_overview_report",
                "vibeagent.cli.format_overview_report_text",
                "overview",
                (Path,),
                {"max_files": 7},
            ),
            (
                ["--repo-map", "src", "--repo-map-max-depth", "2"],
                "vibeagent.cli.get_repo_map_report",
                "vibeagent.cli.format_repo_map_report_text",
                "repoMap",
                (Path, "src"),
                {"max_depth": 2},
            ),
            (
                ["--search", "needle", "--search-path", "src", "--search-max-matches", "5"],
                "vibeagent.cli.get_search_report",
                "vibeagent.cli.format_search_report_text",
                "search",
                (Path, "needle", "src"),
                {"max_matches": 5},
            ),
            (
                ["--search-contexts", "needle", "--search-path", "src", "--search-context-max-bytes", "1000"],
                "vibeagent.cli.get_search_contexts_report",
                "vibeagent.cli.format_search_contexts_report_text",
                "searchContexts",
                (Path, "needle", "src"),
                {"max_bytes_per_context": 1000},
            ),
            (
                ["--find-files", "app", "--find-files-path", "src", "--find-files-include-dirs"],
                "vibeagent.cli.get_find_files_report",
                "vibeagent.cli.format_find_files_report_text",
                "findFiles",
                (Path, "app"),
                {"path": "src", "include_dirs": True},
            ),
        ]
        for argv_tail, getter_target, formatter_target, payload_key, expected_args, expected_kwargs in cases:
            with self.subTest(payload_key=payload_key), tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
                stdout = io.StringIO()
                report = {"ok": True, "message": payload_key}
                rendered = f"{payload_key}: ok"

                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    patch(getter_target, return_value=report) as getter,
                    patch(formatter_target, return_value=rendered) as formatter,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(["--json", "--cwd", base, *argv_tail])

                payload = json.loads(stdout.getvalue())
                resolved_args = tuple(Path(base).resolve() if item is Path else item for item in expected_args)
                self.assertEqual(exit_code, 0)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["status"], "completed")
                self.assertEqual(payload["text"], rendered)
                self.assertEqual(payload[payload_key], report)
                getter.assert_called_once_with(*resolved_args, **expected_kwargs)
                formatter.assert_called_once_with(report)
                create_chat_client.assert_not_called()

    def test_main_rejects_search_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--search-max-matches", "5"], "--search-max-matches can only be used with --search or --search-contexts."),
            (["--search-regex"], "--search-regex can only be used with --search or --search-contexts."),
            (["--search-ignore-case"], "--search-ignore-case can only be used with --search or --search-contexts."),
            (["--search-context-lines", "2"], "--search-context-lines can only be used with --search or --search-contexts."),
            (["--search-context-max-bytes", "1000"], "--search-context-max-bytes can only be used with --search-contexts."),
            (["--search", "needle", "--search-context-max-bytes", "1000"], "--search-context-max-bytes can only be used with --search-contexts."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()

    def test_main_rejects_find_files_options_without_matching_local_flag(self) -> None:
        cases = [
            (["--find-files-path", "src"], "--find-files-path can only be used with --find-files."),
            (["--find-files-max-matches", "5"], "--find-files-max-matches can only be used with --find-files."),
            (["--find-files-regex"], "--find-files-regex can only be used with --find-files."),
            (["--find-files-case-sensitive"], "--find-files-case-sensitive can only be used with --find-files."),
            (["--find-files-include-dirs"], "--find-files-include-dirs can only be used with --find-files."),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                stdout = io.StringIO()
                with (
                    patch("vibeagent.cli.create_chat_client") as create_chat_client,
                    redirect_stdout(stdout),
                ):
                    exit_code = main(argv)

                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), f"{expected}\n")
                create_chat_client.assert_not_called()
