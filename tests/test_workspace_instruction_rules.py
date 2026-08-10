from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.agent_tool_results import record_tool_result_event
from vibeagent.observation_read_types import ReadFileObservation, ReadFileResult, ReadFilesObservation
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_instruction_rules import parse_rule_frontmatter, rule_pattern_matches
from vibeagent.workspace_instruction_state import reset_loaded_instruction_documents
from vibeagent.workspace_project_instructions import (
    read_path_instruction_context,
    read_project_instruction_sources,
    read_project_instructions,
)


class WorkspaceInstructionRuleTests(unittest.TestCase):
    def test_claude_imports_project_file_inline_without_duplicate_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-import")
            self._write(root / "AGENTS.md", "Use unittest.\n")
            self._write(root / "CLAUDE.md", "Shared rules:\n@AGENTS.md\nKeep output concise.\n")

            metadata = read_project_instruction_sources(workspace)

        self.assertTrue(metadata["ok"])
        self.assertEqual([item["path"] for item in metadata["files"]], ["CLAUDE.md", "AGENTS.md"])
        imported = metadata["files"][1]
        self.assertEqual(imported["reason"], "include")
        self.assertEqual(imported["owner_path"], "CLAUDE.md")
        self.assertEqual(imported["parent_path"], "CLAUDE.md")
        self.assertTrue(imported["included"])
        text = str(metadata["text"])
        self.assertEqual(text.count("Use unittest."), 1)
        self.assertNotIn("File: AGENTS.md", text)
        self.assertIn("[Imported instructions from AGENTS.md]", text)

    def test_recursive_imports_are_relative_strip_comments_and_ignore_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-recursive-import")
            self._write(
                root / "CLAUDE.md",
                "<!-- hidden @missing.md -->\n@docs/one.md\n`@inline.md`\n```md\n@fenced.md\n<!-- keep in code -->\n```\n",
            )
            self._write(root / "docs" / "one.md", "One.\n@nested/two.md\n")
            self._write(root / "docs" / "nested" / "two.md", "Two.\n")

            metadata = read_project_instruction_sources(workspace)

        self.assertTrue(metadata["ok"])
        self.assertEqual(
            {item["path"] for item in metadata["files"]},
            {"CLAUDE.md", "docs/one.md", "docs/nested/two.md"},
        )
        parents = {item["path"]: item["parent_path"] for item in metadata["files"]}
        self.assertEqual(parents["docs/one.md"], "CLAUDE.md")
        self.assertEqual(parents["docs/nested/two.md"], "docs/one.md")
        text = str(metadata["text"])
        self.assertIn("One.", text)
        self.assertIn("Two.", text)
        self.assertNotIn("hidden", text)
        self.assertIn("`@inline.md`", text)
        self.assertIn("@fenced.md", text)
        self.assertIn("<!-- keep in code -->", text)

    def test_import_cycle_missing_and_external_symlink_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-import-errors")
            outside = Path(outside_dir) / "outside.md"
            outside.write_text("outside secret\n", encoding="utf-8")
            (root / "external.md").symlink_to(outside)
            self._write(root / ".env", "SECRET_TOKEN=hidden\n")
            self._write(root / "CLAUDE.md", "@a.md\n@missing.md\n@external.md\n@.env\n")
            self._write(root / "a.md", "@CLAUDE.md\n")

            metadata = read_project_instruction_sources(workspace)

        self.assertFalse(metadata["ok"])
        self.assertNotIn("outside secret", metadata["text"])
        self.assertNotIn("SECRET_TOKEN", metadata["text"])
        errors = [item for item in metadata["files"] if not item["included"]]
        self.assertEqual({item["path"] for item in errors}, {"CLAUDE.md", "missing.md", "external.md", ".env"})
        self.assertTrue(any("cycle" in item["message"] for item in errors))
        self.assertTrue(any("project root" in item["message"] for item in errors))
        self.assertTrue(any("protected project path" in item["message"] for item in errors))
        self.assertIn("Instruction import skipped", metadata["text"])

    def test_recursive_import_depth_is_bounded_at_five_hops(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-import-depth")
            self._write(root / "CLAUDE.md", "@chain/1.md\n")
            for index in range(1, 7):
                next_import = f"@{index + 1}.md\n" if index < 6 else ""
                self._write(root / "chain" / f"{index}.md", f"Level {index}.\n{next_import}")

            metadata = read_project_instruction_sources(workspace)

        self.assertFalse(metadata["ok"])
        self.assertIn("Level 5.", metadata["text"])
        self.assertNotIn("Level 6.", metadata["text"])
        depth_error = next(item for item in metadata["files"] if item["path"] == "chain/6.md")
        self.assertFalse(depth_error["included"])
        self.assertIn("at most 5 levels", depth_error["message"])

    def test_instruction_entrypoint_import_count_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-import-count")
            references = "".join(f"@missing-{index}.md\n" for index in range(75))
            self._write(root / "CLAUDE.md", references)

            metadata = read_project_instruction_sources(workspace)

        self.assertFalse(metadata["ok"])
        self.assertLessEqual(len(metadata["files"]), 52)
        self.assertTrue(any("at most 50 files" in item["message"] for item in metadata["files"]))

    def test_lazy_import_group_is_claimed_once_by_its_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-import-claim")
            self._write(root / "pkg" / "CLAUDE.md", "@rules.md\nPackage rule.\n")
            self._write(root / "pkg" / "rules.md", "Imported package rule.\n")

            first = read_path_instruction_context(workspace, ["pkg/module.py"])
            second = read_path_instruction_context(workspace, ["pkg/other.py"])
            state = json.loads((workspace.session_dir / "loaded_instructions.json").read_text(encoding="utf-8"))

        self.assertEqual([item["path"] for item in first["files"]], ["pkg/CLAUDE.md", "pkg/rules.md"])
        self.assertEqual(second["files"], [])
        self.assertEqual(state["consumers"]["main"], ["pkg/CLAUDE.md"])
        self.assertIn("Imported package rule.", first["text"])

    def test_startup_loads_root_local_claude_directory_and_unconditional_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-startup")
            self._write(root / "AGENTS.md", "Root agents.\n")
            self._write(root / "CLAUDE.md", "Root claude.\n")
            self._write(root / "CLAUDE.local.md", "Local preference.\n")
            self._write(root / ".claude" / "CLAUDE.md", "Claude directory.\n")
            self._write(root / ".claude" / "rules" / "testing.md", "Always use focused tests.\n")
            self._write(root / "pkg" / "CLAUDE.md", "Nested package only.\n")

            metadata = read_project_instruction_sources(workspace)
            text = read_project_instructions(workspace) or ""

            self.assertTrue(metadata["ok"])
            self.assertIn("Root agents.", text)
            self.assertIn("Root claude.", text)
            self.assertIn("Local preference.", text)
            self.assertIn("Claude directory.", text)
            self.assertIn("Always use focused tests.", text)
            self.assertNotIn("Nested package only.", text)
            nested = next(item for item in metadata["files"] if item["path"] == "pkg/CLAUDE.md")
            self.assertFalse(nested["included"])
            self.assertEqual(nested["reason"], "nested_traversal")

    def test_path_rules_and_nested_instructions_load_for_matching_file_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-path")
            self._write(root / "src" / "AGENTS.md", "Source subtree rule.\n")
            self._write(
                root / ".claude" / "rules" / "typescript.md",
                '---\npaths:\n  - "src/**/*.{ts,tsx}"\n---\nValidate TypeScript inputs.\n',
            )

            matching = read_path_instruction_context(workspace, ["src/api/handler.ts"], claim=False)
            other = read_path_instruction_context(workspace, ["tests/test_api.py"], claim=False)

            self.assertIn("Source subtree rule.", matching["text"])
            self.assertIn("Validate TypeScript inputs.", matching["text"])
            self.assertEqual(
                [item["reason"] for item in matching["files"]],
                ["path_glob_match", "nested_traversal"],
            )
            self.assertEqual(other["files"], [])

    def test_path_instruction_claim_is_once_per_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-once")
            self._write(root / "pkg" / "CLAUDE.md", "Package rule.\n")

            first = read_path_instruction_context(workspace, ["pkg/module.py"])
            second = read_path_instruction_context(workspace, ["pkg/other.py"])

            self.assertEqual([item["path"] for item in first["files"]], ["pkg/CLAUDE.md"])
            self.assertEqual(second["files"], [])
            state = json.loads((workspace.session_dir / "loaded_instructions.json").read_text(encoding="utf-8"))
            self.assertEqual(state["version"], 2)
            self.assertEqual(state["consumers"]["main"], ["pkg/CLAUDE.md"])

    def test_path_instruction_claims_are_isolated_by_consumer_and_reset_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-consumers")
            self._write(root / "pkg" / "CLAUDE.md", "Package rule.\n")

            main = read_path_instruction_context(workspace, ["pkg/main.py"])
            child = read_path_instruction_context(workspace, ["pkg/child.py"], consumer_id="subagent:delegate-1")
            main_again = read_path_instruction_context(workspace, ["pkg/other.py"])
            removed = reset_loaded_instruction_documents(workspace, "main")
            main_after_reset = read_path_instruction_context(workspace, ["pkg/other.py"])
            child_again = read_path_instruction_context(
                workspace,
                ["pkg/child.py"],
                consumer_id="subagent:delegate-1",
            )

            state = json.loads((workspace.session_dir / "loaded_instructions.json").read_text(encoding="utf-8"))

        self.assertEqual([item["path"] for item in main["files"]], ["pkg/CLAUDE.md"])
        self.assertEqual([item["path"] for item in child["files"]], ["pkg/CLAUDE.md"])
        self.assertEqual(main_again["files"], [])
        self.assertEqual(removed, 1)
        self.assertEqual([item["path"] for item in main_after_reset["files"]], ["pkg/CLAUDE.md"])
        self.assertEqual(child_again["files"], [])
        self.assertEqual(set(state["consumers"]), {"main", "subagent:delegate-1"})

    def test_legacy_instruction_state_migrates_when_another_consumer_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-migrate")
            self._write(root / "pkg" / "CLAUDE.md", "Package rule.\n")
            state_path = workspace.session_dir / "loaded_instructions.json"
            state_path.write_text('["pkg/CLAUDE.md"]\n', encoding="utf-8")

            main = read_path_instruction_context(workspace, ["pkg/main.py"])
            child = read_path_instruction_context(workspace, ["pkg/child.py"], consumer_id="subagent:delegate-1")
            migrated = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(main["files"], [])
        self.assertEqual([item["path"] for item in child["files"]], ["pkg/CLAUDE.md"])
        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["consumers"]["main"], ["pkg/CLAUDE.md"])
        self.assertEqual(migrated["consumers"]["subagent:delegate-1"], ["pkg/CLAUDE.md"])

    def test_concurrent_consumers_claim_without_losing_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-concurrent")
            self._write(root / "pkg" / "CLAUDE.md", "Package rule.\n")
            consumers = [f"subagent:delegate-{index}" for index in range(12)]

            def claim(consumer: str) -> list[str]:
                context = read_path_instruction_context(workspace, ["pkg/module.py"], consumer_id=consumer)
                return [item["path"] for item in context["files"]]

            with ThreadPoolExecutor(max_workers=6) as executor:
                first = list(executor.map(claim, consumers))
                second = list(executor.map(claim, consumers))
            state = json.loads((workspace.session_dir / "loaded_instructions.json").read_text(encoding="utf-8"))

        self.assertEqual(first, [["pkg/CLAUDE.md"]] * len(consumers))
        self.assertEqual(second, [[]] * len(consumers))
        self.assertEqual(set(state["consumers"]), set(consumers))

    def test_consumer_limit_evicts_old_subagent_but_preserves_main(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-consumer-limit")
            self._write(root / "pkg" / "CLAUDE.md", "Package rule.\n")
            read_path_instruction_context(workspace, ["pkg/main.py"])
            for index in range(100):
                read_path_instruction_context(
                    workspace,
                    ["pkg/module.py"],
                    consumer_id=f"subagent:delegate-{index:03d}",
                )

            main_again = read_path_instruction_context(workspace, ["pkg/main.py"])
            state = json.loads((workspace.session_dir / "loaded_instructions.json").read_text(encoding="utf-8"))

        self.assertEqual(main_again["files"], [])
        self.assertEqual(len(state["consumers"]), 100)
        self.assertIn("main", state["consumers"])
        self.assertIn("subagent:delegate-099", state["consumers"])

    def test_tool_result_injects_lazy_instructions_and_records_audit_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-tool-result")
            self._write(root / "pkg" / "AGENTS.md", "Use package fixtures.\n")
            observation = ReadFileObservation(
                kind="read_file",
                path="pkg/module.py",
                content="value = 1\n",
                message="Read pkg/module.py.",
                total_bytes=10,
            )

            first = record_tool_result_event(
                workspace,
                tool_id="read-1",
                tool_name="read_file",
                observation=observation,
                iteration=1,
            )
            second = record_tool_result_event(
                workspace,
                tool_id="read-2",
                tool_name="read_file",
                observation=observation,
                iteration=2,
            )

            self.assertIn("Use package fixtures.", first["pathInstructions"]["text"])
            self.assertNotIn("pathInstructions", second)
            events = [json.loads(line) for line in (workspace.session_dir / "events.jsonl").read_text().splitlines()]
            loaded = [event for event in events if event["type"] == "instructions_loaded"]
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["files"][0]["path"], "pkg/AGENTS.md")

    def test_batch_read_loads_rules_for_all_successful_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-batch")
            self._write(root / "api" / "AGENTS.md", "API rule.\n")
            self._write(root / "web" / "CLAUDE.md", "Web rule.\n")
            observation = ReadFilesObservation(
                kind="read_files",
                files=[
                    ReadFileResult(path="api/a.py", ok=True, content="", message="Read api/a.py."),
                    ReadFileResult(path="web/a.ts", ok=True, content="", message="Read web/a.ts."),
                    ReadFileResult(path="missing.py", ok=False, content="", message="missing"),
                ],
                message="Read 2/3 file(s).",
            )

            payload = record_tool_result_event(
                workspace,
                tool_id="batch",
                tool_name="read_files",
                observation=observation,
                iteration=1,
            )

            paths = [item["path"] for item in payload["pathInstructions"]["files"]]
            self.assertEqual(paths, ["api/AGENTS.md", "web/CLAUDE.md"])

    def test_rule_frontmatter_and_globs_support_common_claude_patterns(self) -> None:
        patterns, body = parse_rule_frontmatter(
            '---\npaths: ["src/**/*.ts", "tests/**/test_?.py"]\n---\nRule body.\n'
        )

        self.assertEqual(patterns, ("src/**/*.ts", "tests/**/test_?.py"))
        self.assertEqual(body, "Rule body.\n")
        self.assertTrue(rule_pattern_matches("src/**/*.ts", "src/index.ts"))
        self.assertTrue(rule_pattern_matches("src/**/*.ts", "src/api/index.ts"))
        self.assertTrue(rule_pattern_matches("*.md", "README.md"))
        self.assertFalse(rule_pattern_matches("*.md", "docs/README.md"))
        self.assertTrue(rule_pattern_matches("src/**/*.{ts,tsx}", "src/ui/button.tsx"))

    def test_external_rule_symlink_fails_closed_without_loading_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            root = Path(temp_dir)
            workspace = create_run_workspace(root, run_id="instruction-symlink")
            outside = Path(outside_dir) / "secret.md"
            outside.write_text("outside secret\n", encoding="utf-8")
            link = root / ".claude" / "rules" / "external.md"
            link.parent.mkdir(parents=True)
            link.symlink_to(outside)

            metadata = read_project_instruction_sources(workspace)

            self.assertFalse(metadata["ok"])
            self.assertNotIn("outside secret", metadata["text"])
            source = next(item for item in metadata["files"] if item["path"] == ".claude/rules/external.md")
            self.assertFalse(source["included"])
            self.assertIn("not in the subpath", source["message"])

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
