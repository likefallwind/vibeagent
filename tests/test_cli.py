import io
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

from vibeagent import cli as cli_module
from vibeagent.cli import main


class CliTests(unittest.TestCase):
    def test_main_interactive_uses_requested_cwd_and_restores_original_cwd(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-cli-") as base:
            stdout = io.StringIO()
            original_cwd = Path.cwd()
            seen_cwds: list[Path] = []

            def fake_git_status_text() -> str:
                seen_cwds.append(Path.cwd())
                return "Git status:\n  ok: yes"

            with (
                patch("builtins.input", side_effect=["/git-status", "/exit"]),
                patch("vibeagent.cli.create_chat_client") as create_chat_client,
                patch("vibeagent.cli.get_git_status_text", side_effect=fake_git_status_text),
                redirect_stdout(stdout),
            ):
                exit_code = main(["--cwd", base])

        self.assertEqual(exit_code, 0)
        self.assertIn("Git status:", stdout.getvalue())
        self.assertEqual(seen_cwds, [Path(base).resolve()])
        self.assertEqual(Path.cwd(), original_cwd)
        create_chat_client.assert_not_called()

    def test_main_interactive_tool_search_reports_invalid_option_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with (
            patch("builtins.input", side_effect=["/tool-search --category missing verification", "/exit"]),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_tool_search_text") as get_tool_search_text,
            redirect_stdout(stdout),
        ):
            exit_code = main([])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /tool-search", output)
        self.assertIn("--category must be one of:", output)
        get_tool_search_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_handles_session_commands_without_creating_client(self) -> None:
        stdout = io.StringIO()

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "builtins.input",
                    side_effect=[
                        "/sessions",
                        "/usage",
                        "/cost",
                        "/doctor",
                        "/config",
                        "/review",
                        "/handoff",
                        "/changes",
                        "/diff --staged app.py",
                        "/diff-hunks --staged app.py",
                        "/diff-contexts --staged app.py",
                        "/tools",
                        "/tool read_file",
                        "/tool-search --max 3 --category session --approval no verification",
                        "/permissions",
                        "/checks",
                        "/commands",
                        "/related-tests pkg/actions.py",
                        "/focused-tests pkg/actions.py",
                        "/check-focused-tests pkg/actions.py",
                        "/run-focused-tests pkg/actions.py",
                        "/manifests",
                        "/command python3 --version",
                        "/run python3 --version",
                        "/check-run-seq python3 --version ;; npm test",
                        "/run-seq python3 --version ;; npm test",
                        "/check-start npm run dev",
                        "/start npm run dev",
                        "/port 5173 127.0.0.1 1500",
                        "/http http://127.0.0.1:5173 ready",
                        "/http-fetch http://127.0.0.1:5173/app",
                        "/overview",
                        "/repo-map src",
                        "/search needle",
                        "/search-contexts needle",
                        "/glob **/*.py",
                        "/tree src",
                        "/symbols src/app.py web/app.ts",
                        "/file-info src/app.py asset.bin",
                        "/image-info assets/logo.png",
                        "/read src/app.py 2:4",
                        "/around src/app.py 42 8",
                        "/around-many src/app.py:42:8 tests/test_app.py:17",
                        "/output-contexts src/app.py:42:8",
                        "/output-diagnostics ERROR src/app.py:42:8 failed",
                        "/python-traceback ValueError: bad",
                        "/tail logs/app.log 3",
                        "/read-files src/app.py tests/test_app.py",
                        "/read-ranges src/app.py:2:4 tests/test_app.py:1",
                        "/python-check src",
                        "/python-deps src",
                        "/python-defs Runner.run src",
                        "/python-refs run_agent src",
                        "/python-ref-contexts run_agent src",
                        "/python-calls helper src",
                        "/python-call-graph src",
                        "/python-rename-preview run_agent execute_agent src",
                        "/python-rename run_agent execute_agent src",
                        "/check-replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src",
                        "/replace-python-def Runner.run '    def run(self):\\n        return 2\\n' src",
                        "/config-check pyproject.toml",
                        "/check-json-set package.json /private true",
                        "/json-set package.json /scripts/test '\"npm test\"'",
                        "/check-json-remove package.json /scripts/dev",
                        "/json-remove package.json /keywords/0",
                        "/check-json-patch package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'",
                        "/json-patch package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'",
                        "/check-replace-lines app.py 2 3 'new\\n'",
                        "/replace-lines app.py 2 2 'new\\n'",
                        "/check-insert-lines app.py 2 'new\\n'",
                        "/insert-lines app.py 2 'new\\n'",
                        "/check-append app.py 'new\\n'",
                        "/append app.py 'new\\n'",
                        "/check-write app.py 'new\\n'",
                        "/write app.py 'new\\n'",
                        "/check-write-files app.py 'a\\n' test.py 'b\\n'",
                        "/write-files app.py 'a\\n' test.py 'b\\n'",
                        "/check-edit app.py old new",
                        "/edit app.py old new",
                        "/check-multi-edit app.py old new print log",
                        "/multi-edit app.py old new print log",
                        "/check-delete old.py",
                        "/delete old.py",
                        "/check-delete-files old.py other.py",
                        "/delete-files old.py other.py",
                        "/check-move old.py new.py",
                        "/move old.py new.py",
                        "/check-move-files old.py new.py other.py other-new.py",
                        "/move-files old.py new.py other.py other-new.py",
                        "/check-copy template.py new.py",
                        "/copy template.py new.py",
                        "/check-copy-files template.py new.py config.py config-copy.py",
                        "/copy-files template.py new.py config.py config-copy.py",
                        "/check-move-dir old_pkg new_pkg",
                        "/move-dir old_pkg new_pkg",
                        "/check-move-dirs old_a new_a old_b new_b",
                        "/move-dirs old_a new_a old_b new_b",
                        "/check-copy-dir template_pkg copy_pkg",
                        "/copy-dir template_pkg copy_pkg",
                        "/check-copy-dirs template_a copy_a template_b copy_b",
                        "/copy-dirs template_a copy_a template_b copy_b",
                        "/check-mkdir pkg/generated",
                        "/mkdir pkg/generated",
                        "/check-mkdirs pkg/generated assets/icons",
                        "/mkdirs pkg/generated assets/icons",
                        "/check-rmdir pkg/generated",
                        "/rmdir pkg/generated",
                        "/check-rmdirs pkg/generated assets/icons",
                        "/rmdirs pkg/generated assets/icons",
                        "/check-executable tool.sh false",
                        "/set-executable tool.sh true",
                        "/check-patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/patch app.py '@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/check-patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/patches '--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'",
                        "/check-regex-replace --ignore-case app.py old new",
                        "/regex-replace --count 1 app.py old new",
                        "/code-deps web",
                        "/code-refs runAgent web",
                        "/code-ref-contexts runAgent web",
                        "/code-defs runAgent web",
                        "/code-rename-preview runAgent executeAgent web",
                        "/code-rename runAgent executeAgent web",
                        "/git-status",
                        "/conflicts src",
                        "/git-info",
                        "/branches",
                        "/log app.py 2",
                        "/show HEAD app.py",
                        "/blame app.py 2:2",
                        "/stashes 3",
                        "/check-fetch origin",
                        "/fetch origin",
                        "/check-pull",
                        "/pull",
                        "/check-push",
                        "/push",
                        "/check-stash --include-untracked save work",
                        "/stash save work",
                        "/check-stash-apply stash@{0}",
                        "/stash-apply stash@{0}",
                        "/check-stash-drop stash@{0}",
                        "/stash-drop stash@{0}",
                        "/check-stage app.py",
                        "/stage app.py",
                        "/check-unstage app.py",
                        "/unstage app.py",
                        "/check-commit update app",
                        "/commit update app",
                        "/check-restore app.py",
                        "/restore app.py",
                        "/check-switch --create feature/demo",
                        "/switch feature/demo",
                        "/env",
                        "/processes",
                        "/process bg-1 2000",
                        "/process-output-contexts bg-1 2000",
                        "/process-output-diagnostics bg-1 2000",
                        "/wait-process bg-1 5000 2000",
                        "/check-write-process bg-1 hello\\n",
                        "/write-process bg-1 hello\\n",
                        "/check-stop-process bg-1",
                        "/stop-process bg-1",
                        "/check-stop-processes",
                        "/stop-processes",
                        "/session run-1",
                        "/last",
                        "/plan run-1",
                        "/transcript run-1",
                        "/checkpoint before tests",
                        "/checkpoints",
                        "/checkpoint-show ckpt-1",
                        "/checkpoint-diff ckpt-1",
                        "/checkpoint-status ckpt-1",
                        "/check-checkpoint-restore ckpt-1",
                        "/checkpoint-restore ckpt-1",
                        "/check-checkpoint-delete ckpt-1",
                        "/checkpoint-delete ckpt-1",
                        "/check-checkpoint-prune 2",
                        "/checkpoint-prune 2",
                        "/resume run-1",
                        "/compact run-1",
                        "/context",
                        "/init",
                        "/clear",
                        "/exit",
                    ],
                )
            )
            create_chat_client = stack.enter_context(patch("vibeagent.cli.create_chat_client"))
            stack.enter_context(patch("vibeagent.cli.get_sessions_text", return_value="Recent sessions:\n  run-1"))
            stack.enter_context(patch("vibeagent.cli.get_usage_text", return_value="Usage:\n  sessions: 1"))
            stack.enter_context(patch("vibeagent.cli.get_cost_text", return_value="Cost:\n  estimatedCostUsd: $0.000001"))
            stack.enter_context(patch("vibeagent.cli.get_doctor_text", return_value="Doctor:\n  provider: minimax"))
            get_config_text = stack.enter_context(patch("vibeagent.cli.get_config_text", return_value="Config:\n  provider: minimax"))
            stack.enter_context(patch("vibeagent.cli.get_review_text", return_value="Review:\n  ready: yes"))
            get_handoff_text = stack.enter_context(patch("vibeagent.cli.get_handoff_text", return_value="Handoff:\n  ready: yes"))
            get_changes_text = stack.enter_context(patch("vibeagent.cli.get_changes_text", return_value="Changes:\n  changedFiles: 1"))
            get_diff_text = stack.enter_context(patch("vibeagent.cli.get_diff_text", return_value="Diff:\n  scope: staged"))
            get_diff_hunks_text = stack.enter_context(patch("vibeagent.cli.get_diff_hunks_text", return_value="Diff hunks:\n  hunks: 1/1"))
            get_diff_contexts_text = stack.enter_context(patch("vibeagent.cli.get_diff_contexts_text", return_value="Diff contexts:\n  contexts: 1/1"))
            stack.enter_context(patch("vibeagent.cli.get_tools_text", return_value="Tools:\n  total: 1"))
            stack.enter_context(patch("vibeagent.cli.get_tool_text", return_value="Tool: read_file"))
            get_tool_search_text = stack.enter_context(patch("vibeagent.cli.get_tool_search_text", return_value="Tool search:\n  matches: 1/1"))
            get_permissions_text = stack.enter_context(patch("vibeagent.cli.get_permissions_text", return_value="Permissions:\n  approvalPolicy: ask"))
            get_checks_text = stack.enter_context(patch("vibeagent.cli.get_checks_text", return_value="Checks:\n  suggestedChecks: 1/1"))
            get_commands_text = stack.enter_context(patch("vibeagent.cli.get_commands_text", return_value="Project commands:\n  commands: 1/1"))
            get_related_tests_text = stack.enter_context(patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1"))
            get_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1"))
            get_check_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes"))
            get_run_focused_test_commands_text = stack.enter_context(patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes"))
            get_manifests_text = stack.enter_context(patch("vibeagent.cli.get_manifests_text", return_value="Manifests:\n  files: 1/1"))
            get_command_check_text = stack.enter_context(patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes"))
            get_run_text = stack.enter_context(patch("vibeagent.cli.get_run_text", return_value="Run:\n  ok: yes"))
            get_check_run_sequence_text = stack.enter_context(patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes"))
            get_run_sequence_text = stack.enter_context(patch("vibeagent.cli.get_run_sequence_text", return_value="Run sequence:\n  ok: yes"))
            get_check_start_text = stack.enter_context(patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes"))
            get_start_text = stack.enter_context(patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes"))
            get_port_text = stack.enter_context(patch("vibeagent.cli.get_port_text", return_value="Port:\n  ok: yes"))
            get_http_text = stack.enter_context(patch("vibeagent.cli.get_http_text", return_value="HTTP:\n  ok: yes"))
            get_http_fetch_text = stack.enter_context(patch("vibeagent.cli.get_http_fetch_text", return_value="HTTP fetch:\n  ok: yes"))
            get_overview_text = stack.enter_context(patch("vibeagent.cli.get_overview_text", return_value="Overview:\n  files: 1/1"))
            get_repo_map_text = stack.enter_context(patch("vibeagent.cli.get_repo_map_text", return_value="Repo map:\n  files: 1/1"))
            get_search_text = stack.enter_context(patch("vibeagent.cli.get_search_text", return_value="Search:\n  matches: 1/1"))
            get_search_contexts_text = stack.enter_context(patch("vibeagent.cli.get_search_contexts_text", return_value="Search contexts:\n  contexts: 1/1"))
            get_glob_text = stack.enter_context(patch("vibeagent.cli.get_glob_text", return_value="Glob:\n  matches: 1/1"))
            get_tree_text = stack.enter_context(patch("vibeagent.cli.get_tree_text", return_value="Tree:\n  entries: 1/1"))
            get_symbols_text = stack.enter_context(patch("vibeagent.cli.get_symbols_text", return_value="Symbols:\n  files: 1/1"))
            get_file_info_text = stack.enter_context(patch("vibeagent.cli.get_file_info_text", return_value="File info:\n  paths: 1/1"))
            get_image_info_text = stack.enter_context(patch("vibeagent.cli.get_image_info_text", return_value="Image info:\n  images: 1/1"))
            get_read_text = stack.enter_context(patch("vibeagent.cli.get_read_text", return_value="Read:\n  ok: yes"))
            get_around_text = stack.enter_context(patch("vibeagent.cli.get_around_text", return_value="Around:\n  ok: yes"))
            get_around_many_text = stack.enter_context(patch("vibeagent.cli.get_around_many_text", return_value="Around many:\n  contexts: 2/2"))
            get_output_contexts_text = stack.enter_context(patch("vibeagent.cli.get_output_contexts_text", return_value="Output contexts:\n  contexts: 1/1"))
            get_output_diagnostics_text = stack.enter_context(patch("vibeagent.cli.get_output_diagnostics_text", return_value="Output diagnostics:\n  diagnostics: 1/1"))
            get_python_traceback_text = stack.enter_context(patch("vibeagent.cli.get_python_traceback_text", return_value="Python traceback:\n  diagnostics: 1/1"))
            get_tail_text = stack.enter_context(patch("vibeagent.cli.get_tail_text", return_value="Tail:\n  ok: yes"))
            get_read_files_text = stack.enter_context(patch("vibeagent.cli.get_read_files_text", return_value="Read files:\n  files: 2/2"))
            get_read_ranges_text = stack.enter_context(patch("vibeagent.cli.get_read_ranges_text", return_value="Read ranges:\n  ranges: 2/2"))
            get_python_check_text = stack.enter_context(patch("vibeagent.cli.get_python_check_text", return_value="Python check:\n  ok: yes"))
            get_python_deps_text = stack.enter_context(patch("vibeagent.cli.get_python_deps_text", return_value="Python dependencies:\n  files: 1/1"))
            get_python_defs_text = stack.enter_context(patch("vibeagent.cli.get_python_defs_text", return_value="Python definitions:\n  definitions: 1/1"))
            get_python_refs_text = stack.enter_context(patch("vibeagent.cli.get_python_refs_text", return_value="Python references:\n  references: 1/1"))
            get_python_ref_contexts_text = stack.enter_context(patch("vibeagent.cli.get_python_ref_contexts_text", return_value="Python reference contexts:\n  contexts: 1/1"))
            get_python_calls_text = stack.enter_context(patch("vibeagent.cli.get_python_calls_text", return_value="Python calls:\n  calls: 1/1"))
            get_python_call_graph_text = stack.enter_context(patch("vibeagent.cli.get_python_call_graph_text", return_value="Python call graph:\n  edges: 3/3"))
            get_python_rename_preview_text = stack.enter_context(patch("vibeagent.cli.get_python_rename_preview_text", return_value="Python rename preview:\n  replacements: 2"))
            get_python_rename_text = stack.enter_context(patch("vibeagent.cli.get_python_rename_text", return_value="Python rename:\n  replacements: 2"))
            get_check_replace_python_definition_text = stack.enter_context(patch("vibeagent.cli.get_check_replace_python_definition_text", return_value="Check replace Python definition:\n  ok: yes"))
            get_replace_python_definition_text = stack.enter_context(patch("vibeagent.cli.get_replace_python_definition_text", return_value="Replace Python definition:\n  ok: yes"))
            get_config_check_text = stack.enter_context(patch("vibeagent.cli.get_config_check_text", return_value="Config check:\n  ok: yes"))
            get_check_json_set_text = stack.enter_context(patch("vibeagent.cli.get_check_json_set_text", return_value="Check JSON set:\n  ok: yes"))
            get_json_set_text = stack.enter_context(patch("vibeagent.cli.get_json_set_text", return_value="JSON set:\n  ok: yes"))
            get_check_json_remove_text = stack.enter_context(patch("vibeagent.cli.get_check_json_remove_text", return_value="Check JSON remove:\n  ok: yes"))
            get_json_remove_text = stack.enter_context(patch("vibeagent.cli.get_json_remove_text", return_value="JSON remove:\n  ok: yes"))
            get_check_json_patch_text = stack.enter_context(patch("vibeagent.cli.get_check_json_patch_text", return_value="Check JSON patch:\n  ok: yes"))
            get_json_patch_text = stack.enter_context(patch("vibeagent.cli.get_json_patch_text", return_value="JSON patch:\n  ok: yes"))
            get_check_replace_lines_text = stack.enter_context(patch("vibeagent.cli.get_check_replace_lines_text", return_value="Check replace lines:\n  ok: yes"))
            get_replace_lines_text = stack.enter_context(patch("vibeagent.cli.get_replace_lines_text", return_value="Replace lines:\n  ok: yes"))
            get_check_insert_lines_text = stack.enter_context(patch("vibeagent.cli.get_check_insert_lines_text", return_value="Check insert lines:\n  ok: yes"))
            get_insert_lines_text = stack.enter_context(patch("vibeagent.cli.get_insert_lines_text", return_value="Insert lines:\n  ok: yes"))
            get_check_append_file_text = stack.enter_context(patch("vibeagent.cli.get_check_append_file_text", return_value="Check append:\n  ok: yes"))
            get_append_file_text = stack.enter_context(patch("vibeagent.cli.get_append_file_text", return_value="Append:\n  ok: yes"))
            get_check_write_file_text = stack.enter_context(patch("vibeagent.cli.get_check_write_file_text", return_value="Check write:\n  ok: yes"))
            get_write_file_text = stack.enter_context(patch("vibeagent.cli.get_write_file_text", return_value="Write:\n  ok: yes"))
            get_check_write_files_text = stack.enter_context(patch("vibeagent.cli.get_check_write_files_text", return_value="Check write files:\n  ok: yes"))
            get_write_files_text = stack.enter_context(patch("vibeagent.cli.get_write_files_text", return_value="Write files:\n  ok: yes"))
            get_check_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_check_edit_file_text", return_value="Check edit:\n  ok: yes"))
            get_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_edit_file_text", return_value="Edit:\n  ok: yes"))
            get_check_multi_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_check_multi_edit_file_text", return_value="Check multi edit:\n  ok: yes"))
            get_multi_edit_file_text = stack.enter_context(patch("vibeagent.cli.get_multi_edit_file_text", return_value="Multi edit:\n  ok: yes"))
            get_check_delete_file_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_file_text", return_value="Check delete:\n  ok: yes"))
            get_delete_file_text = stack.enter_context(patch("vibeagent.cli.get_delete_file_text", return_value="Delete:\n  ok: yes"))
            get_check_delete_files_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_files_text", return_value="Check delete files:\n  ok: yes"))
            get_delete_files_text = stack.enter_context(patch("vibeagent.cli.get_delete_files_text", return_value="Delete files:\n  ok: yes"))
            get_check_move_file_text = stack.enter_context(patch("vibeagent.cli.get_check_move_file_text", return_value="Check move:\n  ok: yes"))
            get_move_file_text = stack.enter_context(patch("vibeagent.cli.get_move_file_text", return_value="Move:\n  ok: yes"))
            get_check_move_files_text = stack.enter_context(patch("vibeagent.cli.get_check_move_files_text", return_value="Check move files:\n  ok: yes"))
            get_move_files_text = stack.enter_context(patch("vibeagent.cli.get_move_files_text", return_value="Move files:\n  ok: yes"))
            get_check_copy_file_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_file_text", return_value="Check copy:\n  ok: yes"))
            get_copy_file_text = stack.enter_context(patch("vibeagent.cli.get_copy_file_text", return_value="Copy:\n  ok: yes"))
            get_check_copy_files_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_files_text", return_value="Check copy files:\n  ok: yes"))
            get_copy_files_text = stack.enter_context(patch("vibeagent.cli.get_copy_files_text", return_value="Copy files:\n  ok: yes"))
            get_check_move_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_move_dir_text", return_value="Check move dir:\n  ok: yes"))
            get_move_dir_text = stack.enter_context(patch("vibeagent.cli.get_move_dir_text", return_value="Move dir:\n  ok: yes"))
            get_check_move_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_move_dirs_text", return_value="Check move dirs:\n  ok: yes"))
            get_move_dirs_text = stack.enter_context(patch("vibeagent.cli.get_move_dirs_text", return_value="Move dirs:\n  ok: yes"))
            get_check_copy_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_dir_text", return_value="Check copy dir:\n  ok: yes"))
            get_copy_dir_text = stack.enter_context(patch("vibeagent.cli.get_copy_dir_text", return_value="Copy dir:\n  ok: yes"))
            get_check_copy_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_copy_dirs_text", return_value="Check copy dirs:\n  ok: yes"))
            get_copy_dirs_text = stack.enter_context(patch("vibeagent.cli.get_copy_dirs_text", return_value="Copy dirs:\n  ok: yes"))
            get_check_create_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_create_dir_text", return_value="Check mkdir:\n  ok: yes"))
            get_create_dir_text = stack.enter_context(patch("vibeagent.cli.get_create_dir_text", return_value="Mkdir:\n  ok: yes"))
            get_check_create_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_create_dirs_text", return_value="Check mkdirs:\n  ok: yes"))
            get_create_dirs_text = stack.enter_context(patch("vibeagent.cli.get_create_dirs_text", return_value="Mkdirs:\n  ok: yes"))
            get_check_delete_empty_dir_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_empty_dir_text", return_value="Check rmdir:\n  ok: yes"))
            get_delete_empty_dir_text = stack.enter_context(patch("vibeagent.cli.get_delete_empty_dir_text", return_value="Rmdir:\n  ok: yes"))
            get_check_delete_empty_dirs_text = stack.enter_context(patch("vibeagent.cli.get_check_delete_empty_dirs_text", return_value="Check rmdirs:\n  ok: yes"))
            get_delete_empty_dirs_text = stack.enter_context(patch("vibeagent.cli.get_delete_empty_dirs_text", return_value="Rmdirs:\n  ok: yes"))
            get_check_set_executable_text = stack.enter_context(patch("vibeagent.cli.get_check_set_executable_text", return_value="Check executable:\n  ok: yes"))
            get_set_executable_text = stack.enter_context(patch("vibeagent.cli.get_set_executable_text", return_value="Set executable:\n  ok: yes"))
            get_check_patch_text = stack.enter_context(patch("vibeagent.cli.get_check_patch_text", return_value="Check patch:\n  ok: yes"))
            get_patch_text = stack.enter_context(patch("vibeagent.cli.get_patch_text", return_value="Patch:\n  ok: yes"))
            get_check_patches_text = stack.enter_context(patch("vibeagent.cli.get_check_patches_text", return_value="Check patches:\n  ok: yes"))
            get_patches_text = stack.enter_context(patch("vibeagent.cli.get_patches_text", return_value="Patches:\n  ok: yes"))
            get_check_regex_replace_text = stack.enter_context(patch("vibeagent.cli.get_check_regex_replace_text", return_value="Check regex replace:\n  ok: yes"))
            get_regex_replace_text = stack.enter_context(patch("vibeagent.cli.get_regex_replace_text", return_value="Regex replace:\n  ok: yes"))
            get_code_deps_text = stack.enter_context(patch("vibeagent.cli.get_code_deps_text", return_value="Code dependencies:\n  files: 1/1"))
            get_code_refs_text = stack.enter_context(patch("vibeagent.cli.get_code_refs_text", return_value="Code references:\n  references: 1/1"))
            get_code_ref_contexts_text = stack.enter_context(patch("vibeagent.cli.get_code_ref_contexts_text", return_value="Code reference contexts:\n  contexts: 1/1"))
            get_code_defs_text = stack.enter_context(patch("vibeagent.cli.get_code_defs_text", return_value="Code definitions:\n  definitions: 1/1"))
            get_code_rename_preview_text = stack.enter_context(patch("vibeagent.cli.get_code_rename_preview_text", return_value="Code rename preview:\n  replacements: 2"))
            get_code_rename_text = stack.enter_context(patch("vibeagent.cli.get_code_rename_text", return_value="Code rename:\n  replacements: 2"))
            get_git_status_text = stack.enter_context(patch("vibeagent.cli.get_git_status_text", return_value="Git status:\n  ok: yes"))
            get_git_conflicts_text = stack.enter_context(patch("vibeagent.cli.get_git_conflicts_text", return_value="Git conflicts:\n  ok: yes"))
            get_git_info_text = stack.enter_context(patch("vibeagent.cli.get_git_info_text", return_value="Git info:\n  branch: main"))
            get_branches_text = stack.enter_context(patch("vibeagent.cli.get_branches_text", return_value="Branches:\n  current: main"))
            get_log_text = stack.enter_context(patch("vibeagent.cli.get_log_text", return_value="Log:\n  ok: yes"))
            get_show_text = stack.enter_context(patch("vibeagent.cli.get_show_text", return_value="Show:\n  ok: yes"))
            get_blame_text = stack.enter_context(patch("vibeagent.cli.get_blame_text", return_value="Blame:\n  ok: yes"))
            get_stashes_text = stack.enter_context(patch("vibeagent.cli.get_stashes_text", return_value="Stashes:\n  entries: 1/1"))
            get_check_fetch_text = stack.enter_context(patch("vibeagent.cli.get_check_fetch_text", return_value="Check fetch:\n  ok: yes"))
            get_fetch_text = stack.enter_context(patch("vibeagent.cli.get_fetch_text", return_value="Fetch:\n  ok: yes"))
            get_check_pull_text = stack.enter_context(patch("vibeagent.cli.get_check_pull_text", return_value="Check pull:\n  ok: yes"))
            get_pull_text = stack.enter_context(patch("vibeagent.cli.get_pull_text", return_value="Pull:\n  ok: yes"))
            get_check_push_text = stack.enter_context(patch("vibeagent.cli.get_check_push_text", return_value="Check push:\n  ok: yes"))
            get_push_text = stack.enter_context(patch("vibeagent.cli.get_push_text", return_value="Push:\n  ok: yes"))
            get_check_stash_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_text", return_value="Check stash:\n  ok: yes"))
            get_stash_text = stack.enter_context(patch("vibeagent.cli.get_stash_text", return_value="Stash:\n  ok: yes"))
            get_check_stash_apply_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_apply_text", return_value="Check stash apply:\n  ok: yes"))
            get_stash_apply_text = stack.enter_context(patch("vibeagent.cli.get_stash_apply_text", return_value="Stash apply:\n  ok: yes"))
            get_check_stash_drop_text = stack.enter_context(patch("vibeagent.cli.get_check_stash_drop_text", return_value="Check stash drop:\n  ok: yes"))
            get_stash_drop_text = stack.enter_context(patch("vibeagent.cli.get_stash_drop_text", return_value="Stash drop:\n  ok: yes"))
            get_check_stage_text = stack.enter_context(patch("vibeagent.cli.get_check_stage_text", return_value="Check stage:\n  ok: yes"))
            get_stage_text = stack.enter_context(patch("vibeagent.cli.get_stage_text", return_value="Stage:\n  ok: yes"))
            get_check_unstage_text = stack.enter_context(patch("vibeagent.cli.get_check_unstage_text", return_value="Check unstage:\n  ok: yes"))
            get_unstage_text = stack.enter_context(patch("vibeagent.cli.get_unstage_text", return_value="Unstage:\n  ok: yes"))
            get_check_commit_text = stack.enter_context(patch("vibeagent.cli.get_check_commit_text", return_value="Check commit:\n  ok: yes"))
            get_commit_text = stack.enter_context(patch("vibeagent.cli.get_commit_text", return_value="Commit:\n  ok: yes"))
            get_check_restore_text = stack.enter_context(patch("vibeagent.cli.get_check_restore_text", return_value="Check restore:\n  ok: yes"))
            get_restore_text = stack.enter_context(patch("vibeagent.cli.get_restore_text", return_value="Restore:\n  ok: yes"))
            get_check_switch_text = stack.enter_context(patch("vibeagent.cli.get_check_switch_text", return_value="Check switch:\n  ok: yes"))
            get_switch_text = stack.enter_context(patch("vibeagent.cli.get_switch_text", return_value="Switch:\n  ok: yes"))
            get_env_text = stack.enter_context(patch("vibeagent.cli.get_env_text", return_value="Environment:\n  tools: 3/9"))
            get_processes_text = stack.enter_context(patch("vibeagent.cli.get_processes_text", return_value="Processes:\n  processes: 0"))
            get_process_text = stack.enter_context(patch("vibeagent.cli.get_process_text", return_value="Process:\n  ok: no"))
            get_process_output_contexts_text = stack.enter_context(patch("vibeagent.cli.get_process_output_contexts_text", return_value="Process output contexts:\n  contexts: 1/1"))
            get_process_output_diagnostics_text = stack.enter_context(patch("vibeagent.cli.get_process_output_diagnostics_text", return_value="Process output diagnostics:\n  diagnostics: 1/1"))
            get_wait_process_text = stack.enter_context(patch("vibeagent.cli.get_wait_process_text", return_value="Wait process:\n  ok: no"))
            get_check_write_process_text = stack.enter_context(patch("vibeagent.cli.get_check_write_process_text", return_value="Check write process:\n  ok: yes"))
            get_write_process_text = stack.enter_context(patch("vibeagent.cli.get_write_process_text", return_value="Write process:\n  ok: no"))
            get_check_stop_process_text = stack.enter_context(patch("vibeagent.cli.get_check_stop_process_text", return_value="Check stop process:\n  ok: yes"))
            get_stop_process_text = stack.enter_context(patch("vibeagent.cli.get_stop_process_text", return_value="Stop process:\n  ok: no"))
            get_check_stop_all_processes_text = stack.enter_context(patch("vibeagent.cli.get_check_stop_all_processes_text", return_value="Check stop processes:\n  processes: 1"))
            get_stop_all_processes_text = stack.enter_context(patch("vibeagent.cli.get_stop_all_processes_text", return_value="Stop processes:\n  stopped: 1"))
            get_session_text = stack.enter_context(patch("vibeagent.cli.get_session_text", return_value="Session: run-1"))
            stack.enter_context(patch("vibeagent.cli.get_last_session_text", return_value="Session: run-1"))
            get_plan_text = stack.enter_context(patch("vibeagent.cli.get_plan_text", return_value="Plan:\n  session: run-1"))
            get_transcript_text = stack.enter_context(patch("vibeagent.cli.get_transcript_text", return_value="Transcript:\n  session: run-1"))
            get_checkpoint_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_text", return_value="Checkpoint:\n  created: yes"))
            get_checkpoints_text = stack.enter_context(patch("vibeagent.cli.get_checkpoints_text", return_value="Checkpoints:\n  total: 1"))
            get_checkpoint_show_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_show_text", return_value="Checkpoint:\n  id: ckpt-1"))
            get_checkpoint_diff_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_diff_text", return_value="Checkpoint diff:\n  id: ckpt-1"))
            get_checkpoint_status_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_status_text", return_value="Checkpoint status:\n  matches: yes"))
            get_check_checkpoint_restore_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_restore_text", return_value="Check checkpoint restore:\n  ok: yes"))
            get_checkpoint_restore_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_restore_text", return_value="Checkpoint restore:\n  restored: yes"))
            get_check_checkpoint_delete_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_delete_text", return_value="Check checkpoint delete:\n  canDelete: yes"))
            get_checkpoint_delete_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_delete_text", return_value="Checkpoint delete:\n  deleted: yes"))
            get_check_checkpoint_prune_text = stack.enter_context(patch("vibeagent.cli.get_check_checkpoint_prune_text", return_value="Check checkpoint prune:\n  deleteCount: 2"))
            get_checkpoint_prune_text = stack.enter_context(patch("vibeagent.cli.get_checkpoint_prune_text", return_value="Checkpoint prune:\n  deleted: 2"))
            stack.enter_context(patch("vibeagent.cli.get_resume_context", return_value=("run-1", "context", "Resume context loaded from session run-1.")))
            stack.enter_context(patch("vibeagent.cli.get_compact_context", return_value=("run-1", "context", "Compacted context loaded from session run-1.")))
            stack.enter_context(patch("vibeagent.cli.get_context_text", return_value="Context:\n  resume: run-1"))
            stack.enter_context(patch("vibeagent.cli.init_project_instructions", return_value="Created AGENTS.md."))
            stack.enter_context(redirect_stdout(stdout))
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Recent sessions:", output)
        self.assertIn("Usage:", output)
        self.assertIn("Cost:", output)
        self.assertIn("Doctor:", output)
        self.assertIn("Config:", output)
        self.assertIn("Review:", output)
        self.assertIn("Handoff:", output)
        self.assertIn("Changes:", output)
        self.assertIn("Diff:", output)
        self.assertIn("Diff hunks:", output)
        self.assertIn("Diff contexts:", output)
        self.assertIn("Tools:", output)
        self.assertIn("Tool: read_file", output)
        self.assertIn("Tool search:", output)
        self.assertIn("Permissions:", output)
        self.assertIn("Checks:", output)
        self.assertIn("Project commands:", output)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        self.assertIn("Run focused test commands:", output)
        self.assertIn("Manifests:", output)
        self.assertIn("Command check:", output)
        self.assertIn("Run:", output)
        self.assertIn("Check run sequence:", output)
        self.assertIn("Run sequence:", output)
        self.assertIn("Check start:", output)
        self.assertIn("Start:", output)
        self.assertIn("Port:", output)
        self.assertIn("HTTP:", output)
        self.assertIn("Overview:", output)
        self.assertIn("Repo map:", output)
        self.assertIn("Search:", output)
        self.assertIn("Search contexts:", output)
        self.assertIn("Glob:", output)
        self.assertIn("Tree:", output)
        self.assertIn("Symbols:", output)
        self.assertIn("File info:", output)
        self.assertIn("Read:", output)
        self.assertIn("Output contexts:", output)
        self.assertIn("Output diagnostics:", output)
        self.assertIn("Python traceback:", output)
        self.assertIn("Read files:", output)
        self.assertIn("Read ranges:", output)
        self.assertIn("Python check:", output)
        self.assertIn("Python dependencies:", output)
        self.assertIn("Python definitions:", output)
        self.assertIn("Python references:", output)
        self.assertIn("Python reference contexts:", output)
        self.assertIn("Python calls:", output)
        self.assertIn("Python call graph:", output)
        self.assertIn("Python rename preview:", output)
        self.assertIn("Python rename:", output)
        self.assertIn("Config check:", output)
        self.assertIn("Check JSON set:", output)
        self.assertIn("JSON set:", output)
        self.assertIn("Check JSON remove:", output)
        self.assertIn("JSON remove:", output)
        self.assertIn("Check write:", output)
        self.assertIn("Write:", output)
        self.assertIn("Check write files:", output)
        self.assertIn("Write files:", output)
        self.assertIn("Check edit:", output)
        self.assertIn("Edit:", output)
        self.assertIn("Check multi edit:", output)
        self.assertIn("Multi edit:", output)
        self.assertIn("Check delete:", output)
        self.assertIn("Delete:", output)
        self.assertIn("Check delete files:", output)
        self.assertIn("Delete files:", output)
        self.assertIn("Check move:", output)
        self.assertIn("Move:", output)
        self.assertIn("Check move files:", output)
        self.assertIn("Move files:", output)
        self.assertIn("Check copy:", output)
        self.assertIn("Copy:", output)
        self.assertIn("Check copy files:", output)
        self.assertIn("Copy files:", output)
        self.assertIn("Check move dir:", output)
        self.assertIn("Move dir:", output)
        self.assertIn("Check move dirs:", output)
        self.assertIn("Move dirs:", output)
        self.assertIn("Check copy dir:", output)
        self.assertIn("Copy dir:", output)
        self.assertIn("Check copy dirs:", output)
        self.assertIn("Copy dirs:", output)
        self.assertIn("Check mkdir:", output)
        self.assertIn("Mkdir:", output)
        self.assertIn("Check mkdirs:", output)
        self.assertIn("Mkdirs:", output)
        self.assertIn("Check rmdir:", output)
        self.assertIn("Rmdir:", output)
        self.assertIn("Check rmdirs:", output)
        self.assertIn("Rmdirs:", output)
        self.assertIn("Check executable:", output)
        self.assertIn("Set executable:", output)
        self.assertIn("Check patch:", output)
        self.assertIn("Patch:", output)
        self.assertIn("Check patches:", output)
        self.assertIn("Patches:", output)
        self.assertIn("Code dependencies:", output)
        self.assertIn("Code references:", output)
        self.assertIn("Code reference contexts:", output)
        self.assertIn("Code definitions:", output)
        self.assertIn("Code rename preview:", output)
        self.assertIn("Code rename:", output)
        self.assertIn("Git status:", output)
        self.assertIn("Git conflicts:", output)
        self.assertIn("Git info:", output)
        self.assertIn("Branches:", output)
        self.assertIn("Log:", output)
        self.assertIn("Show:", output)
        self.assertIn("Blame:", output)
        self.assertIn("Stashes:", output)
        self.assertIn("Check fetch:", output)
        self.assertIn("Fetch:", output)
        self.assertIn("Check pull:", output)
        self.assertIn("Pull:", output)
        self.assertIn("Check push:", output)
        self.assertIn("Push:", output)
        self.assertIn("Check stash:", output)
        self.assertIn("Stash:", output)
        self.assertIn("Check stash apply:", output)
        self.assertIn("Stash apply:", output)
        self.assertIn("Check stash drop:", output)
        self.assertIn("Stash drop:", output)
        self.assertIn("Check stage:", output)
        self.assertIn("Stage:", output)
        self.assertIn("Check unstage:", output)
        self.assertIn("Unstage:", output)
        self.assertIn("Check commit:", output)
        self.assertIn("Commit:", output)
        self.assertIn("Check restore:", output)
        self.assertIn("Restore:", output)
        self.assertIn("Check switch:", output)
        self.assertIn("Switch:", output)
        self.assertIn("Environment:", output)
        self.assertIn("Processes:", output)
        self.assertIn("Process:", output)
        self.assertIn("Process output contexts:", output)
        self.assertIn("Process output diagnostics:", output)
        self.assertIn("Wait process:", output)
        self.assertIn("Write process:", output)
        self.assertIn("Check stop process:", output)
        self.assertIn("Stop process:", output)
        self.assertIn("Check stop processes:", output)
        self.assertIn("Stop processes:", output)
        self.assertIn("Session: run-1", output)
        self.assertIn("Plan:", output)
        self.assertIn("Transcript:", output)
        self.assertIn("Checkpoint:", output)
        self.assertIn("Checkpoints:", output)
        self.assertIn("Checkpoint diff:", output)
        self.assertIn("Checkpoint status:", output)
        self.assertIn("Check checkpoint restore:", output)
        self.assertIn("Checkpoint restore:", output)
        self.assertIn("Check checkpoint delete:", output)
        self.assertIn("Checkpoint delete:", output)
        self.assertIn("Check checkpoint prune:", output)
        self.assertIn("Checkpoint prune:", output)
        self.assertIn("Resume context loaded", output)
        self.assertIn("Compacted context loaded", output)
        self.assertIn("Context:", output)
        self.assertIn("Created AGENTS.md.", output)
        self.assertIn("Cleared chat history and resume context.", output)
        get_session_text.assert_called_once_with("run-1")
        get_plan_text.assert_called_once_with(run_id="run-1")
        get_transcript_text.assert_called_once_with(run_id="run-1")
        get_checkpoint_text.assert_called_once_with(label="before tests")
        get_checkpoints_text.assert_called_once_with()
        get_checkpoint_show_text.assert_called_once_with("ckpt-1")
        get_checkpoint_diff_text.assert_called_once_with("ckpt-1")
        get_checkpoint_status_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_restore_text.assert_called_once_with("ckpt-1")
        get_checkpoint_restore_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_delete_text.assert_called_once_with("ckpt-1")
        get_checkpoint_delete_text.assert_called_once_with("ckpt-1")
        get_check_checkpoint_prune_text.assert_called_once_with("2")
        get_checkpoint_prune_text.assert_called_once_with("2")
        get_diff_text.assert_called_once_with(argument="--staged app.py", max_chars=12000)
        get_diff_hunks_text.assert_called_once_with(argument="--staged app.py")
        get_diff_contexts_text.assert_called_once_with(argument="--staged app.py")
        get_config_text.assert_called_once_with()
        get_handoff_text.assert_called_once_with()
        get_changes_text.assert_called_once_with()
        get_tool_search_text.assert_called_once_with("verification", max_matches=3, category="session", approval_required=False)
        get_permissions_text.assert_called_once_with("ask", Path.cwd())
        get_checks_text.assert_called_once_with()
        get_commands_text.assert_called_once_with()
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py")
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py")
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py")
        get_run_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", timeout_ms=30000, max_output_chars=12000)
        get_manifests_text.assert_called_once_with()
        get_command_check_text.assert_called_once_with(command="python3 --version")
        get_run_text.assert_called_once_with(command="python3 --version")
        get_check_run_sequence_text.assert_called_once_with(argument="python3 --version ;; npm test")
        get_run_sequence_text.assert_called_once_with(argument="python3 --version ;; npm test")
        get_check_start_text.assert_called_once_with(command="npm run dev")
        get_start_text.assert_called_once_with(command="npm run dev")
        get_port_text.assert_called_once_with(argument="5173 127.0.0.1 1500")
        get_http_text.assert_called_once_with(argument="http://127.0.0.1:5173 ready")
        get_http_fetch_text.assert_called_once_with(argument="http://127.0.0.1:5173/app")
        get_overview_text.assert_called_once_with()
        get_repo_map_text.assert_called_once_with(path="src")
        get_search_text.assert_called_once_with(query="needle")
        get_search_contexts_text.assert_called_once_with(query="needle")
        get_glob_text.assert_called_once_with(pattern="**/*.py")
        get_tree_text.assert_called_once_with(path="src")
        get_symbols_text.assert_called_once_with(argument="src/app.py web/app.ts")
        get_file_info_text.assert_called_once_with(argument="src/app.py asset.bin")
        get_image_info_text.assert_called_once_with(argument="assets/logo.png")
        get_read_text.assert_called_once_with(argument="src/app.py 2:4")
        get_around_text.assert_called_once_with(argument="src/app.py 42 8")
        get_around_many_text.assert_called_once_with(argument="src/app.py:42:8 tests/test_app.py:17")
        get_output_contexts_text.assert_called_once_with(text="src/app.py:42:8")
        get_output_diagnostics_text.assert_called_once_with(text="ERROR src/app.py:42:8 failed")
        get_python_traceback_text.assert_called_once_with(text="ValueError: bad")
        get_tail_text.assert_called_once_with(argument="logs/app.log 3")
        get_read_files_text.assert_called_once_with(argument="src/app.py tests/test_app.py")
        get_read_ranges_text.assert_called_once_with(argument="src/app.py:2:4 tests/test_app.py:1")
        get_python_check_text.assert_called_once_with(argument="src")
        get_python_deps_text.assert_called_once_with(argument="src")
        get_python_defs_text.assert_called_once_with(argument="Runner.run src")
        get_python_refs_text.assert_called_once_with(argument="run_agent src")
        get_python_ref_contexts_text.assert_called_once_with(argument="run_agent src")
        get_python_calls_text.assert_called_once_with(argument="helper src")
        get_python_call_graph_text.assert_called_once_with(argument="src")
        get_python_rename_preview_text.assert_called_once_with(argument="run_agent execute_agent src")
        get_python_rename_text.assert_called_once_with(argument="run_agent execute_agent src")
        get_check_replace_python_definition_text.assert_called_once_with(argument="Runner.run '    def run(self):\\n        return 2\\n' src")
        get_replace_python_definition_text.assert_called_once_with(argument="Runner.run '    def run(self):\\n        return 2\\n' src")
        get_config_check_text.assert_called_once_with(argument="pyproject.toml")
        get_check_json_set_text.assert_called_once_with(argument="package.json /private true")
        get_json_set_text.assert_called_once_with(argument="package.json /scripts/test '\"npm test\"'")
        get_check_json_remove_text.assert_called_once_with(argument="package.json /scripts/dev")
        get_json_remove_text.assert_called_once_with(argument="package.json /keywords/0")
        get_check_json_patch_text.assert_called_once_with(argument="package.json '[{\"op\":\"replace\",\"path\":\"/private\",\"value\":true}]'")
        get_json_patch_text.assert_called_once_with(argument="package.json '[{\"op\":\"remove\",\"path\":\"/keywords/0\"}]'")
        get_check_replace_lines_text.assert_called_once_with(argument="app.py 2 3 'new\\n'")
        get_replace_lines_text.assert_called_once_with(argument="app.py 2 2 'new\\n'")
        get_check_insert_lines_text.assert_called_once_with(argument="app.py 2 'new\\n'")
        get_insert_lines_text.assert_called_once_with(argument="app.py 2 'new\\n'")
        get_check_append_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_append_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_check_write_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_write_file_text.assert_called_once_with(argument="app.py 'new\\n'")
        get_check_write_files_text.assert_called_once_with(argument="app.py 'a\\n' test.py 'b\\n'")
        get_write_files_text.assert_called_once_with(argument="app.py 'a\\n' test.py 'b\\n'")
        get_check_edit_file_text.assert_called_once_with(argument="app.py old new")
        get_edit_file_text.assert_called_once_with(argument="app.py old new")
        get_check_multi_edit_file_text.assert_called_once_with(argument="app.py old new print log")
        get_multi_edit_file_text.assert_called_once_with(argument="app.py old new print log")
        get_check_delete_file_text.assert_called_once_with(argument="old.py")
        get_delete_file_text.assert_called_once_with(argument="old.py")
        get_check_delete_files_text.assert_called_once_with(argument="old.py other.py")
        get_delete_files_text.assert_called_once_with(argument="old.py other.py")
        get_check_move_file_text.assert_called_once_with(argument="old.py new.py")
        get_move_file_text.assert_called_once_with(argument="old.py new.py")
        get_check_move_files_text.assert_called_once_with(argument="old.py new.py other.py other-new.py")
        get_move_files_text.assert_called_once_with(argument="old.py new.py other.py other-new.py")
        get_check_copy_file_text.assert_called_once_with(argument="template.py new.py")
        get_copy_file_text.assert_called_once_with(argument="template.py new.py")
        get_check_copy_files_text.assert_called_once_with(argument="template.py new.py config.py config-copy.py")
        get_copy_files_text.assert_called_once_with(argument="template.py new.py config.py config-copy.py")
        get_check_move_dir_text.assert_called_once_with(argument="old_pkg new_pkg")
        get_move_dir_text.assert_called_once_with(argument="old_pkg new_pkg")
        get_check_move_dirs_text.assert_called_once_with(argument="old_a new_a old_b new_b")
        get_move_dirs_text.assert_called_once_with(argument="old_a new_a old_b new_b")
        get_check_copy_dir_text.assert_called_once_with(argument="template_pkg copy_pkg")
        get_copy_dir_text.assert_called_once_with(argument="template_pkg copy_pkg")
        get_check_copy_dirs_text.assert_called_once_with(argument="template_a copy_a template_b copy_b")
        get_copy_dirs_text.assert_called_once_with(argument="template_a copy_a template_b copy_b")
        get_check_create_dir_text.assert_called_once_with(argument="pkg/generated")
        get_create_dir_text.assert_called_once_with(argument="pkg/generated")
        get_check_create_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_create_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_check_delete_empty_dir_text.assert_called_once_with(argument="pkg/generated")
        get_delete_empty_dir_text.assert_called_once_with(argument="pkg/generated")
        get_check_delete_empty_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_delete_empty_dirs_text.assert_called_once_with(argument="pkg/generated assets/icons")
        get_check_set_executable_text.assert_called_once_with(argument="tool.sh false")
        get_set_executable_text.assert_called_once_with(argument="tool.sh true")
        get_check_patch_text.assert_called_once_with(argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_patch_text.assert_called_once_with(argument="app.py '@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_check_patches_text.assert_called_once_with(argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_patches_text.assert_called_once_with(argument="'--- a/app.py\\n+++ b/app.py\\n@@ -1 +1 @@\\n-old\\n+new\\n'")
        get_check_regex_replace_text.assert_called_once_with(argument="--ignore-case app.py old new")
        get_regex_replace_text.assert_called_once_with(argument="--count 1 app.py old new")
        get_code_deps_text.assert_called_once_with(argument="web")
        get_code_refs_text.assert_called_once_with(argument="runAgent web")
        get_code_ref_contexts_text.assert_called_once_with(argument="runAgent web")
        get_code_defs_text.assert_called_once_with(argument="runAgent web")
        get_code_rename_preview_text.assert_called_once_with(argument="runAgent executeAgent web")
        get_code_rename_text.assert_called_once_with(argument="runAgent executeAgent web")
        get_git_status_text.assert_called_once_with()
        get_git_conflicts_text.assert_called_once_with(argument="src")
        get_git_info_text.assert_called_once_with()
        get_branches_text.assert_called_once_with()
        get_log_text.assert_called_once_with(argument="app.py 2")
        get_show_text.assert_called_once_with(argument="HEAD app.py")
        get_blame_text.assert_called_once_with(argument="app.py 2:2")
        get_stashes_text.assert_called_once_with(argument="3")
        get_check_fetch_text.assert_called_once_with(argument="origin")
        get_fetch_text.assert_called_once_with(argument="origin")
        get_check_pull_text.assert_called_once_with()
        get_pull_text.assert_called_once_with()
        get_check_push_text.assert_called_once_with()
        get_push_text.assert_called_once_with()
        get_check_stash_text.assert_called_once_with(argument="--include-untracked save work")
        get_stash_text.assert_called_once_with(argument="save work")
        get_check_stash_apply_text.assert_called_once_with(argument="stash@{0}")
        get_stash_apply_text.assert_called_once_with(argument="stash@{0}")
        get_check_stash_drop_text.assert_called_once_with(argument="stash@{0}")
        get_stash_drop_text.assert_called_once_with(argument="stash@{0}")
        get_check_stage_text.assert_called_once_with(argument="app.py")
        get_stage_text.assert_called_once_with(argument="app.py")
        get_check_unstage_text.assert_called_once_with(argument="app.py")
        get_unstage_text.assert_called_once_with(argument="app.py")
        get_check_commit_text.assert_called_once_with(argument="update app")
        get_commit_text.assert_called_once_with(argument="update app")
        get_check_restore_text.assert_called_once_with(argument="app.py")
        get_restore_text.assert_called_once_with(argument="app.py")
        get_check_switch_text.assert_called_once_with(argument="--create feature/demo")
        get_switch_text.assert_called_once_with(argument="feature/demo")
        get_env_text.assert_called_once_with()
        get_processes_text.assert_called_once_with()
        get_process_text.assert_called_once_with(argument="bg-1 2000")
        get_process_output_contexts_text.assert_called_once_with(process_id="bg-1", max_output_chars=2000)
        get_process_output_diagnostics_text.assert_called_once_with(process_id="bg-1", max_output_chars=2000)
        get_wait_process_text.assert_called_once_with(process_id="bg-1", timeout_ms=5000, max_output_chars=2000)
        get_check_write_process_text.assert_called_once_with(argument="bg-1 hello\\n")
        get_write_process_text.assert_called_once_with(argument="bg-1 hello\\n")
        get_check_stop_process_text.assert_called_once_with(process_id="bg-1")
        get_stop_process_text.assert_called_once_with(process_id="bg-1")
        get_check_stop_all_processes_text.assert_called_once_with()
        get_stop_all_processes_text.assert_called_once_with()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --max-paths 3 --max-candidates 4 --max-commands 5 --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- pkg/actions.py tests/test_actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text", return_value="Run focused test commands:\n  ok: yes") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run focused test commands:", output)
        get_run_focused_test_commands_text.assert_called_once_with(
            argument="pkg/actions.py tests/test_actions.py",
            max_paths=3,
            max_candidates=4,
            max_commands=5,
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_related_and_focused_test_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 3 --max-candidates 4 -- pkg/actions.py",
                    "/focused-tests --max-paths 5 --max-candidates 6 --max-commands 7 -- pkg/actions.py",
                    "/check-focused-tests --max-paths 8 --max-candidates 9 --max-commands 10 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text", return_value="Related tests:\n  candidates: 1/1") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text", return_value="Focused test commands:\n  commands: 1/1") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text", return_value="Check focused test commands:\n  ok: yes") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Related tests:", output)
        self.assertIn("Focused test commands:", output)
        self.assertIn("Check focused test commands:", output)
        get_related_tests_text.assert_called_once_with(argument="pkg/actions.py", max_paths=3, max_candidates=4)
        get_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=5, max_candidates=6, max_commands=7)
        get_check_focused_test_commands_text.assert_called_once_with(argument="pkg/actions.py", max_paths=8, max_candidates=9, max_commands=10)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_test_limit_option_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/related-tests --max-paths 0 -- pkg/actions.py",
                    "/focused-tests --max-commands 0 -- pkg/actions.py",
                    "/check-focused-tests --unknown 1 -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_related_tests_text") as get_related_tests_text,
            patch("vibeagent.cli.get_focused_test_commands_text") as get_focused_test_commands_text,
            patch("vibeagent.cli.get_check_focused_test_commands_text") as get_check_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /related-tests [--max-paths N]", output)
        self.assertIn("--max-paths must be a positive integer.", output)
        self.assertIn("Usage: /focused-tests [--max-paths N]", output)
        self.assertIn("--max-commands must be a positive integer.", output)
        self.assertIn("Usage: /check-focused-tests [--max-paths N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_related_tests_text.assert_not_called()
        get_focused_test_commands_text.assert_not_called()
        get_check_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_focused_test_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-focused-tests --timeout-ms 99 -- pkg/actions.py",
                    "/run-focused-tests --max-bytes 0 -- pkg/actions.py",
                    "/run-focused-tests --output-contexts=true -- pkg/actions.py",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_focused_test_commands_text") as get_run_focused_test_commands_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-focused-tests [--max-paths N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--max-bytes must be a positive integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_focused_test_commands_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 2000 --max-chars 3000 --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument="2",
            timeout_ms=2000,
            max_output_chars=3000,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_suggested_check_named_max_option(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --max-checks 2 --timeout-ms 2000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text", return_value="Run suggested checks:\n  ok: yes") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run suggested checks:", output)
        get_run_suggested_checks_text.assert_called_once_with(
            argument=None,
            max_checks=2,
            timeout_ms=2000,
        )
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_check_suggested_check_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text", return_value="Check suggested checks:\n  ok: yes") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Check suggested checks:", output)
        get_check_suggested_checks_text.assert_called_once_with(max_checks=2)
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_check_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/check-suggested-checks --max-checks 0",
                    "/check-suggested-checks --bad",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_check_suggested_checks_text") as get_check_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /check-suggested-checks [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Unknown option: --bad", output)
        get_check_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_suggested_check_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-suggested-checks --timeout-ms 99 -- 2",
                    "/run-suggested-checks --context-lines -1 -- 2",
                    "/run-suggested-checks --output-diagnostics=true -- 2",
                    "/run-suggested-checks --output-contexts -- 1 2",
                    "/run-suggested-checks --max-checks 1 -- 2",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_suggested_checks_text") as get_run_suggested_checks_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-suggested-checks [--max-checks N]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-diagnostics does not take a value.", output)
        self.assertIn("expected at most one max value.", output)
        self.assertIn("provide either --max-checks or trailing max, not both.", output)
        get_run_suggested_checks_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_run_session_verification_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-session-verification run-1 --max-checks 2 --timeout-ms 2000 --max-output-chars 3000 --no-failed --continue-on-failure --output-contexts --output-diagnostics --context-lines 2 --max-diagnostics 7 --max-contexts 5 --max-bytes 1000",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_session_verification_text", return_value="Run session verification:\n  ok: yes") as get_run_session_verification_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Run session verification:", output)
        get_run_session_verification_text.assert_called_once_with(
            run_id="run-1",
            max_checks=2,
            timeout_ms=2000,
            max_output_chars=3000,
            include_failed=False,
            stop_on_failure=False,
            extract_output_contexts=True,
            extract_output_diagnostics=True,
            context_lines=2,
            max_diagnostics=7,
            max_contexts=5,
            max_bytes_per_context=1000,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_run_session_verification_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/run-session-verification --timeout-ms 99",
                    "/run-session-verification --context-lines -1",
                    "/run-session-verification --output-contexts=true",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_run_session_verification_text") as get_run_session_verification_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /run-session-verification [run-id]", output)
        self.assertIn("--timeout-ms must be at least 100.", output)
        self.assertIn("--context-lines must be a non-negative integer.", output)
        self.assertIn("--output-contexts does not take a value.", output)
        get_run_session_verification_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_preflight_cwd_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/command --cwd src -- python3 --version",
                    "/check-run-seq --cwd src -- python3 --version ;; npm test",
                    "/check-start --cwd web -- npm run dev",
                    "/start --cwd web -- npm run dev",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_command_check_text", return_value="Command check:\n  ok: yes") as get_command_check_text,
            patch("vibeagent.cli.get_check_run_sequence_text", return_value="Check run sequence:\n  ok: yes") as get_check_run_sequence_text,
            patch("vibeagent.cli.get_check_start_text", return_value="Check start:\n  ok: yes") as get_check_start_text,
            patch("vibeagent.cli.get_start_text", return_value="Start:\n  ok: yes") as get_start_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Command check:", output)
        self.assertIn("Check run sequence:", output)
        self.assertIn("Check start:", output)
        self.assertIn("Start:", output)
        get_command_check_text.assert_called_once_with(command="python3 --version", cwd="src")
        get_check_run_sequence_text.assert_called_once_with(commands=["python3 --version", "npm test"], cwd="src")
        get_check_start_text.assert_called_once_with(command="npm run dev", cwd="web")
        get_start_text.assert_called_once_with(command="npm run dev", cwd="web")
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_preflight_cwd_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/command --cwd",
                    "/command --cwd src",
                    "/check-run-seq --cwd src",
                    "/check-start --cwd app --cwd web -- npm run dev",
                    "/start --cwd app --cwd web -- npm run dev",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_command_check_text") as get_command_check_text,
            patch("vibeagent.cli.get_check_run_sequence_text") as get_check_run_sequence_text,
            patch("vibeagent.cli.get_check_start_text") as get_check_start_text,
            patch("vibeagent.cli.get_start_text") as get_start_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /command [--cwd PATH] -- <cmd>", output)
        self.assertIn("--cwd requires a value.", output)
        self.assertIn("command is required.", output)
        self.assertIn("Usage: /check-run-seq [--cwd PATH] -- <cmd> ;; <cmd>", output)
        self.assertIn("at least one command is required.", output)
        self.assertIn("Usage: /check-start [--cwd PATH] -- <cmd>", output)
        self.assertIn("Usage: /start [--cwd PATH] -- <cmd>", output)
        self.assertIn("--cwd can only be provided once.", output)
        get_command_check_text.assert_not_called()
        get_check_run_sequence_text.assert_not_called()
        get_check_start_text.assert_not_called()
        get_start_text.assert_not_called()
        create_chat_client.assert_not_called()

    def test_main_parses_interactive_session_detail_limit_options(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-verification run-1 --max-checks 2",
                    "/session-commands run-1 --max-commands 2 --max-output-chars 0",
                    "/session-files run-1 --max-files 3",
                    "/session-failures run-1 --max-failures 4 --max-text 80",
                    "/session-audit run-1 --max-failures 5 --max-files 6 --max-commands 7 --max-checks 8 --max-text 90",
                    "/session-handoff run-1 --max-failures 8 --max-files 9 --max-commands 10 --max-checks 11 --max-output-chars 0 --max-text 100",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_verification_text", return_value="Session verification:\n  session: run-1") as get_session_verification_text,
            patch("vibeagent.cli.get_session_commands_text", return_value="Command results:\n  session: run-1") as get_session_commands_text,
            patch("vibeagent.cli.get_session_files_text", return_value="Session files:\n  session: run-1") as get_session_files_text,
            patch("vibeagent.cli.get_session_failures_text", return_value="Session failures:\n  session: run-1") as get_session_failures_text,
            patch("vibeagent.cli.get_session_audit_text", return_value="Session audit:\n  session: run-1") as get_session_audit_text,
            patch("vibeagent.cli.get_session_handoff_text", return_value="Session handoff:\n  session: run-1") as get_session_handoff_text,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Session verification:", output)
        self.assertIn("Command results:", output)
        self.assertIn("Session files:", output)
        self.assertIn("Session failures:", output)
        self.assertIn("Session audit:", output)
        self.assertIn("Session handoff:", output)
        get_session_verification_text.assert_called_once_with(run_id="run-1", max_checks=2)
        get_session_commands_text.assert_called_once_with(run_id="run-1", max_commands=2, max_output_chars=0)
        get_session_files_text.assert_called_once_with(run_id="run-1", max_files=3)
        get_session_failures_text.assert_called_once_with(run_id="run-1", max_failures=4, max_text=80)
        get_session_audit_text.assert_called_once_with(
            run_id="run-1",
            max_failures=5,
            max_files=6,
            max_commands=7,
            max_checks=8,
            max_text=90,
        )
        get_session_handoff_text.assert_called_once_with(
            run_id="run-1",
            max_failures=8,
            max_files=9,
            max_commands=10,
            max_checks=11,
            max_output_chars=0,
            max_text=100,
        )
        create_chat_client.assert_not_called()

    def test_main_reports_interactive_session_detail_limit_errors(self) -> None:
        stdout = io.StringIO()

        with (
            patch(
                "builtins.input",
                side_effect=[
                    "/session-verification --max-checks 0",
                    "/session-commands --max-output-chars -1",
                    "/session-files --max-files 0",
                    "/session-audit --max-checks 0",
                    "/session-handoff --max-checks 0",
                    "/session-handoff --unknown run-1",
                    "/resume --max-checks 0",
                    "/resume --max-output-chars -1",
                    "/compact --max-checks 0",
                    "/compact --max-output-chars -1",
                    "/exit",
                ],
            ),
            patch("vibeagent.cli.create_chat_client") as create_chat_client,
            patch("vibeagent.cli.get_session_verification_text") as get_session_verification_text,
            patch("vibeagent.cli.get_session_commands_text") as get_session_commands_text,
            patch("vibeagent.cli.get_session_files_text") as get_session_files_text,
            patch("vibeagent.cli.get_session_handoff_text") as get_session_handoff_text,
            patch("vibeagent.cli.get_resume_context") as get_resume_context,
            patch("vibeagent.cli.get_compact_context") as get_compact_context,
            redirect_stdout(stdout),
        ):
            exit_code = main()

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage: /session-verification [run-id] [--max-checks N]", output)
        self.assertIn("--max-checks must be a positive integer.", output)
        self.assertIn("Usage: /session-commands [run-id] [--max-commands N] [--max-output-chars N]", output)
        self.assertIn("--max-output-chars must be a non-negative integer.", output)
        self.assertIn("Usage: /session-files [run-id] [--max-files N]", output)
        self.assertIn("--max-files must be a positive integer.", output)
        self.assertIn("Usage: /session-audit [run-id]", output)
        self.assertIn("Usage: /session-handoff [run-id]", output)
        self.assertIn("Usage: /resume [run-id|off] [--max-failures N]", output)
        self.assertIn("Usage: /compact [run-id] [--max-failures N]", output)
        self.assertIn("Unknown option: --unknown", output)
        get_session_verification_text.assert_not_called()
        get_session_commands_text.assert_not_called()
        get_session_files_text.assert_not_called()
        get_session_handoff_text.assert_not_called()
        get_resume_context.assert_not_called()
        get_compact_context.assert_not_called()
        create_chat_client.assert_not_called()

if __name__ == "__main__":
    unittest.main()
