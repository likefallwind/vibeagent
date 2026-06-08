import tempfile
import unittest
import subprocess
from pathlib import Path

from vibeagent.workspace import (
    build_repo_map,
    check_python_syntax,
    check_project_patch,
    check_project_patches,
    create_run_workspace,
    delete_project_file,
    edit_project_file,
    inspect_python_call_graph,
    find_python_calls,
    find_python_definitions,
    find_python_references,
    glob_project_files,
    inspect_python_dependencies,
    insert_project_file_lines,
    list_project_files,
    list_project_tree,
    move_project_file,
    multi_edit_project_file,
    patch_project_file,
    patch_project_files,
    read_project_command_hints,
    read_git_changes,
    read_git_blame,
    read_git_diff,
    read_git_log,
    read_git_show,
    read_git_status,
    read_project_file_info,
    read_project_instructions,
    read_project_file,
    read_python_symbol_outline,
    replace_python_definition,
    replace_project_file_lines,
    review_project_changes,
    resolve_inside_run,
    resolve_command_cwd,
    search_project,
    suggest_project_checks,
    write_run_file,
    write_run_files,
)


class WorkspaceTests(unittest.TestCase):
    def test_resolve_inside_run_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "Absolute paths"):
                resolve_inside_run(workspace.root, "/tmp/file.py")

    def test_resolve_inside_run_rejects_parent_directory_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_inside_run(workspace.root, "../file.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_inside_run(workspace.root, "nested/../../file.py")

    def test_write_run_file_writes_inside_the_run_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            target = write_run_file(workspace, "nested/hello.txt", "hello")

            self.assertEqual(workspace.root, Path(base).resolve())
            self.assertEqual(workspace.session_dir, Path(base).resolve() / ".vibeagent" / "sessions" / "test-run")
            self.assertEqual(target, workspace.root / "nested" / "hello.txt")
            self.assertEqual(Path(target).read_text(encoding="utf-8"), "hello")

    def test_write_run_files_writes_multiple_files_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "existing.txt", "old\n")

            written = write_run_files(
                workspace,
                [
                    ("existing.txt", "new\n"),
                    ("pkg/app.py", "print('ok')\n"),
                ],
            )

            with self.assertRaisesRegex(ValueError, "Path is protected"):
                write_run_files(
                    workspace,
                    [
                        ("existing.txt", "bad\n"),
                        (".vibeagent/secret.txt", "no\n"),
                    ],
                )

            with self.assertRaisesRegex(ValueError, "Duplicate file path"):
                write_run_files(workspace, [("dup.txt", "one\n"), ("dup.txt", "two\n")])

            self.assertEqual([path.relative_to(workspace.root).as_posix() for path in written], ["existing.txt", "pkg/app.py"])
            self.assertEqual((workspace.root / "existing.txt").read_text(encoding="utf-8"), "new\n")
            self.assertEqual((workspace.root / "pkg/app.py").read_text(encoding="utf-8"), "print('ok')\n")
            self.assertFalse((workspace.root / ".vibeagent" / "secret.txt").exists())

    def test_project_helpers_read_search_and_edit_inside_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            files, total = list_project_files(workspace)
            self.assertEqual(files, ["app.py"])
            self.assertEqual(total, 1)
            self.assertIn("name = 'old'", read_project_file(workspace, "app.py"))
            self.assertEqual(read_project_file(workspace, "app.py", start_line=2, line_count=1), "2: print(name)")
            self.assertEqual(search_project(workspace, "print"), ["app.py:2: print(name)"])
            Path(base, "asset.bin").write_bytes(b"\x00\x01")

            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                read_project_file(workspace, "asset.bin")

            _, diff = edit_project_file(workspace, "app.py", "old", "new")

            self.assertIn("-name = 'old'", diff)
            self.assertIn("+name = 'new'", diff)
            self.assertIn("name = 'new'", read_project_file(workspace, "app.py"))

    def test_multi_edit_project_file_applies_replacements_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            _, diff = multi_edit_project_file(
                workspace,
                "app.py",
                [("old", "new"), ("print(name)", "print(name.upper())")],
            )

            with self.assertRaisesRegex(ValueError, "Edit 2 old text was not found"):
                multi_edit_project_file(workspace, "app.py", [("new", "changed"), ("missing", "value")])

            content = read_project_file(workspace, "app.py")

        self.assertEqual(content, "name = 'new'\nprint(name.upper())\n")
        self.assertIn("+print(name.upper())", diff)

    def test_replace_project_file_lines_replaces_inclusive_range(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\ntwo\nthree\nfour\n")

            _, diff = replace_project_file_lines(workspace, "app.py", 2, 3, "TWO\nTHREE")

            with self.assertRaisesRegex(ValueError, "end_line must be greater"):
                replace_project_file_lines(workspace, "app.py", 3, 2, "bad\n")
            with self.assertRaisesRegex(ValueError, "exceeds file line count"):
                replace_project_file_lines(workspace, "app.py", 4, 5, "bad\n")
            with self.assertRaisesRegex(ValueError, "made no changes"):
                replace_project_file_lines(workspace, "app.py", 2, 3, "TWO\nTHREE\n")

            _, delete_diff = replace_project_file_lines(workspace, "app.py", 2, 2, "")
            content = read_project_file(workspace, "app.py")

        self.assertIn("-two", diff)
        self.assertIn("+TWO", diff)
        self.assertEqual(content, "one\nTHREE\nfour\n")
        self.assertIn("-TWO", delete_diff)

    def test_insert_project_file_lines_inserts_before_line_or_appends(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\nthree\n")

            _, diff = insert_project_file_lines(workspace, "app.py", 2, "two")
            _, append_diff = insert_project_file_lines(workspace, "app.py", 4, "four\n")

            with self.assertRaisesRegex(ValueError, "content must not be empty"):
                insert_project_file_lines(workspace, "app.py", 1, "")
            with self.assertRaisesRegex(ValueError, "exceeds append position"):
                insert_project_file_lines(workspace, "app.py", 6, "bad\n")

            content = read_project_file(workspace, "app.py")

        self.assertEqual(content, "one\ntwo\nthree\nfour\n")
        self.assertIn("+two", diff)
        self.assertIn("+four", append_diff)

    def test_read_project_file_info_reports_text_binary_directory_and_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "one\ntwo\n")
            Path(base, "asset.bin").write_bytes(b"\x00\x01")
            Path(base, "pkg").mkdir()

            text = read_project_file_info(workspace, "app.py")
            binary = read_project_file_info(workspace, "asset.bin")
            directory = read_project_file_info(workspace, "pkg")
            missing = read_project_file_info(workspace, "missing.py")

            with self.assertRaisesRegex(ValueError, "protected"):
                read_project_file_info(workspace, ".vibeagent")

        self.assertTrue(text["ok"])
        self.assertEqual(text["size_bytes"], 8)
        self.assertEqual(text["line_count"], 2)
        self.assertFalse(text["is_binary"])
        self.assertTrue(binary["is_binary"])
        self.assertTrue(directory["is_dir"])
        self.assertFalse(missing["ok"])
        self.assertFalse(missing["exists"])

    def test_read_python_symbol_outline_reports_imports_and_nested_definitions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "app.py",
                (
                    "import os\n"
                    "from pathlib import Path\n\n"
                    "class App:\n"
                    "    def run(self):\n"
                    "        def inner():\n"
                    "            return Path.cwd()\n"
                    "        return inner()\n\n"
                    "async def main():\n"
                    "    return App().run()\n"
                ),
            )
            write_run_file(workspace, "bad.py", "def broken(:\n")
            write_run_file(workspace, "note.txt", "plain\n")

            outline = read_python_symbol_outline(workspace, "app.py")

            with self.assertRaisesRegex(ValueError, "not a Python source file"):
                read_python_symbol_outline(workspace, "note.txt")
            with self.assertRaisesRegex(ValueError, "Python syntax error"):
                read_python_symbol_outline(workspace, "bad.py")

        self.assertIn("1: import os", outline["imports"])
        self.assertIn("2: from pathlib import Path", outline["imports"])
        self.assertEqual(
            [(item["kind"], item["name"], item["line"], item["parent"]) for item in outline["symbols"]],
            [
                ("class", "App", 4, None),
                ("function", "run", 5, "App"),
                ("function", "inner", 6, "App.run"),
                ("async_function", "main", 10, None),
            ],
        )

    def test_check_python_syntax_reports_errors_and_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "def ok():\n    return 1\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "tests/test_app.py", "def test_ok():\n    assert True\n")
            write_run_file(workspace, "note.txt", "def ignored(:\n")

            results, total = check_python_syntax(workspace)
            scoped, scoped_total = check_python_syntax(workspace, "tests")
            limited, limited_total = check_python_syntax(workspace, max_files=1)

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                check_python_syntax(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "escapes"):
                check_python_syntax(workspace, "../outside")

        self.assertEqual(total, 3)
        self.assertEqual([(item["path"], item["ok"]) for item in results], [("src/app.py", True), ("src/bad.py", False), ("tests/test_app.py", True)])
        self.assertEqual(results[1]["line"], 1)
        self.assertIn("Python syntax error", results[1]["message"])
        self.assertEqual(scoped_total, 1)
        self.assertEqual(scoped[0]["path"], "tests/test_app.py")
        self.assertEqual(limited_total, 3)
        self.assertEqual(len(limited), 1)

    def test_inspect_python_dependencies_classifies_local_and_external_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/__init__.py", "")
            write_run_file(workspace, "pkg/util.py", "VALUE = 1\n")
            write_run_file(
                workspace,
                "pkg/app.py",
                (
                    "import os\n"
                    "import pkg.util as util\n"
                    "from .util import VALUE\n"
                    "from pathlib import Path\n"
                ),
            )
            write_run_file(workspace, "pkg/bad.py", "def broken(:\n")

            results, total = inspect_python_dependencies(workspace, "pkg")
            limited, limited_total = inspect_python_dependencies(workspace, "pkg", max_files=1)

            with self.assertRaisesRegex(ValueError, "max_imports must be at most 2000"):
                inspect_python_dependencies(workspace, max_imports=2001)
            with self.assertRaisesRegex(ValueError, "escapes"):
                inspect_python_dependencies(workspace, "../outside")

        self.assertEqual(total, 4)
        files = {item["path"]: item for item in results}
        self.assertTrue(files["pkg/app.py"]["ok"])
        self.assertEqual(files["pkg/app.py"]["module"], "pkg.app")
        self.assertIn("pkg.util", files["pkg/app.py"]["local_modules"])
        self.assertIn("os", files["pkg/app.py"]["external_modules"])
        self.assertIn("pathlib", files["pkg/app.py"]["external_modules"])
        self.assertEqual([(item["target"], item["local"]) for item in files["pkg/app.py"]["imports"]], [("os", False), ("pkg.util", True), ("pkg.util", True), ("pathlib", False)])
        self.assertFalse(files["pkg/bad.py"]["ok"])
        self.assertIn("Python syntax error", files["pkg/bad.py"]["message"])
        self.assertEqual(limited_total, 4)
        self.assertEqual(len(limited), 1)

    def test_find_python_definitions_returns_focused_source_excerpts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "class Runner:\n"
                    "    def run(self):\n"
                    "        value = 1\n"
                    "        return value\n\n"
                    "def run(task):\n"
                    "    return task\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            definitions, total, errors = find_python_definitions(workspace, "Runner.run", "src", max_lines=2)
            unqualified, unqualified_total, _ = find_python_definitions(workspace, "run", "src/app.py")

            with self.assertRaisesRegex(ValueError, "valid identifier"):
                find_python_definitions(workspace, "bad-name")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 200"):
                find_python_definitions(workspace, "run", max_matches=201)

        self.assertEqual(total, 1)
        self.assertEqual(definitions[0]["qualified_name"], "Runner.run")
        self.assertEqual(definitions[0]["line"], 2)
        self.assertEqual(definitions[0]["end_line"], 4)
        self.assertTrue(definitions[0]["truncated"])
        self.assertIn("2:     def run", definitions[0]["content"])
        self.assertIn("Python syntax error in src/bad.py", errors[0])
        self.assertEqual(unqualified_total, 2)
        self.assertEqual([item["qualified_name"] for item in unqualified], ["Runner.run", "run"])

    def test_replace_python_definition_replaces_unique_symbol_and_validates_syntax(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "class Runner:\n"
                    "    def run(self):\n"
                    "        return 'old'\n\n"
                    "def run(task):\n"
                    "    return task\n"
                ),
            )

            target, diff, definition = replace_python_definition(
                workspace,
                "Runner.run",
                "    def run(self):\n        return 'new'\n",
                "src/app.py",
            )

            with self.assertRaisesRegex(ValueError, "ambiguous"):
                replace_python_definition(workspace, "run", "def run(task):\n    return task\n", "src/app.py")
            with self.assertRaisesRegex(ValueError, "syntax error"):
                replace_python_definition(workspace, "Runner.run", "    def run(self):\n        return (\n", "src/app.py")

            content = read_project_file(workspace, "src/app.py")

        self.assertEqual(target, workspace.root / "src" / "app.py")
        self.assertEqual(definition["qualified_name"], "Runner.run")
        self.assertIn("-        return 'old'", diff)
        self.assertIn("+        return 'new'", diff)
        self.assertIn("return 'new'", content)

    def test_find_python_calls_reports_call_sites_and_callers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
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
                    "    def other(self):\n"
                    "        return self.call()\n\n"
                    "value = Runner().call()\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            calls, total, errors = find_python_calls(workspace, "call", "src")
            run_calls, run_total, _ = find_python_calls(workspace, "run_agent", "src/app.py")

            with self.assertRaisesRegex(ValueError, "valid identifier"):
                find_python_calls(workspace, "bad-name")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 500"):
                find_python_calls(workspace, "run_agent", max_matches=501)

        self.assertEqual(total, 2)
        self.assertEqual(
            [(item["path"], item["line"], item["callee"], item["caller"], item["context"]) for item in calls],
            [
                ("src/app.py", 9, "self.call", "Runner.other", "return self.call()"),
                ("src/app.py", 11, "Runner.call", None, "value = Runner().call()"),
            ],
        )
        self.assertEqual(run_total, 1)
        self.assertEqual(run_calls[0]["callee"], "run_agent")
        self.assertEqual(run_calls[0]["caller"], "Runner.call")
        self.assertIn("Python syntax error in src/bad.py", errors[0])

    def test_inspect_python_call_graph_reports_edges_and_file_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "def helper():\n"
                    "    return 1\n\n"
                    "async def fetch(client):\n"
                    "    return client.get('/x')\n\n"
                    "class Runner:\n"
                    "    def run(self):\n"
                    "        return helper()\n\n"
                    "    def build(self):\n"
                    "        return Runner().run()\n\n"
                    "value = Runner().build()\n"
                ),
            )
            write_run_file(workspace, "src/bad.py", "def broken(:\n")

            edges, total, total_files, errors = inspect_python_call_graph(workspace, "src", max_edges=4)
            limited, limited_total, limited_files, _ = inspect_python_call_graph(workspace, "src", max_files=1)

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                inspect_python_call_graph(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "max_edges must be at most 2000"):
                inspect_python_call_graph(workspace, max_edges=2001)

        self.assertEqual(total_files, 2)
        self.assertEqual(total, 6)
        self.assertEqual(len(edges), 4)
        self.assertEqual(
            {(item["callee"], item["caller"]) for item in edges},
            {("client.get", "fetch"), ("helper", "Runner.run"), ("Runner", "Runner.build"), ("Runner.run", "Runner.build")},
        )
        self.assertIn("Python syntax error in src/bad.py", errors[0])
        self.assertEqual(limited_files, 2)
        self.assertEqual(limited_total, 6)
        self.assertEqual(len(limited), 6)

    def test_find_python_references_reports_ast_matches_and_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(
                workspace,
                "src/app.py",
                (
                    "from helpers import run_agent\n\n"
                    "def run_agent(task):\n"
                    "    return task\n\n"
                    "class Runner:\n"
                    "    def call(self):\n"
                    "        return self.run_agent('x')\n\n"
                    "result = run_agent('task')\n"
                ),
            )
            write_run_file(workspace, "tests/test_app.py", "from src.app import run_agent\nvalue = run_agent('t')\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "note.txt", "run_agent in text\n")

            matches, total, errors = find_python_references(workspace, "run_agent", max_matches=4)
            scoped, scoped_total, scoped_errors = find_python_references(workspace, "run_agent", relative_path="tests")

            with self.assertRaisesRegex(ValueError, "valid identifier"):
                find_python_references(workspace, "not-valid")
            with self.assertRaisesRegex(ValueError, "max_matches must be at most 500"):
                find_python_references(workspace, "run_agent", max_matches=501)

        self.assertEqual(
            [(item["path"], item["line"], item["kind"], item["context"]) for item in matches],
            [
                ("src/app.py", 1, "import", "from helpers import run_agent"),
                ("src/app.py", 3, "definition", "def run_agent(task):"),
                ("src/app.py", 8, "reference", "return self.run_agent('x')"),
                ("src/app.py", 10, "reference", "result = run_agent('task')"),
            ],
        )
        self.assertEqual(total, 6)
        self.assertEqual(len(errors), 1)
        self.assertIn("Python syntax error in src/bad.py", errors[0])
        self.assertEqual(scoped_total, 2)
        self.assertFalse(scoped_errors)
        self.assertEqual([item["path"] for item in scoped], ["tests/test_app.py", "tests/test_app.py"])

    def test_read_project_instructions_reads_scoped_agents_md_with_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            self.assertIsNone(read_project_instructions(workspace))

            write_run_file(workspace, "AGENTS.md", "Use Python.\n")
            write_run_file(workspace, "pkg/AGENTS.md", "Use unittest in this package.\n")
            write_run_file(workspace, "empty/AGENTS.md", "\n")
            short = read_project_instructions(workspace)
            bounded = read_project_instructions(workspace, max_bytes=40)

        self.assertIn("File: AGENTS.md", short or "")
        self.assertIn("Scope: .", short or "")
        self.assertIn("Use Python.", short or "")
        self.assertIn("File: pkg/AGENTS.md", short or "")
        self.assertIn("Scope: pkg", short or "")
        self.assertIn("Use unittest in this package.", short or "")
        self.assertNotIn("empty/AGENTS.md", short or "")
        self.assertTrue((bounded or "").endswith("[AGENTS.md instructions truncated]"))

    def test_read_project_command_hints_reads_common_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            self.assertIsNone(read_project_command_hints(workspace))

            write_run_file(
                workspace,
                "package.json",
                '{"scripts":{"test":"python3 -m unittest discover -s tests","build":"python3 -m compileall -q vibeagent"}}',
            )
            write_run_file(
                workspace,
                "apps/web/package.json",
                '{"scripts":{"test":"vitest","dev":"vite --host 0.0.0.0"}}',
            )
            write_run_file(
                workspace,
                "pyproject.toml",
                '[project]\n[project.scripts]\nvibeagent = "vibeagent.cli:main"\n',
            )
            write_run_file(workspace, "apps/api/Makefile", "test:\n\tpytest\n")
            write_run_file(workspace, "node_modules/pkg/package.json", '{"scripts":{"test":"ignored"}}')
            write_run_file(workspace, "Makefile", "test:\n\tpython3 -m unittest\n.PHONY: test\nbuild:\n\tpython3 -m compileall\n")
            hints = read_project_command_hints(workspace)
            bounded = read_project_command_hints(workspace, max_bytes=50)

        self.assertIn("File: package.json", hints or "")
        self.assertIn("Cwd: .", hints or "")
        self.assertIn("package.json scripts:", hints or "")
        self.assertIn("npm run test: python3 -m unittest discover -s tests", hints or "")
        self.assertIn("File: apps/web/package.json", hints or "")
        self.assertIn("Cwd: apps/web", hints or "")
        self.assertIn("npm run dev: vite --host 0.0.0.0", hints or "")
        self.assertIn("pyproject.toml console scripts:", hints or "")
        self.assertIn("vibeagent: vibeagent.cli:main", hints or "")
        self.assertIn("Makefile targets:", hints or "")
        self.assertIn("make build", hints or "")
        self.assertIn("File: apps/api/Makefile", hints or "")
        self.assertIn("Cwd: apps/api", hints or "")
        self.assertNotIn("ignored", hints or "")
        self.assertTrue((bounded or "").endswith("[project command hints truncated]"))

    def test_suggest_project_checks_uses_metadata_tests_and_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            root = Path(base)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            workspace = create_run_workspace(root, "test-run")
            write_run_file(
                workspace,
                "package.json",
                '{"scripts":{"test":"node test.js","build":"vite build","dev":"vite"}}',
            )
            write_run_file(workspace, "pkg/__init__.py", "")
            write_run_file(workspace, "tests/test_app.py", "def test_ok():\n    assert True\n")
            write_run_file(workspace, "Makefile", "lint:\n\tpython -m compileall pkg\nserve:\n\tpython -m http.server\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "initial"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            write_run_file(workspace, "pkg/app.py", "value = 1\n")

            suggestions = suggest_project_checks(workspace, max_commands=3)
            all_suggestions = suggest_project_checks(workspace)

            with self.assertRaisesRegex(ValueError, "max_commands must be at most 100"):
                suggest_project_checks(workspace, max_commands=101)

        self.assertTrue(suggestions["ok"])
        self.assertTrue(suggestions["truncated"])
        self.assertEqual(len(suggestions["checks"]), 3)
        commands = {(item["cwd"], item["command"]) for item in all_suggestions["checks"]}
        self.assertIn((".", "npm run test"), commands)
        self.assertIn((".", "npm run build"), commands)
        self.assertIn((".", "make lint"), commands)
        self.assertIn((".", "python -m unittest discover -s tests"), commands)
        self.assertIn((".", "python -m compileall -q pkg"), commands)
        self.assertNotIn((".", "npm run dev"), commands)
        self.assertNotIn((".", "make serve"), commands)
        self.assertIn("pkg/app.py", all_suggestions["changed_files"])

    def test_resolve_command_cwd_allows_only_project_directories(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "pkg/app.py", "print('ok')\n")

            cwd = resolve_command_cwd(workspace, "pkg")

            self.assertEqual(cwd, workspace.root / "pkg")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                resolve_command_cwd(workspace, "pkg/app.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                resolve_command_cwd(workspace, "../outside")
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_command_cwd(workspace, ".vibeagent")

    def test_search_project_supports_scope_regex_and_case_options(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "def HandleEvent():\n    return 1\n")
            write_run_file(workspace, "tests/test_app.py", "def test_handle_event():\n    return 2\n")
            Path(base, "src", "asset.bin").write_bytes(b"\x00def\xff")

            scoped = search_project(workspace, "def", relative_path="src")
            insensitive = search_project(workspace, "handleevent", case_sensitive=False)
            regex = search_project(workspace, r"def\s+\w+Event", regex=True, relative_path="src/app.py")
            contextual = search_project(workspace, "return 1", relative_path="src/app.py", context_lines=1)

            with self.assertRaisesRegex(ValueError, "Invalid regex"):
                search_project(workspace, "(", regex=True)
            with self.assertRaisesRegex(ValueError, "context_lines must be at most 5"):
                search_project(workspace, "def", context_lines=6)

        self.assertEqual(scoped, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(insensitive, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(regex, ["src/app.py:1: def HandleEvent():"])
        self.assertEqual(contextual, ["src/app.py:1:  def HandleEvent():\nsrc/app.py:2:>     return 1"])

    def test_glob_project_files_matches_relative_patterns_and_ignores_generated_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "print('app')\n")
            write_run_file(workspace, "tests/test_app.py", "def test_app(): pass\n")
            write_run_file(workspace, "node_modules/pkg/index.py", "ignored\n")
            (Path(base) / ".vibeagent" / "local.py").write_text("ignored\n", encoding="utf-8")

            matches, total = glob_project_files(workspace, "**/*.py", max_matches=1)

        self.assertEqual(matches, ["src/app.py"])
        self.assertEqual(total, 2)

    def test_glob_project_files_rejects_unsafe_patterns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "Absolute paths"):
                glob_project_files(workspace, "/tmp/*.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                glob_project_files(workspace, "../*.py")
            with self.assertRaisesRegex(ValueError, "protected"):
                glob_project_files(workspace, ".git/*")

    def test_list_project_tree_reports_hierarchy_and_ignores_generated_dirs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "src/app.py", "print('app')\n")
            write_run_file(workspace, "src/pkg/mod.py", "value = 1\n")
            write_run_file(workspace, "tests/test_app.py", "def test_app(): pass\n")
            write_run_file(workspace, "node_modules/pkg/index.py", "ignored\n")
            (Path(base) / ".vibeagent" / "local.py").write_text("ignored\n", encoding="utf-8")

            shallow, shallow_total = list_project_tree(workspace, max_depth=1)
            deeper, deeper_total = list_project_tree(workspace, max_depth=3, max_entries=3)
            src_tree, src_total = list_project_tree(workspace, "src", max_depth=2)
            file_tree, file_total = list_project_tree(workspace, "src/app.py")

        self.assertEqual(shallow, ["src/", "tests/"])
        self.assertEqual(shallow_total, 2)
        self.assertEqual(deeper, ["src/", "src/app.py", "src/pkg/"])
        self.assertEqual(deeper_total, 6)
        self.assertEqual(src_tree, ["src/app.py", "src/pkg/", "src/pkg/mod.py"])
        self.assertEqual(src_total, 3)
        self.assertEqual(file_tree, ["src/app.py"])
        self.assertEqual(file_total, 1)

    def test_list_project_tree_rejects_invalid_bounds_and_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "max_depth must be at least 1"):
                list_project_tree(workspace, max_depth=0)
            with self.assertRaisesRegex(ValueError, "max_depth must be at most 10"):
                list_project_tree(workspace, max_depth=11)
            with self.assertRaisesRegex(ValueError, "max_entries must be at least 1"):
                list_project_tree(workspace, max_entries=0)
            with self.assertRaisesRegex(ValueError, "max_entries must be at most 1000"):
                list_project_tree(workspace, max_entries=1001)
            with self.assertRaisesRegex(ValueError, "escapes"):
                list_project_tree(workspace, "../outside")
            with self.assertRaisesRegex(ValueError, "protected"):
                list_project_tree(workspace, ".vibeagent")

    def test_build_repo_map_reports_tree_files_and_python_symbols(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "README.md", "# Demo\n")
            write_run_file(workspace, "src/app.py", "import os\n\nclass App:\n    def run(self):\n        return os.getcwd()\n")
            write_run_file(workspace, "src/util.py", "def helper():\n    return 1\n")
            write_run_file(workspace, "src/bad.py", "def broken(:\n")
            write_run_file(workspace, "node_modules/pkg/index.py", "ignored\n")

            repo_map = build_repo_map(workspace, max_depth=2, max_files=10, max_symbols=10)
            scoped = build_repo_map(workspace, "src", max_depth=1, max_files=2, max_symbols=10)

            with self.assertRaisesRegex(ValueError, "max_files must be at most 500"):
                build_repo_map(workspace, max_files=501)
            with self.assertRaisesRegex(ValueError, "protected"):
                build_repo_map(workspace, ".vibeagent")

        self.assertEqual(repo_map["path"], ".")
        self.assertEqual(repo_map["tree"], ["README.md", "src/", "src/app.py", "src/bad.py", "src/util.py"])
        self.assertEqual(repo_map["files"], ["README.md", "src/app.py", "src/bad.py", "src/util.py"])
        python_files = repo_map["python_files"]
        self.assertEqual([item["path"] for item in python_files], ["src/app.py", "src/bad.py", "src/util.py"])
        self.assertTrue(python_files[0]["ok"])
        self.assertEqual([(item["kind"], item["name"]) for item in python_files[0]["symbols"]], [("class", "App"), ("function", "run")])
        self.assertFalse(python_files[1]["ok"])
        self.assertIn("Python syntax error", python_files[1]["message"])
        self.assertEqual(scoped["path"], "src")
        self.assertEqual(scoped["files"], ["src/app.py", "src/bad.py"])
        self.assertEqual(scoped["total_files"], 3)
        self.assertTrue(scoped["truncated"])

    def test_patch_project_file_applies_unified_diff_hunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            _, diff = patch_project_file(
                workspace,
                "app.py",
                "@@ -1,2 +1,3 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                "+count = 1\n"
                " print(name)\n",
            )

            content = read_project_file(workspace, "app.py")
        self.assertEqual(content, "name = 'new'\ncount = 1\nprint(name)\n")
        self.assertIn("+count = 1", diff)

    def test_patch_project_file_rejects_mismatched_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'actual'\nprint(name)\n")

            with self.assertRaisesRegex(ValueError, "context did not match"):
                patch_project_file(
                    workspace,
                    "app.py",
                    "@@ -1,2 +1,2 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n"
                    " print(name)\n",
                )

            self.assertEqual(read_project_file(workspace, "app.py"), "name = 'actual'\nprint(name)\n")

    def test_check_project_patch_validates_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")

            path, diff = check_project_patch(
                workspace,
                "app.py",
                "@@ -1,2 +1,2 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                " print(name)\n",
            )
            content = read_project_file(workspace, "app.py")

            with self.assertRaisesRegex(ValueError, "context did not match"):
                check_project_patch(
                    workspace,
                    "app.py",
                    "@@ -1,2 +1,2 @@\n"
                    "-name = 'missing'\n"
                    "+name = 'new'\n"
                    " print(name)\n",
                )

        self.assertEqual(path.name, "app.py")
        self.assertIn("+name = 'new'", diff)
        self.assertEqual(content, "name = 'old'\nprint(name)\n")

    def test_patch_project_files_applies_multi_file_patch_atomically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            paths, diff = patch_project_files(
                workspace,
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1,2 +1,2 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                " print(name)\n"
                "--- a/config.py\n"
                "+++ b/config.py\n"
                "@@ -1 +1 @@\n"
                "-debug = False\n"
                "+debug = True\n",
            )

            app = read_project_file(workspace, "app.py")
            config = read_project_file(workspace, "config.py")
        self.assertEqual([path.name for path in paths], ["app.py", "config.py"])
        self.assertEqual(app, "name = 'new'\nprint(name)\n")
        self.assertEqual(config, "debug = True\n")
        self.assertIn("a/app.py", diff)
        self.assertIn("a/config.py", diff)

    def test_check_project_patches_validates_multiple_files_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            paths, diff = check_project_patches(
                workspace,
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1 +1 @@\n"
                "-name = 'old'\n"
                "+name = 'new'\n"
                "--- a/config.py\n"
                "+++ b/config.py\n"
                "@@ -1 +1 @@\n"
                "-debug = False\n"
                "+debug = True\n",
            )
            app = read_project_file(workspace, "app.py")
            config = read_project_file(workspace, "config.py")

            with self.assertRaisesRegex(ValueError, "duplicate file section"):
                check_project_patches(
                    workspace,
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1 +1 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n"
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1 +1 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n",
                )

        self.assertEqual([path.name for path in paths], ["app.py", "config.py"])
        self.assertIn("+debug = True", diff)
        self.assertEqual(app, "name = 'old'\n")
        self.assertEqual(config, "debug = False\n")

    def test_patch_project_files_rejects_second_file_without_partial_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "name = 'old'\nprint(name)\n")
            write_run_file(workspace, "config.py", "debug = False\n")

            with self.assertRaisesRegex(ValueError, "context did not match"):
                patch_project_files(
                    workspace,
                    "--- a/app.py\n"
                    "+++ b/app.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    "-name = 'old'\n"
                    "+name = 'new'\n"
                    " print(name)\n"
                    "--- a/config.py\n"
                    "+++ b/config.py\n"
                    "@@ -1 +1 @@\n"
                    "-debug = wrong\n"
                    "+debug = True\n",
                )

            app = read_project_file(workspace, "app.py")
            config = read_project_file(workspace, "config.py")
        self.assertEqual(app, "name = 'old'\nprint(name)\n")
        self.assertEqual(config, "debug = False\n")

    def test_delete_project_file_removes_file_and_returns_diff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "obsolete.py", "print('remove')\n")

            deleted, diff = delete_project_file(workspace, "obsolete.py")

            self.assertEqual(deleted, workspace.root / "obsolete.py")
            self.assertFalse((workspace.root / "obsolete.py").exists())
            self.assertIn("-print('remove')", diff)

    def test_text_mutation_helpers_reject_binary_files_without_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            binary = Path(base, "asset.bin")
            binary.write_bytes(b"\x00old")

            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                edit_project_file(workspace, "asset.bin", "old", "new")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                multi_edit_project_file(workspace, "asset.bin", [("old", "new")])
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                patch_project_file(workspace, "asset.bin", "@@ -1 +1 @@\n-old\n+new\n")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                patch_project_files(workspace, "--- a/asset.bin\n+++ b/asset.bin\n@@ -1 +1 @@\n-old\n+new\n")
            with self.assertRaisesRegex(ValueError, "binary or non-UTF-8"):
                delete_project_file(workspace, "asset.bin")

            self.assertEqual(binary.read_bytes(), b"\x00old")

    def test_move_project_file_moves_file_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "old.py", "print('move')\n")

            source, destination = move_project_file(workspace, "old.py", "pkg/new.py")

            self.assertEqual(source, workspace.root / "old.py")
            self.assertEqual(destination, workspace.root / "pkg" / "new.py")
            self.assertFalse((workspace.root / "old.py").exists())
            self.assertEqual((workspace.root / "pkg" / "new.py").read_text(encoding="utf-8"), "print('move')\n")

            write_run_file(workspace, "other.py", "print('other')\n")
            with self.assertRaisesRegex(ValueError, "Destination already exists"):
                move_project_file(workspace, "other.py", "pkg/new.py")
            self.assertTrue((workspace.root / "other.py").exists())

    def test_read_git_status_and_diff_are_read_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
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
            write_run_file(workspace, "app.py", "print('new')\n")
            write_run_file(workspace, "staged.py", "print('staged')\n")
            subprocess.run(["git", "add", "staged.py"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            write_run_file(workspace, "new.py", "print('untracked')\n")

            status = read_git_status(workspace)
            changes = read_git_changes(workspace)
            diff = read_git_diff(workspace, "app.py")
            log = read_git_log(workspace, max_count=1, relative_path="app.py")
            show = read_git_show(workspace, "HEAD", "app.py")
            blame = read_git_blame(workspace, "blame.py", start_line=1, line_count=1)

        self.assertTrue(status.ok)
        self.assertIn("M app.py", status.stdout)
        self.assertTrue(changes["ok"])
        files = {str(item["path"]): item for item in changes["files"]}
        self.assertTrue(files["app.py"]["unstaged"])
        self.assertEqual(files["app.py"]["unstaged_insertions"], 1)
        self.assertEqual(files["app.py"]["unstaged_deletions"], 1)
        self.assertTrue(files["staged.py"]["staged"])
        self.assertEqual(files["staged.py"]["staged_insertions"], 1)
        self.assertTrue(files["new.py"]["untracked"])
        self.assertTrue(diff.ok)
        self.assertIn("-print('old')", diff.stdout)
        self.assertIn("+print('new')", diff.stdout)
        self.assertTrue(log.ok)
        self.assertIn("initial", log.stdout)
        self.assertTrue(show.ok)
        self.assertIn("initial", show.stdout)
        self.assertIn("app.py", show.stdout)
        self.assertIn("+print('old')", show.stdout)
        self.assertTrue(blame.ok)
        self.assertIn("print('blame')", blame.stdout)
        self.assertIn("Test", blame.stdout)

    def test_read_git_blame_rejects_invalid_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "app.py", "print('ok')\n")

            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_blame(workspace, "../outside.py")
            with self.assertRaisesRegex(ValueError, "not a file"):
                read_git_blame(workspace, ".")
            with self.assertRaisesRegex(ValueError, "line_count must be at most 1000"):
                read_git_blame(workspace, "app.py", start_line=1, line_count=1001)

    def test_review_project_changes_checks_diff_and_changed_python(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
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
            write_run_file(workspace, "note.txt", "trailing whitespace \n")
            subprocess.run(["git", "add", "note.txt"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Path(root, ".vibeagent").mkdir(exist_ok=True)
            Path(root, ".vibeagent", "local.py").write_text("def ignored(:\n", encoding="utf-8")

            review = review_project_changes(workspace)

        self.assertFalse(review["ok"])
        self.assertTrue(review["changes_ok"])
        self.assertFalse(review["diff_check_ok"])
        self.assertFalse(review["staged_diff_check_ok"])
        self.assertFalse(review["python_ok"])
        self.assertIn("unstaged diff check failed", review["message"])
        self.assertIn("staged diff check failed", review["message"])
        files = {str(item["path"]): item for item in review["files"]}
        self.assertEqual(sorted(files), ["app.py", "note.txt"])
        self.assertEqual(review["total_files"], 2)
        self.assertEqual([(item["path"], item["ok"]) for item in review["python"]], [("app.py", False)])
        self.assertEqual(review["python_total"], 1)
        self.assertIn("Python syntax error", review["python"][0]["message"])
        self.assertIn("note.txt", review["staged_diff_check"])

    def test_read_git_diff_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_diff(workspace, "../outside.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_log(workspace, relative_path="../outside.py")
            with self.assertRaisesRegex(ValueError, "escapes"):
                read_git_show(workspace, relative_path="../outside.py")
            with self.assertRaisesRegex(ValueError, "must not start"):
                read_git_show(workspace, rev="--stat")

    def test_project_paths_protect_vibeagent_and_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workspace-") as base:
            workspace = create_run_workspace(base, "test-run")

            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(workspace.root, ".vibeagent/sessions/test-run/events.jsonl")
            with self.assertRaisesRegex(ValueError, "protected"):
                resolve_inside_run(workspace.root, ".git/config")


if __name__ == "__main__":
    unittest.main()
