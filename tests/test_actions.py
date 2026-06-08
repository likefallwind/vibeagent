import tempfile
import time
import unittest
import subprocess
from pathlib import Path

from vibeagent.actions import AGENT_TOOL_DEFINITIONS, ActionParseError, execute_action, parse_tool_action, run_command
from vibeagent.types import (
    CheckPatchAction,
    CheckPatchesAction,
    DeleteFileAction,
    EditFileAction,
    EditOperation,
    FileInfoAction,
    GlobAction,
    GitBlameAction,
    GitChangesAction,
    GitDiffAction,
    GitLogAction,
    GitShowAction,
    GitStatusAction,
    InsertLinesAction,
    ListFilesAction,
    ListProcessesAction,
    ListTreeAction,
    MoveFileAction,
    MultiEditAction,
    PatchFileAction,
    PatchFilesAction,
    PythonCallGraphAction,
    PythonCallsAction,
    PythonCheckAction,
    PythonDependenciesAction,
    PythonDefinitionsAction,
    PythonReferencesAction,
    ReplacePythonDefinitionAction,
    PythonSymbolsAction,
    ReadFileAction,
    ReadFileRangeItem,
    ReadFileRangesAction,
    ReadFilesAction,
    ReadProcessAction,
    ReplaceLinesAction,
    ReviewChangesAction,
    RepoMapAction,
    RunCommandAction,
    SearchAction,
    SessionSummaryAction,
    StartCommandAction,
    StopProcessAction,
    SuggestChecksAction,
    WriteFileItem,
    WriteFilesAction,
)
from vibeagent.workspace import create_run_workspace, write_run_file


class ActionTests(unittest.TestCase):
    def test_parse_tool_action_accepts_project_actions(self) -> None:
        cases = [
            ("list_files", {"path": "src"}, "list_files"),
            ("list_tree", {"path": "src", "max_depth": 2, "max_entries": 50}, "list_tree"),
            ("repo_map", {"path": "src", "max_depth": 2, "max_files": 20, "max_symbols": 50}, "repo_map"),
            ("read_file", {"path": "src/app.py"}, "read_file"),
            ("read_file", {"path": "src/app.py", "start_line": 3, "line_count": 5}, "read_file"),
            ("read_files", {"paths": ["src/app.py", "tests/test_app.py"]}, "read_files"),
            (
                "read_file_ranges",
                {"ranges": [{"path": "src/app.py", "start_line": 3, "line_count": 5}]},
                "read_file_ranges",
            ),
            ("file_info", {"paths": ["src/app.py", "assets/logo.png"]}, "file_info"),
            ("python_symbols", {"paths": ["src/app.py", "tests/test_app.py"]}, "python_symbols"),
            ("python_check", {"path": "src", "max_files": 10}, "python_check"),
            ("python_dependencies", {"path": "src", "max_files": 10, "max_imports": 50}, "python_dependencies"),
            ("python_definitions", {"symbol": "run_agent", "path": "src", "max_matches": 10, "max_lines": 50}, "python_definitions"),
            (
                "replace_python_definition",
                {"symbol": "run_agent", "path": "src", "content": "def run_agent(task):\n    return task\n"},
                "replace_python_definition",
            ),
            ("python_calls", {"symbol": "run_agent", "path": "src", "max_matches": 50}, "python_calls"),
            ("python_call_graph", {"path": "src", "max_files": 10, "max_edges": 50}, "python_call_graph"),
            ("python_references", {"symbol": "run_agent", "path": "src", "max_matches": 50}, "python_references"),
            ("search", {"query": "needle"}, "search"),
            (
                "search",
                {
                    "query": "needle",
                    "path": "src",
                    "regex": True,
                    "case_sensitive": False,
                    "max_matches": 10,
                    "context_lines": 2,
                },
                "search",
            ),
            ("glob", {"pattern": "**/*.py", "max_matches": 10}, "glob"),
            ("git_status", {}, "git_status"),
            ("git_changes", {}, "git_changes"),
            ("review_changes", {"max_files": 10}, "review_changes"),
            ("suggest_checks", {"max_commands": 10}, "suggest_checks"),
            ("git_diff", {"path": "src/app.py", "staged": False, "max_output_chars": 2000}, "git_diff"),
            ("git_log", {"path": "src/app.py", "max_count": 3}, "git_log"),
            ("git_show", {"rev": "HEAD", "path": "src/app.py", "max_output_chars": 2000}, "git_show"),
            ("git_blame", {"path": "src/app.py", "start_line": 1, "line_count": 5, "max_output_chars": 2000}, "git_blame"),
            ("session_summary", {"run_id": "run-1", "recent_limit": 3}, "session_summary"),
            ("edit_file", {"path": "src/app.py", "old": "a", "new": "b"}, "edit_file"),
            (
                "multi_edit_file",
                {"path": "src/app.py", "edits": [{"old": "a", "new": "b"}, {"old": "c", "new": "d"}]},
                "multi_edit_file",
            ),
            ("replace_lines", {"path": "src/app.py", "start_line": 2, "end_line": 3, "content": "new\n"}, "replace_lines"),
            ("insert_lines", {"path": "src/app.py", "line": 2, "content": "new\n"}, "insert_lines"),
            ("patch_file", {"path": "src/app.py", "patch": "@@ -1 +1 @@\n-old\n+new\n"}, "patch_file"),
            ("check_patch", {"path": "src/app.py", "patch": "@@ -1 +1 @@\n-old\n+new\n"}, "check_patch"),
            ("check_patches", {"patch": "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"}, "check_patches"),
            ("patch_files", {"patch": "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n"}, "patch_files"),
            ("delete_file", {"path": "src/old.py"}, "delete_file"),
            ("move_file", {"source": "src/old.py", "destination": "src/new.py"}, "move_file"),
            ("write_files", {"files": [{"path": "a.py", "content": "a\n"}, {"path": "b.py", "content": "b\n"}]}, "write_files"),
            (
                "run_command",
                {"command": "python3 test.py", "timeout_ms": 120000, "cwd": "pkg", "max_output_chars": 2000},
                "run_command",
            ),
            ("start_command", {"command": "python3 -m http.server 8000", "cwd": "web"}, "start_command"),
            ("read_process", {"process_id": "abc123"}, "read_process"),
            ("list_processes", {}, "list_processes"),
            ("stop_process", {"process_id": "abc123"}, "stop_process"),
            ("update_plan", {"plan": [{"step": "Inspect files", "status": "in_progress"}]}, "update_plan"),
        ]

        for name, tool_input, expected_type in cases:
            parsed = parse_tool_action(name, tool_input)
            self.assertEqual(parsed.type, expected_type)

    def test_parse_tool_action_rejects_unsupported_action(self) -> None:
        with self.assertRaisesRegex(ActionParseError, "Unsupported action type"):
            parse_tool_action("delete_everything", {})

    def test_parse_tool_action_validates_tool_inputs(self) -> None:
        action = parse_tool_action("write_file", {"path": "app.py", "content": "print('ok')\n"})

        self.assertEqual(action.type, "write_file")
        self.assertEqual(action.path, "app.py")

        with self.assertRaisesRegex(ActionParseError, "read_file action requires a string path"):
            parse_tool_action("read_file", {})

        with self.assertRaisesRegex(ActionParseError, "list_tree action path must be a string"):
            parse_tool_action("list_tree", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_depth must be at most 10"):
            parse_tool_action("list_tree", {"max_depth": 11})

        with self.assertRaisesRegex(ActionParseError, "max_entries must be at most 1000"):
            parse_tool_action("list_tree", {"max_entries": 1001})

        with self.assertRaisesRegex(ActionParseError, "repo_map action path must be a string"):
            parse_tool_action("repo_map", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_files must be at most 500"):
            parse_tool_action("repo_map", {"max_files": 501})

        with self.assertRaisesRegex(ActionParseError, "max_symbols must be at most 500"):
            parse_tool_action("repo_map", {"max_symbols": 501})

        with self.assertRaisesRegex(ActionParseError, "line_count requires start_line"):
            parse_tool_action("read_file", {"path": "app.py", "line_count": 5})

        with self.assertRaisesRegex(ActionParseError, "start_line must be a positive integer"):
            parse_tool_action("read_file", {"path": "app.py", "start_line": True})

        with self.assertRaisesRegex(ActionParseError, "tool input must be an object"):
            parse_tool_action("read_file", "bad")

        with self.assertRaisesRegex(ActionParseError, "write_files action requires a non-empty files list"):
            parse_tool_action("write_files", {"files": []})

        with self.assertRaisesRegex(ActionParseError, "write_files file 1 requires string content"):
            parse_tool_action("write_files", {"files": [{"path": "app.py", "content": 1}]})

        with self.assertRaisesRegex(ActionParseError, "duplicates path"):
            parse_tool_action(
                "write_files",
                {"files": [{"path": "app.py", "content": "a"}, {"path": "app.py", "content": "b"}]},
            )

        with self.assertRaisesRegex(ActionParseError, "non-empty paths list"):
            parse_tool_action("read_files", {"paths": []})

        with self.assertRaisesRegex(ActionParseError, "at most 20"):
            parse_tool_action("read_files", {"paths": [f"{index}.py" for index in range(21)]})

        with self.assertRaisesRegex(ActionParseError, "path 1 must be a non-empty string"):
            parse_tool_action("read_files", {"paths": [""]})

        with self.assertRaisesRegex(ActionParseError, "read_file_ranges action requires a non-empty ranges list"):
            parse_tool_action("read_file_ranges", {"ranges": []})

        with self.assertRaisesRegex(ActionParseError, "read_file_ranges range 1 requires a non-empty path"):
            parse_tool_action("read_file_ranges", {"ranges": [{"path": "", "start_line": 1}]})

        with self.assertRaisesRegex(ActionParseError, "read_file_ranges range 1 requires start_line"):
            parse_tool_action("read_file_ranges", {"ranges": [{"path": "app.py"}]})

        with self.assertRaisesRegex(ActionParseError, "read_file_ranges range 1 line_count must be at most 1000"):
            parse_tool_action("read_file_ranges", {"ranges": [{"path": "app.py", "start_line": 1, "line_count": 1001}]})

        with self.assertRaisesRegex(ActionParseError, "file_info action requires a non-empty paths list"):
            parse_tool_action("file_info", {"paths": []})

        with self.assertRaisesRegex(ActionParseError, "file_info action paths must contain at most 50"):
            parse_tool_action("file_info", {"paths": [f"{index}.py" for index in range(51)]})

        with self.assertRaisesRegex(ActionParseError, "python_symbols action paths must contain at most 20"):
            parse_tool_action("python_symbols", {"paths": [f"{index}.py" for index in range(21)]})

        with self.assertRaisesRegex(ActionParseError, "python_check action path must be a string"):
            parse_tool_action("python_check", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_files must be at most 500"):
            parse_tool_action("python_check", {"max_files": 501})

        with self.assertRaisesRegex(ActionParseError, "python_dependencies action path must be a string"):
            parse_tool_action("python_dependencies", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_imports must be at most 2000"):
            parse_tool_action("python_dependencies", {"max_imports": 2001})

        with self.assertRaisesRegex(ActionParseError, "python_definitions action requires a non-empty symbol"):
            parse_tool_action("python_definitions", {"symbol": ""})

        with self.assertRaisesRegex(ActionParseError, "python_definitions action path must be a string"):
            parse_tool_action("python_definitions", {"symbol": "run_agent", "path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_lines must be at most 1000"):
            parse_tool_action("python_definitions", {"symbol": "run_agent", "max_lines": 1001})

        with self.assertRaisesRegex(ActionParseError, "replace_python_definition action requires a non-empty symbol"):
            parse_tool_action("replace_python_definition", {"symbol": "", "content": "def run_agent():\n    pass\n"})

        with self.assertRaisesRegex(ActionParseError, "replace_python_definition action requires non-empty string content"):
            parse_tool_action("replace_python_definition", {"symbol": "run_agent", "content": ""})

        with self.assertRaisesRegex(ActionParseError, "replace_python_definition action path must be a string"):
            parse_tool_action("replace_python_definition", {"symbol": "run_agent", "content": "def run_agent():\n    pass\n", "path": 1})

        with self.assertRaisesRegex(ActionParseError, "python_calls action requires a non-empty symbol"):
            parse_tool_action("python_calls", {"symbol": ""})

        with self.assertRaisesRegex(ActionParseError, "python_calls action path must be a string"):
            parse_tool_action("python_calls", {"symbol": "run_agent", "path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_matches must be at most 500"):
            parse_tool_action("python_calls", {"symbol": "run_agent", "max_matches": 501})

        with self.assertRaisesRegex(ActionParseError, "python_call_graph action path must be a string"):
            parse_tool_action("python_call_graph", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_files must be at most 500"):
            parse_tool_action("python_call_graph", {"max_files": 501})

        with self.assertRaisesRegex(ActionParseError, "max_edges must be at most 2000"):
            parse_tool_action("python_call_graph", {"max_edges": 2001})

        with self.assertRaisesRegex(ActionParseError, "python_references action requires a non-empty symbol"):
            parse_tool_action("python_references", {"symbol": ""})

        with self.assertRaisesRegex(ActionParseError, "python_references action path must be a string"):
            parse_tool_action("python_references", {"symbol": "run_agent", "path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_matches must be at most 500"):
            parse_tool_action("python_references", {"symbol": "run_agent", "max_matches": 501})

        with self.assertRaisesRegex(ActionParseError, "patch_file action requires string patch"):
            parse_tool_action("patch_file", {"path": "app.py"})

        with self.assertRaisesRegex(ActionParseError, "check_patch action requires a string path"):
            parse_tool_action("check_patch", {"patch": "@@ -1 +1 @@\n-a\n+b\n"})

        with self.assertRaisesRegex(ActionParseError, "check_patch action requires string patch"):
            parse_tool_action("check_patch", {"path": "app.py"})

        with self.assertRaisesRegex(ActionParseError, "check_patches action requires string patch"):
            parse_tool_action("check_patches", {})

        with self.assertRaisesRegex(ActionParseError, "multi_edit_file action requires a non-empty edits list"):
            parse_tool_action("multi_edit_file", {"path": "app.py", "edits": []})

        with self.assertRaisesRegex(ActionParseError, "edit 1 requires non-empty string old"):
            parse_tool_action("multi_edit_file", {"path": "app.py", "edits": [{"old": "", "new": "b"}]})

        with self.assertRaisesRegex(ActionParseError, "edit 1 requires string new"):
            parse_tool_action("multi_edit_file", {"path": "app.py", "edits": [{"old": "a"}]})

        with self.assertRaisesRegex(ActionParseError, "replace_lines action requires start_line"):
            parse_tool_action("replace_lines", {"path": "app.py", "end_line": 2, "content": "new\n"})

        with self.assertRaisesRegex(ActionParseError, "end_line must be greater"):
            parse_tool_action("replace_lines", {"path": "app.py", "start_line": 3, "end_line": 2, "content": "new\n"})

        with self.assertRaisesRegex(ActionParseError, "replace_lines action requires string content"):
            parse_tool_action("replace_lines", {"path": "app.py", "start_line": 1, "end_line": 1, "content": 1})

        with self.assertRaisesRegex(ActionParseError, "insert_lines action requires line"):
            parse_tool_action("insert_lines", {"path": "app.py", "content": "new\n"})

        with self.assertRaisesRegex(ActionParseError, "insert_lines action requires non-empty string content"):
            parse_tool_action("insert_lines", {"path": "app.py", "line": 1, "content": ""})

        with self.assertRaisesRegex(ActionParseError, "patch_files action requires string patch"):
            parse_tool_action("patch_files", {})

        with self.assertRaisesRegex(ActionParseError, "delete_file action requires a string path"):
            parse_tool_action("delete_file", {})

        with self.assertRaisesRegex(ActionParseError, "move_file action requires string destination"):
            parse_tool_action("move_file", {"source": "old.py"})

        with self.assertRaisesRegex(ActionParseError, "git_diff action staged must be a boolean"):
            parse_tool_action("git_diff", {"staged": "false"})

        with self.assertRaisesRegex(ActionParseError, "max_output_chars must be at least 1000"):
            parse_tool_action("git_diff", {"max_output_chars": 999})

        with self.assertRaisesRegex(ActionParseError, "max_output_chars must be at most 50000"):
            parse_tool_action("git_diff", {"max_output_chars": 50001})

        with self.assertRaisesRegex(ActionParseError, "git_log action path must be a string"):
            parse_tool_action("git_log", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_count must be at most 50"):
            parse_tool_action("git_log", {"max_count": 51})

        with self.assertRaisesRegex(ActionParseError, "git_show action rev must be a non-empty string"):
            parse_tool_action("git_show", {"rev": ""})

        with self.assertRaisesRegex(ActionParseError, "git_show action path must be a string"):
            parse_tool_action("git_show", {"path": 1})

        with self.assertRaisesRegex(ActionParseError, "max_output_chars must be at least 1000"):
            parse_tool_action("git_show", {"max_output_chars": 999})

        with self.assertRaisesRegex(ActionParseError, "git_blame action path must be a non-empty string"):
            parse_tool_action("git_blame", {"path": ""})

        with self.assertRaisesRegex(ActionParseError, "line_count must be at most 1000"):
            parse_tool_action("git_blame", {"path": "app.py", "line_count": 1001})

        with self.assertRaisesRegex(ActionParseError, "max_output_chars must be at least 1000"):
            parse_tool_action("git_blame", {"path": "app.py", "max_output_chars": 999})

        with self.assertRaisesRegex(ActionParseError, "session_summary action run_id must be a string"):
            parse_tool_action("session_summary", {"run_id": 1})

        with self.assertRaisesRegex(ActionParseError, "recent_limit must be at most 20"):
            parse_tool_action("session_summary", {"recent_limit": 21})

        with self.assertRaisesRegex(ActionParseError, "search action regex must be a boolean"):
            parse_tool_action("search", {"query": "needle", "regex": "true"})

        with self.assertRaisesRegex(ActionParseError, "max_matches must be at most 500"):
            parse_tool_action("search", {"query": "needle", "max_matches": 501})

        with self.assertRaisesRegex(ActionParseError, "context_lines must be at most 5"):
            parse_tool_action("search", {"query": "needle", "context_lines": 6})

        with self.assertRaisesRegex(ActionParseError, "context_lines must be a non-negative integer"):
            parse_tool_action("search", {"query": "needle", "context_lines": -1})

        with self.assertRaisesRegex(ActionParseError, "glob action requires a non-empty pattern"):
            parse_tool_action("glob", {"pattern": ""})

        with self.assertRaisesRegex(ActionParseError, "max_matches must be at most 500"):
            parse_tool_action("glob", {"pattern": "**/*.py", "max_matches": 501})

        with self.assertRaisesRegex(ActionParseError, "timeout_ms must be at least 100"):
            parse_tool_action("run_command", {"command": "python3 test.py", "timeout_ms": 99})

        with self.assertRaisesRegex(ActionParseError, "timeout_ms must be at most 600000"):
            parse_tool_action("run_command", {"command": "python3 test.py", "timeout_ms": 600001})

        with self.assertRaisesRegex(ActionParseError, "run_command action cwd must be a string"):
            parse_tool_action("run_command", {"command": "python3 test.py", "cwd": 1})

        with self.assertRaisesRegex(ActionParseError, "max_output_chars must be at least 1000"):
            parse_tool_action("run_command", {"command": "python3 test.py", "max_output_chars": 999})

        with self.assertRaisesRegex(ActionParseError, "max_output_chars must be at most 50000"):
            parse_tool_action("run_command", {"command": "python3 test.py", "max_output_chars": 50001})

        with self.assertRaisesRegex(ActionParseError, "max_files must be at most 500"):
            parse_tool_action("review_changes", {"max_files": 501})

        with self.assertRaisesRegex(ActionParseError, "max_commands must be at most 100"):
            parse_tool_action("suggest_checks", {"max_commands": 101})

        with self.assertRaisesRegex(ActionParseError, "start_command action requires a non-empty command"):
            parse_tool_action("start_command", {"command": ""})

        with self.assertRaisesRegex(ActionParseError, "start_command action cwd must be a string"):
            parse_tool_action("start_command", {"command": "python3 -m http.server", "cwd": 1})

        with self.assertRaisesRegex(ActionParseError, "read_process action requires a non-empty process_id"):
            parse_tool_action("read_process", {})

        with self.assertRaisesRegex(ActionParseError, "stop_process action requires a non-empty process_id"):
            parse_tool_action("stop_process", {"process_id": ""})

    def test_update_plan_tool_schema_is_exposed(self) -> None:
        names = [tool["name"] for tool in AGENT_TOOL_DEFINITIONS]

        self.assertIn("update_plan", names)
        self.assertIn("read_files", names)
        self.assertIn("read_file_ranges", names)
        self.assertIn("list_tree", names)
        self.assertIn("repo_map", names)
        self.assertIn("file_info", names)
        self.assertIn("python_symbols", names)
        self.assertIn("python_check", names)
        self.assertIn("python_dependencies", names)
        self.assertIn("python_definitions", names)
        self.assertIn("replace_python_definition", names)
        self.assertIn("python_calls", names)
        self.assertIn("python_call_graph", names)
        self.assertIn("python_references", names)
        self.assertIn("glob", names)
        self.assertIn("check_patch", names)
        self.assertIn("check_patches", names)
        self.assertIn("replace_lines", names)
        self.assertIn("insert_lines", names)
        self.assertIn("git_changes", names)
        self.assertIn("review_changes", names)
        self.assertIn("suggest_checks", names)
        self.assertIn("git_show", names)
        self.assertIn("git_blame", names)
        self.assertIn("write_files", names)
        self.assertIn("session_summary", names)
        self.assertIn("start_command", names)
        self.assertIn("read_process", names)
        self.assertIn("list_processes", names)
        self.assertIn("stop_process", names)

    def test_parse_tool_action_validates_update_plan_items(self) -> None:
        action = parse_tool_action(
            "update_plan",
            {
                "explanation": "Starting work",
                "plan": [
                    {"step": "Inspect files", "status": "completed"},
                    {"step": "Implement change", "status": "in_progress"},
                    {"step": "Run tests", "status": "pending"},
                ],
            },
        )

        self.assertEqual(action.type, "update_plan")
        self.assertEqual(action.plan[1].step, "Implement change")
        self.assertEqual(action.plan[1].status, "in_progress")

        with self.assertRaisesRegex(ActionParseError, "non-empty plan list"):
            parse_tool_action("update_plan", {"plan": []})

        with self.assertRaisesRegex(ActionParseError, "at most one in_progress"):
            parse_tool_action(
                "update_plan",
                {
                    "plan": [
                        {"step": "A", "status": "in_progress"},
                        {"step": "B", "status": "in_progress"},
                    ]
                },
            )

    def test_run_command_captures_stdout_stderr_exit_code_and_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-") as cwd:
            result = run_command(
                Path(cwd),
                "python3 -c \"import sys; print('out'); print('err', file=sys.stderr)\"",
            )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), "out")
        self.assertEqual(result.stderr.strip(), "err")
        self.assertFalse(result.timed_out)

    def test_run_command_reports_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-timeout-") as cwd:
            result = run_command(Path(cwd), "python3 -c \"import time; time.sleep(1)\"", 50)

        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.signal)
        self.assertEqual(result.timeout_ms, 50)

    def test_run_command_truncates_large_output_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-command-") as cwd:
            result = run_command(
                Path(cwd),
                "python3 -c \"print('A' * 1500); print('B' * 1500)\"",
                max_output_chars=1000,
            )

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout_truncated)
        self.assertFalse(result.stderr_truncated)
        self.assertEqual(result.max_output_chars, 1000)
        self.assertLessEqual(len(result.stdout), 1000)
        self.assertIn("[truncated to 1000 chars", result.stdout)

    def test_execute_run_command_uses_action_timeout_when_provided(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")

            observation = execute_action(
                workspace,
                RunCommandAction(
                    type="run_command",
                    command="python3 -c \"import time; time.sleep(0.2); print('done')\"",
                    timeout_ms=500,
                ),
                command_timeout_ms=100,
            )

        self.assertEqual(observation.kind, "run_command")
        self.assertFalse(observation.result.timed_out)
        self.assertEqual(observation.result.timeout_ms, 500)
        self.assertEqual(observation.result.stdout.strip(), "done")

    def test_execute_run_command_uses_project_relative_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/app.py", "print('ok')\n")

            observation = execute_action(
                workspace,
                RunCommandAction(type="run_command", command="pwd", cwd="pkg"),
            )
            invalid = execute_action(
                workspace,
                RunCommandAction(type="run_command", command="pwd", cwd="../outside"),
            )

        self.assertEqual(observation.kind, "run_command")
        self.assertEqual(observation.result.cwd, "pkg")
        self.assertEqual(observation.result.stdout.strip(), str(Path(base, "pkg").resolve()))
        self.assertEqual(invalid.kind, "run_command")
        self.assertIsNone(invalid.result.exit_code)
        self.assertIn("escapes", invalid.result.stderr)

    def test_execute_project_actions_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "value = 'old'\nprint(value)\n")
            write_run_file(workspace, "module.py", "def add(a, b):\n    return a + b\n")
            write_run_file(workspace, "config.py", "debug = False\n")
            write_run_file(workspace, "obsolete.py", "print('remove')\n")
            write_run_file(workspace, "old_name.py", "print('move')\n")

            listed = execute_action(workspace, ListFilesAction(type="list_files"))
            tree = execute_action(workspace, ListTreeAction(type="list_tree", max_depth=2, max_entries=3))
            repo_map = execute_action(workspace, RepoMapAction(type="repo_map", max_depth=2, max_files=5))
            read = execute_action(workspace, ReadFileAction(type="read_file", path="app.py"))
            read_range = execute_action(workspace, ReadFileAction(type="read_file", path="app.py", start_line=2, line_count=1))
            read_files = execute_action(workspace, ReadFilesAction(type="read_files", paths=["app.py", "config.py"]))
            read_ranges = execute_action(
                workspace,
                ReadFileRangesAction(
                    type="read_file_ranges",
                    ranges=[
                        ReadFileRangeItem(path="app.py", start_line=1, line_count=1),
                        ReadFileRangeItem(path="module.py", start_line=2, line_count=1),
                    ],
                ),
            )
            Path(base, "binary.bin").write_bytes(b"\x00\x01\x02")
            Path(base, "pkg").mkdir()
            file_info = execute_action(
                workspace,
                FileInfoAction(type="file_info", paths=["app.py", "binary.bin", "pkg", "missing.py"]),
            )
            symbols = execute_action(workspace, PythonSymbolsAction(type="python_symbols", paths=["module.py", "missing.py"]))
            syntax = execute_action(workspace, PythonCheckAction(type="python_check"))
            references = execute_action(
                workspace,
                PythonReferencesAction(type="python_references", symbol="add", path="module.py"),
            )
            searched = execute_action(workspace, SearchAction(type="search", query="print"))
            globbed = execute_action(workspace, GlobAction(type="glob", pattern="*.py"))
            edited = execute_action(workspace, EditFileAction(type="edit_file", path="app.py", old="old", new="new"))
            multi_edited = execute_action(
                workspace,
                MultiEditAction(
                    type="multi_edit_file",
                    path="app.py",
                    edits=[
                        EditOperation(old="new", new="multi-new"),
                        EditOperation(old="print(value)", new="print(value.upper())"),
                    ],
                ),
            )
            line_replaced = execute_action(
                workspace,
                ReplaceLinesAction(
                    type="replace_lines",
                    path="app.py",
                    start_line=1,
                    end_line=1,
                    content="value = 'line'\n",
                ),
            )
            line_inserted = execute_action(
                workspace,
                InsertLinesAction(
                    type="insert_lines",
                    path="app.py",
                    line=2,
                    content="value = value\n",
                ),
            )
            checked = execute_action(
                workspace,
                CheckPatchAction(
                    type="check_patch",
                    path="app.py",
                    patch="@@ -1,3 +1,3 @@\n-value = 'line'\n+value = 'checked'\n value = value\n print(value.upper())\n",
                ),
            )
            patched = execute_action(
                workspace,
                PatchFileAction(
                    type="patch_file",
                    path="app.py",
                    patch="@@ -1,3 +1,3 @@\n-value = 'line'\n+value = 'patched'\n value = value\n print(value.upper())\n",
                ),
            )
            patched_files = execute_action(
                workspace,
                PatchFilesAction(
                    type="patch_files",
                    patch=(
                        "--- a/app.py\n"
                        "+++ b/app.py\n"
                        "@@ -1,3 +1,3 @@\n"
                        "-value = 'patched'\n"
                        "+value = 'multi'\n"
                        " value = value\n"
                        " print(value.upper())\n"
                        "--- a/config.py\n"
                        "+++ b/config.py\n"
                        "@@ -1 +1 @@\n"
                        "-debug = False\n"
                        "+debug = True\n"
                    ),
                ),
            )
            deleted = execute_action(workspace, DeleteFileAction(type="delete_file", path="obsolete.py"))
            moved = execute_action(
                workspace,
                MoveFileAction(type="move_file", source="old_name.py", destination="pkg/new_name.py"),
            )
            wrote_files = execute_action(
                workspace,
                WriteFilesAction(
                    type="write_files",
                    files=[
                        WriteFileItem(path="pkg/a.py", content="A = 1\n"),
                        WriteFileItem(path="pkg/b.py", content="B = 2\n"),
                    ],
                ),
            )
            rejected_write_files = execute_action(
                workspace,
                WriteFilesAction(
                    type="write_files",
                    files=[
                        WriteFileItem(path="pkg/c.py", content="C = 3\n"),
                        WriteFileItem(path=".vibeagent/secret.py", content="SECRET = True\n"),
                    ],
                ),
            )

            self.assertEqual(listed.kind, "list_files")
            self.assertEqual(tree.kind, "list_tree")
            self.assertTrue(tree.ok)
            self.assertTrue(tree.truncated)
            self.assertEqual(tree.max_depth, 2)
            self.assertEqual(tree.entries, ["app.py", "config.py", "module.py"])
            self.assertEqual(repo_map.kind, "repo_map")
            self.assertTrue(repo_map.ok)
            self.assertIn("module.py", repo_map.files)
            self.assertEqual(repo_map.python_files[0].path, "app.py")
            self.assertEqual(read.kind, "read_file")
            self.assertEqual(read_range.kind, "read_file")
            self.assertEqual(read_range.content, "2: print(value)")
            self.assertEqual(read_files.kind, "read_files")
            self.assertEqual([item.path for item in read_files.files], ["app.py", "config.py"])
            self.assertTrue(all(item.ok for item in read_files.files))
            self.assertEqual(read_ranges.kind, "read_file_ranges")
            self.assertTrue(all(item.ok for item in read_ranges.ranges))
            self.assertEqual([item.content for item in read_ranges.ranges], ["1: value = 'old'", "2:     return a + b"])
            self.assertEqual(file_info.kind, "file_info")
            self.assertEqual([item.path for item in file_info.files], ["app.py", "binary.bin", "pkg", "missing.py"])
            self.assertTrue(file_info.files[0].is_file)
            self.assertEqual(file_info.files[0].line_count, 2)
            self.assertFalse(file_info.files[0].is_binary)
            self.assertTrue(file_info.files[1].is_binary)
            self.assertTrue(file_info.files[2].is_dir)
            self.assertFalse(file_info.files[3].ok)
            self.assertEqual(symbols.kind, "python_symbols")
            self.assertTrue(symbols.files[0].ok)
            self.assertEqual(symbols.files[0].symbols[0].name, "add")
            self.assertFalse(symbols.files[1].ok)
            self.assertEqual(syntax.kind, "python_check")
            self.assertTrue(syntax.ok)
            self.assertGreaterEqual(syntax.total, 5)
            self.assertEqual(references.kind, "python_references")
            self.assertTrue(references.ok)
            self.assertEqual([(item.path, item.line, item.kind) for item in references.references], [("module.py", 1, "definition")])
            self.assertEqual(searched.kind, "search")
            self.assertEqual(globbed.kind, "glob")
            self.assertEqual(globbed.matches, ["app.py", "config.py", "module.py", "obsolete.py", "old_name.py"])
            self.assertEqual(edited.kind, "edit_file")
            self.assertEqual(multi_edited.kind, "multi_edit_file")
            self.assertTrue(multi_edited.ok)
            self.assertIn("+print(value.upper())", multi_edited.diff)
            self.assertEqual(line_replaced.kind, "replace_lines")
            self.assertTrue(line_replaced.ok)
            self.assertIn("+value = 'line'", line_replaced.diff)
            self.assertEqual(line_inserted.kind, "insert_lines")
            self.assertTrue(line_inserted.ok)
            self.assertIn("+value = value", line_inserted.diff)
            self.assertEqual(checked.kind, "check_patch")
            self.assertTrue(checked.ok)
            self.assertIn("+value = 'checked'", checked.diff)
            self.assertEqual(patched.kind, "patch_file")
            self.assertTrue(patched.ok)
            self.assertIn("+value = 'patched'", patched.diff)
            self.assertEqual(patched_files.kind, "patch_files")
            self.assertTrue(patched_files.ok)
            self.assertEqual(patched_files.files, ["app.py", "config.py"])
            self.assertEqual(deleted.kind, "delete_file")
            self.assertTrue(deleted.ok)
            self.assertIn("-print('remove')", deleted.diff)
            self.assertEqual(moved.kind, "move_file")
            self.assertTrue(moved.ok)
            self.assertEqual(wrote_files.kind, "write_files")
            self.assertTrue(wrote_files.ok)
            self.assertEqual([item.path for item in wrote_files.files], ["pkg/a.py", "pkg/b.py"])
            self.assertTrue(all(item.ok for item in wrote_files.files))
            self.assertEqual(rejected_write_files.kind, "write_files")
            self.assertFalse(rejected_write_files.ok)
            self.assertIn("Path is protected", rejected_write_files.message)
            self.assertEqual(Path(base, "app.py").read_text(encoding="utf-8"), "value = 'multi'\nvalue = value\nprint(value.upper())\n")
            self.assertEqual(Path(base, "config.py").read_text(encoding="utf-8"), "debug = True\n")
            self.assertFalse(Path(base, "obsolete.py").exists())
            self.assertEqual(Path(base, "pkg", "new_name.py").read_text(encoding="utf-8"), "print('move')\n")
            self.assertEqual(Path(base, "pkg", "a.py").read_text(encoding="utf-8"), "A = 1\n")
            self.assertEqual(Path(base, "pkg", "b.py").read_text(encoding="utf-8"), "B = 2\n")
            self.assertFalse(Path(base, "pkg", "c.py").exists())

    def test_execute_git_actions_read_repository_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('old')\n")
            write_run_file(workspace, "blame.py", "print('blame')\n")
            subprocess.run(["git", "add", "app.py", "blame.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "app.py", f"{'x' * 4000}\nprint('new')\n")

            status = execute_action(workspace, GitStatusAction(type="git_status"))
            changes = execute_action(workspace, GitChangesAction(type="git_changes"))
            diff = execute_action(workspace, GitDiffAction(type="git_diff", path="app.py", max_output_chars=1000))
            log = execute_action(workspace, GitLogAction(type="git_log", path="app.py", max_count=1))
            show = execute_action(workspace, GitShowAction(type="git_show", rev="HEAD", path="app.py", max_output_chars=1000))
            blame = execute_action(
                workspace,
                GitBlameAction(type="git_blame", path="blame.py", start_line=1, line_count=1, max_output_chars=1000),
            )
            invalid_blame = execute_action(workspace, GitBlameAction(type="git_blame", path="../outside.py"))

        self.assertEqual(status.kind, "git_status")
        self.assertTrue(status.ok)
        self.assertIn("M app.py", status.status)
        self.assertEqual(changes.kind, "git_changes")
        self.assertTrue(changes.ok)
        self.assertEqual(changes.files[0].path, "app.py")
        self.assertTrue(changes.files[0].unstaged)
        self.assertEqual(changes.files[0].unstaged_insertions, 2)
        self.assertEqual(changes.files[0].unstaged_deletions, 1)
        self.assertEqual(diff.kind, "git_diff")
        self.assertTrue(diff.ok)
        self.assertIn("+print('new')", diff.diff)
        self.assertTrue(diff.truncated)
        self.assertEqual(diff.max_output_chars, 1000)
        self.assertEqual(log.kind, "git_log")
        self.assertTrue(log.ok)
        self.assertIn("initial", log.log)
        self.assertEqual(show.kind, "git_show")
        self.assertTrue(show.ok)
        self.assertIn("initial", show.output)
        self.assertIn("app.py", show.output)
        self.assertFalse(show.truncated)
        self.assertEqual(blame.kind, "git_blame")
        self.assertTrue(blame.ok)
        self.assertIn("print('blame')", blame.blame)
        self.assertEqual(blame.start_line, 1)
        self.assertEqual(blame.line_count, 1)
        self.assertEqual(invalid_blame.kind, "git_blame")
        self.assertFalse(invalid_blame.ok)
        self.assertIn("escapes", invalid_blame.message)

    def test_execute_review_changes_action_reports_pre_final_checks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "app.py", "print('old')\n")
            subprocess.run(["git", "add", "app.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "app.py", "def broken(: \n")

            observation = execute_action(workspace, ReviewChangesAction(type="review_changes"))
            invalid = execute_action(workspace, ReviewChangesAction(type="review_changes", max_files=501))

        self.assertEqual(observation.kind, "review_changes")
        self.assertFalse(observation.ok)
        self.assertTrue(observation.changes_ok)
        self.assertFalse(observation.diff_check_ok)
        self.assertTrue(observation.staged_diff_check_ok)
        self.assertFalse(observation.python_ok)
        self.assertEqual(observation.total_files, 1)
        self.assertEqual(observation.files[0].path, "app.py")
        self.assertEqual(observation.python_total, 1)
        self.assertFalse(observation.python[0].ok)
        self.assertIn("Python syntax error", observation.python[0].message)
        self.assertIn("app.py", observation.diff_check)
        self.assertEqual(invalid.kind, "review_changes")
        self.assertFalse(invalid.ok)
        self.assertIn("max_files must be at most 500", invalid.message)

    def test_execute_suggest_checks_action_reports_candidate_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(workspace, "package.json", '{"scripts":{"test":"node test.js","dev":"vite"}}')
            write_run_file(workspace, "pkg/__init__.py", "")
            write_run_file(workspace, "tests/test_app.py", "def test_ok():\n    assert True\n")

            observation = execute_action(workspace, SuggestChecksAction(type="suggest_checks"))
            invalid = execute_action(workspace, SuggestChecksAction(type="suggest_checks", max_commands=101))

        self.assertEqual(observation.kind, "suggest_checks")
        self.assertTrue(observation.ok)
        commands = {(item.cwd, item.command) for item in observation.checks}
        self.assertIn((".", "npm run test"), commands)
        self.assertIn((".", "python -m unittest discover -s tests"), commands)
        self.assertIn((".", "python -m compileall -q pkg"), commands)
        self.assertTrue(observation.changed_files)
        self.assertEqual(invalid.kind, "suggest_checks")
        self.assertFalse(invalid.ok)
        self.assertIn("max_commands must be at most 100", invalid.message)

    def test_execute_session_summary_action_reads_compact_summary_without_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "run-1")
            (workspace.session_dir / "events.jsonl").write_text(
                '{"type":"task","task":"Build feature"}\n'
                '{"type":"tool_call","iteration":1,"id":"1","name":"read_file","input":{"path":"SECRET_PATH"}}\n'
                '{"type":"model","iteration":2,"content":[{"type":"text","text":"Done."}]}\n',
                encoding="utf-8",
            )

            observation = execute_action(workspace, SessionSummaryAction(type="session_summary", recent_limit=2))
            invalid = execute_action(workspace, SessionSummaryAction(type="session_summary", run_id="../bad"))

        self.assertEqual(observation.kind, "session_summary")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.run_id, "run-1")
        self.assertIn("Session: run-1", observation.summary)
        self.assertIn("status: completed", observation.summary)
        self.assertIn("Recent sessions:", "\n".join(observation.recent_sessions))
        self.assertNotIn("SECRET_PATH", observation.summary)
        self.assertEqual(invalid.kind, "session_summary")
        self.assertFalse(invalid.ok)
        self.assertIn("Invalid session id", invalid.message)

    def test_execute_search_action_uses_scope_regex_and_case_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "def HandleEvent():\n    return 1\n")
            write_run_file(workspace, "tests/test_app.py", "def test_handle_event():\n    return 2\n")

            observation = execute_action(
                workspace,
                SearchAction(
                    type="search",
                    query=r"handleevent",
                    path="src",
                    regex=False,
                    case_sensitive=False,
                    max_matches=5,
                ),
            )
            contextual = execute_action(
                workspace,
                SearchAction(type="search", query="return 1", path="src/app.py", context_lines=1),
            )
            invalid = execute_action(workspace, SearchAction(type="search", query="(", regex=True))

        self.assertEqual(observation.kind, "search")
        self.assertEqual(observation.path, "src")
        self.assertFalse(observation.case_sensitive)
        self.assertEqual(observation.matches, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(contextual.kind, "search")
        self.assertEqual(contextual.context_lines, 1)
        self.assertEqual(contextual.matches, ["src/app.py:1:  def HandleEvent():\nsrc/app.py:2:>     return 1"])
        self.assertEqual(invalid.kind, "search")
        self.assertIn("Invalid regex", invalid.message)

    def test_execute_python_check_action_reports_syntax_errors_and_invalid_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "def ok():\n    return 1\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            observation = execute_action(workspace, PythonCheckAction(type="python_check", path="src"))
            invalid = execute_action(workspace, PythonCheckAction(type="python_check", path="../outside"))

        self.assertEqual(observation.kind, "python_check")
        self.assertFalse(observation.ok)
        self.assertEqual(observation.total, 2)
        self.assertEqual([(item.path, item.ok) for item in observation.files], [("src/app.py", True), ("src/bad.py", False)])
        self.assertEqual(observation.files[1].line, 1)
        self.assertIn("Python syntax error", observation.files[1].message)
        self.assertEqual(invalid.kind, "python_check")
        self.assertFalse(invalid.ok)
        self.assertIn("escapes", invalid.message)

    def test_execute_python_dependencies_action_reports_local_and_external_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/__init__.py", "")
            write_run_file(workspace, "pkg/util.py", "VALUE = 1\n")
            write_run_file(
                workspace,
                "pkg/app.py",
                "import os\nfrom .util import VALUE\nfrom pathlib import Path\n",
            )

            observation = execute_action(workspace, PythonDependenciesAction(type="python_dependencies", path="pkg"))
            invalid = execute_action(workspace, PythonDependenciesAction(type="python_dependencies", path="../outside"))

        self.assertEqual(observation.kind, "python_dependencies")
        self.assertTrue(observation.ok)
        app = next(file for file in observation.files if file.path == "pkg/app.py")
        self.assertEqual(app.module, "pkg.app")
        self.assertIn("pkg.util", app.local_modules)
        self.assertIn("os", app.external_modules)
        self.assertIn("pathlib", app.external_modules)
        self.assertEqual([(item.target, item.local) for item in app.imports], [("os", False), ("pkg.util", True), ("pathlib", False)])
        self.assertEqual(invalid.kind, "python_dependencies")
        self.assertFalse(invalid.ok)
        self.assertIn("escapes", invalid.message)

    def test_execute_python_definitions_action_returns_source_excerpts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "class Runner:\n"
                    "    def run_agent(self, task):\n"
                    "        return task\n\n"
                    "def run_agent(task):\n"
                    "    return task\n"
                ),
            )

            observation = execute_action(
                workspace,
                PythonDefinitionsAction(type="python_definitions", symbol="run_agent", path="src", max_lines=1),
            )
            invalid = execute_action(workspace, PythonDefinitionsAction(type="python_definitions", symbol="bad-name"))

        self.assertEqual(observation.kind, "python_definitions")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.total, 2)
        self.assertEqual([item.qualified_name for item in observation.definitions], ["Runner.run_agent", "run_agent"])
        self.assertTrue(observation.definitions[0].truncated)
        self.assertIn("2:     def run_agent", observation.definitions[0].content)
        self.assertEqual(invalid.kind, "python_definitions")
        self.assertFalse(invalid.ok)
        self.assertIn("valid identifier", invalid.message)

    def test_execute_replace_python_definition_action_updates_unique_definition(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "class Runner:\n"
                    "    def run_agent(self, task):\n"
                    "        return task\n\n"
                    "def run_agent(task):\n"
                    "    return task\n"
                ),
            )

            observation = execute_action(
                workspace,
                ReplacePythonDefinitionAction(
                    type="replace_python_definition",
                    symbol="Runner.run_agent",
                    path="src/app.py",
                    content="    def run_agent(self, task):\n        return task.upper()\n",
                ),
            )
            invalid = execute_action(
                workspace,
                ReplacePythonDefinitionAction(
                    type="replace_python_definition",
                    symbol="run_agent",
                    path="src/app.py",
                    content="def run_agent(task):\n    return task\n",
                ),
            )
            content = Path(base, "src", "app.py").read_text(encoding="utf-8")

        self.assertEqual(observation.kind, "replace_python_definition")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.definition_path, "src/app.py")
        self.assertEqual(observation.qualified_name, "Runner.run_agent")
        self.assertIn("+        return task.upper()", observation.diff)
        self.assertIn("return task.upper()", content)
        self.assertEqual(invalid.kind, "replace_python_definition")
        self.assertFalse(invalid.ok)
        self.assertIn("ambiguous", invalid.message)

    def test_execute_check_patch_actions_validate_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            single = execute_action(
                workspace,
                CheckPatchAction(
                    type="check_patch",
                    path="app.py",
                    patch="@@ -1 +1 @@\n-name = 'old'\n+name = 'new'\n",
                ),
            )
            multi = execute_action(
                workspace,
                CheckPatchesAction(
                    type="check_patches",
                    patch=(
                        "--- a/app.py\n"
                        "+++ b/app.py\n"
                        "@@ -1 +1 @@\n"
                        "-name = 'old'\n"
                        "+name = 'new'\n"
                        "--- a/config.py\n"
                        "+++ b/config.py\n"
                        "@@ -1 +1 @@\n"
                        "-debug = False\n"
                        "+debug = True\n"
                    ),
                ),
            )
            invalid = execute_action(
                workspace,
                CheckPatchAction(
                    type="check_patch",
                    path="app.py",
                    patch="@@ -1 +1 @@\n-name = 'missing'\n+name = 'new'\n",
                ),
            )
            app = Path(base, "app.py").read_text(encoding="utf-8")
            config = Path(base, "config.py").read_text(encoding="utf-8")

        self.assertEqual(single.kind, "check_patch")
        self.assertTrue(single.ok)
        self.assertIn("+name = 'new'", single.diff)
        self.assertEqual(multi.kind, "check_patches")
        self.assertTrue(multi.ok)
        self.assertEqual(multi.files, ["app.py", "config.py"])
        self.assertIn("+debug = True", multi.diff)
        self.assertEqual(invalid.kind, "check_patch")
        self.assertFalse(invalid.ok)
        self.assertIn("context did not match", invalid.message)
        self.assertEqual(app, "name = 'old'\n")
        self.assertEqual(config, "debug = False\n")

    def test_execute_python_references_action_reports_matches_and_invalid_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                "def run_agent(task):\n    return task\n\nvalue = run_agent('x')\n",
            )

            observation = execute_action(
                workspace,
                PythonReferencesAction(type="python_references", symbol="run_agent", path="src", max_matches=1),
            )
            invalid = execute_action(workspace, PythonReferencesAction(type="python_references", symbol="bad-name"))

        self.assertEqual(observation.kind, "python_references")
        self.assertTrue(observation.ok)
        self.assertTrue(observation.truncated)
        self.assertEqual(observation.total, 2)
        self.assertEqual([(item.path, item.line, item.kind) for item in observation.references], [("src/app.py", 1, "definition")])
        self.assertEqual(invalid.kind, "python_references")
        self.assertFalse(invalid.ok)
        self.assertIn("valid identifier", invalid.message)

    def test_execute_python_calls_action_reports_matches_and_invalid_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "def run_agent(task):\n"
                    "    return task\n\n"
                    "class Runner:\n"
                    "    def call(self):\n"
                    "        return run_agent('x')\n\n"
                    "value = Runner().call()\n"
                ),
            )

            observation = execute_action(
                workspace,
                PythonCallsAction(type="python_calls", symbol="run_agent", path="src", max_matches=1),
            )
            invalid = execute_action(workspace, PythonCallsAction(type="python_calls", symbol="bad-name"))

        self.assertEqual(observation.kind, "python_calls")
        self.assertTrue(observation.ok)
        self.assertFalse(observation.truncated)
        self.assertEqual(observation.total, 1)
        self.assertEqual([(item.path, item.line, item.callee, item.caller) for item in observation.calls], [("src/app.py", 6, "run_agent", "Runner.call")])
        self.assertEqual(invalid.kind, "python_calls")
        self.assertFalse(invalid.ok)
        self.assertIn("valid identifier", invalid.message)

    def test_execute_python_call_graph_action_reports_edges_and_invalid_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "def run_agent(task):\n"
                    "    return task\n\n"
                    "class Runner:\n"
                    "    def call(self):\n"
                    "        return run_agent('x')\n\n"
                    "value = Runner().call()\n"
                ),
            )

            observation = execute_action(
                workspace,
                PythonCallGraphAction(type="python_call_graph", path="src", max_edges=1),
            )
            invalid = execute_action(workspace, PythonCallGraphAction(type="python_call_graph", path="../outside"))

        self.assertEqual(observation.kind, "python_call_graph")
        self.assertTrue(observation.ok)
        self.assertTrue(observation.truncated)
        self.assertEqual(observation.total, 3)
        self.assertEqual([(item.path, item.line, item.callee, item.caller) for item in observation.edges], [("src/app.py", 6, "run_agent", "Runner.call")])
        self.assertEqual(invalid.kind, "python_call_graph")
        self.assertFalse(invalid.ok)
        self.assertIn("escapes", invalid.message)

    def test_execute_glob_action_reports_matches_and_invalid_patterns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "print('app')\n")
            write_run_file(workspace, "tests/test_app.py", "def test_app(): pass\n")

            observation = execute_action(workspace, GlobAction(type="glob", pattern="**/*.py", max_matches=1))
            invalid = execute_action(workspace, GlobAction(type="glob", pattern="../*.py"))

        self.assertEqual(observation.kind, "glob")
        self.assertTrue(observation.ok)
        self.assertTrue(observation.truncated)
        self.assertEqual(observation.matches, ["src/app.py"])
        self.assertEqual(observation.total, 2)
        self.assertEqual(invalid.kind, "glob")
        self.assertFalse(invalid.ok)
        self.assertIn("escapes", invalid.message)

    def test_execute_list_tree_action_reports_entries_and_invalid_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "print('app')\n")
            write_run_file(workspace, "src/pkg/mod.py", "value = 1\n")

            observation = execute_action(
                workspace,
                ListTreeAction(type="list_tree", path="src", max_depth=2, max_entries=2),
            )
            invalid = execute_action(workspace, ListTreeAction(type="list_tree", path="../outside"))

        self.assertEqual(observation.kind, "list_tree")
        self.assertTrue(observation.ok)
        self.assertTrue(observation.truncated)
        self.assertEqual(observation.entries, ["src/app.py", "src/pkg/"])
        self.assertEqual(observation.total, 3)
        self.assertEqual(observation.max_depth, 2)
        self.assertEqual(invalid.kind, "list_tree")
        self.assertFalse(invalid.ok)
        self.assertIn("escapes", invalid.message)

    def test_execute_repo_map_action_reports_overview_and_invalid_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "class App:\n    def run(self):\n        return 1\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "README.md", "# Demo\n")

            observation = execute_action(
                workspace,
                RepoMapAction(type="repo_map", path="src", max_depth=1, max_files=10, max_symbols=10),
            )
            invalid = execute_action(workspace, RepoMapAction(type="repo_map", path="../outside"))

        self.assertEqual(observation.kind, "repo_map")
        self.assertTrue(observation.ok)
        self.assertEqual(observation.path, "src")
        self.assertEqual(observation.files, ["src/app.py", "src/bad.py"])
        self.assertEqual([(item.kind, item.name) for item in observation.python_files[0].symbols], [("class", "App"), ("function", "run")])
        self.assertFalse(observation.python_files[1].ok)
        self.assertIn("Python syntax error", observation.python_files[1].message)
        self.assertEqual(invalid.kind, "repo_map")
        self.assertFalse(invalid.ok)
        self.assertIn("escapes", invalid.message)

    def test_execute_project_action_errors_are_observations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            Path(base, "asset.bin").write_bytes(b"\x00\x01")

            read = execute_action(workspace, ReadFileAction(type="read_file", path="missing.py"))
            binary_read = execute_action(workspace, ReadFileAction(type="read_file", path="asset.bin"))
            read_files = execute_action(
                workspace,
                ReadFilesAction(type="read_files", paths=["missing.py", "asset.bin"]),
            )
            read_ranges = execute_action(
                workspace,
                ReadFileRangesAction(
                    type="read_file_ranges",
                    ranges=[ReadFileRangeItem(path="missing.py", start_line=1, line_count=1)],
                ),
            )
            edit = execute_action(workspace, EditFileAction(type="edit_file", path="missing.py", old="a", new="b"))
            binary_edit = execute_action(workspace, EditFileAction(type="edit_file", path="asset.bin", old="a", new="b"))
            multi_edit = execute_action(
                workspace,
                MultiEditAction(type="multi_edit_file", path="missing.py", edits=[EditOperation(old="a", new="b")]),
            )
            binary_multi_edit = execute_action(
                workspace,
                MultiEditAction(type="multi_edit_file", path="asset.bin", edits=[EditOperation(old="a", new="b")]),
            )
            replace_lines = execute_action(
                workspace,
                ReplaceLinesAction(type="replace_lines", path="missing.py", start_line=1, end_line=1, content="new\n"),
            )
            binary_replace_lines = execute_action(
                workspace,
                ReplaceLinesAction(type="replace_lines", path="asset.bin", start_line=1, end_line=1, content="new\n"),
            )
            insert_lines = execute_action(
                workspace,
                InsertLinesAction(type="insert_lines", path="missing.py", line=1, content="new\n"),
            )
            binary_insert_lines = execute_action(
                workspace,
                InsertLinesAction(type="insert_lines", path="asset.bin", line=1, content="new\n"),
            )
            check_patch = execute_action(
                workspace,
                CheckPatchAction(type="check_patch", path="missing.py", patch="@@ -1 +1 @@\n-a\n+b\n"),
            )
            binary_check_patch = execute_action(
                workspace,
                CheckPatchAction(type="check_patch", path="asset.bin", patch="@@ -1 +1 @@\n-a\n+b\n"),
            )
            check_patches = execute_action(
                workspace,
                CheckPatchesAction(
                    type="check_patches",
                    patch="--- a/missing.py\n+++ b/missing.py\n@@ -1 +1 @@\n-a\n+b\n",
                ),
            )
            patch = execute_action(
                workspace,
                PatchFileAction(type="patch_file", path="missing.py", patch="@@ -1 +1 @@\n-a\n+b\n"),
            )
            binary_patch = execute_action(
                workspace,
                PatchFileAction(type="patch_file", path="asset.bin", patch="@@ -1 +1 @@\n-a\n+b\n"),
            )
            patch_files = execute_action(
                workspace,
                PatchFilesAction(
                    type="patch_files",
                    patch="--- a/missing.py\n+++ b/missing.py\n@@ -1 +1 @@\n-a\n+b\n",
                ),
            )
            binary_patch_files = execute_action(
                workspace,
                PatchFilesAction(
                    type="patch_files",
                    patch="--- a/asset.bin\n+++ b/asset.bin\n@@ -1 +1 @@\n-a\n+b\n",
                ),
            )
            delete = execute_action(workspace, DeleteFileAction(type="delete_file", path="missing.py"))
            binary_delete = execute_action(workspace, DeleteFileAction(type="delete_file", path="asset.bin"))
            move = execute_action(
                workspace,
                MoveFileAction(type="move_file", source="missing.py", destination="new.py"),
            )

            self.assertEqual(read.kind, "read_file")
            self.assertIn("File does not exist", read.message)
            self.assertEqual(binary_read.kind, "read_file")
            self.assertIn("binary or non-UTF-8", binary_read.message)
            self.assertEqual(read_files.kind, "read_files")
            self.assertFalse(read_files.files[0].ok)
            self.assertIn("File does not exist", read_files.files[0].message)
            self.assertFalse(read_files.files[1].ok)
            self.assertIn("binary or non-UTF-8", read_files.files[1].message)
            self.assertEqual(read_ranges.kind, "read_file_ranges")
            self.assertFalse(read_ranges.ranges[0].ok)
            self.assertIn("File does not exist", read_ranges.ranges[0].message)
            self.assertEqual(edit.kind, "edit_file")
            self.assertFalse(edit.ok)
            self.assertIn("File does not exist", edit.message)
            self.assertFalse(binary_edit.ok)
            self.assertIn("binary or non-UTF-8", binary_edit.message)
            self.assertEqual(multi_edit.kind, "multi_edit_file")
            self.assertFalse(multi_edit.ok)
            self.assertIn("File does not exist", multi_edit.message)
            self.assertFalse(binary_multi_edit.ok)
            self.assertIn("binary or non-UTF-8", binary_multi_edit.message)
            self.assertEqual(replace_lines.kind, "replace_lines")
            self.assertFalse(replace_lines.ok)
            self.assertIn("File does not exist", replace_lines.message)
            self.assertFalse(binary_replace_lines.ok)
            self.assertIn("binary or non-UTF-8", binary_replace_lines.message)
            self.assertEqual(insert_lines.kind, "insert_lines")
            self.assertFalse(insert_lines.ok)
            self.assertIn("File does not exist", insert_lines.message)
            self.assertFalse(binary_insert_lines.ok)
            self.assertIn("binary or non-UTF-8", binary_insert_lines.message)
            self.assertEqual(check_patch.kind, "check_patch")
            self.assertFalse(check_patch.ok)
            self.assertIn("File does not exist", check_patch.message)
            self.assertFalse(binary_check_patch.ok)
            self.assertIn("binary or non-UTF-8", binary_check_patch.message)
            self.assertEqual(check_patches.kind, "check_patches")
            self.assertFalse(check_patches.ok)
            self.assertIn("File does not exist", check_patches.message)
            self.assertEqual(patch.kind, "patch_file")
            self.assertFalse(patch.ok)
            self.assertIn("File does not exist", patch.message)
            self.assertFalse(binary_patch.ok)
            self.assertIn("binary or non-UTF-8", binary_patch.message)
            self.assertEqual(patch_files.kind, "patch_files")
            self.assertFalse(patch_files.ok)
            self.assertIn("File does not exist", patch_files.message)
            self.assertFalse(binary_patch_files.ok)
            self.assertIn("binary or non-UTF-8", binary_patch_files.message)
            self.assertEqual(delete.kind, "delete_file")
            self.assertFalse(delete.ok)
            self.assertIn("File does not exist", delete.message)
            self.assertFalse(binary_delete.ok)
            self.assertIn("binary or non-UTF-8", binary_delete.message)
            self.assertEqual(move.kind, "move_file")
            self.assertFalse(move.ok)
            self.assertIn("File does not exist", move.message)

    def test_execute_action_blocks_high_risk_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")

            observation = execute_action(workspace, RunCommandAction(type="run_command", command="sudo reboot"))

            self.assertEqual(observation.kind, "run_command")
            self.assertIsNone(observation.result.exit_code)
            self.assertIn("Command blocked", observation.result.stderr)

    def test_execute_background_process_actions_start_read_and_stop_process(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/app.py", "print('ok')\n")
            start = execute_action(
                workspace,
                StartCommandAction(
                    type="start_command",
                    command="python3 -c \"import os, time; print(os.getcwd(), flush=True); time.sleep(5)\"",
                    cwd="pkg",
                ),
            )
            try:
                self.assertEqual(start.kind, "start_command")
                self.assertTrue(start.ok)
                self.assertTrue(start.process_id)
                self.assertEqual(start.cwd, "pkg")
                time.sleep(0.2)

                read = execute_action(workspace, ReadProcessAction(type="read_process", process_id=start.process_id))
                self.assertEqual(read.kind, "read_process")
                self.assertTrue(read.ok)
                self.assertTrue(read.running)
                self.assertIn(str(Path(base, "pkg").resolve()), read.stdout)

                listed = execute_action(workspace, ListProcessesAction(type="list_processes"))
                self.assertEqual(listed.kind, "list_processes")
                self.assertEqual(len(listed.processes), 1)
                self.assertEqual(listed.processes[0].process_id, start.process_id)
                self.assertEqual(listed.processes[0].cwd, "pkg")
                self.assertTrue(listed.processes[0].running)

                stop = execute_action(workspace, StopProcessAction(type="stop_process", process_id=start.process_id))
                self.assertEqual(stop.kind, "stop_process")
                self.assertTrue(stop.ok)
                self.assertIsNotNone(stop.exit_code)
            finally:
                if start.kind == "start_command" and start.process_id:
                    execute_action(workspace, StopProcessAction(type="stop_process", process_id=start.process_id))

    def test_execute_background_process_actions_report_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")

            blocked = execute_action(workspace, StartCommandAction(type="start_command", command="sudo reboot"))
            invalid_cwd = execute_action(
                workspace,
                StartCommandAction(type="start_command", command="python3 -m http.server", cwd="../outside"),
            )
            read = execute_action(workspace, ReadProcessAction(type="read_process", process_id="missing"))
            stopped = execute_action(workspace, StopProcessAction(type="stop_process", process_id="missing"))

        self.assertEqual(blocked.kind, "start_command")
        self.assertFalse(blocked.ok)
        self.assertIn("Command blocked", blocked.message)
        self.assertEqual(invalid_cwd.kind, "start_command")
        self.assertFalse(invalid_cwd.ok)
        self.assertIn("escapes", invalid_cwd.message)
        self.assertEqual(read.kind, "read_process")
        self.assertFalse(read.ok)
        self.assertEqual(stopped.kind, "stop_process")
        self.assertFalse(stopped.ok)

    def test_execute_update_plan_returns_plan_observation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-actions-") as base:
            workspace = create_run_workspace(base, "test-run")
            action = parse_tool_action(
                "update_plan",
                {
                    "plan": [
                        {"step": "Inspect files", "status": "completed"},
                        {"step": "Run tests", "status": "in_progress"},
                    ]
                },
            )

            observation = execute_action(workspace, action)

        self.assertEqual(observation.kind, "update_plan")
        self.assertEqual([item.step for item in observation.plan], ["Inspect files", "Run tests"])
        self.assertIn("Run tests", observation.message)


if __name__ == "__main__":
    unittest.main()
