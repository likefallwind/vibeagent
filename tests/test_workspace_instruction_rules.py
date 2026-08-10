from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from vibeagent.agent_tool_results import record_tool_result_event
from vibeagent.observation_read_types import ReadFileObservation, ReadFileResult, ReadFilesObservation
from vibeagent.workspace_core import create_run_workspace
from vibeagent.workspace_instruction_rules import parse_rule_frontmatter, rule_pattern_matches
from vibeagent.workspace_project_instructions import (
    read_path_instruction_context,
    read_project_instruction_sources,
    read_project_instructions,
)


class WorkspaceInstructionRuleTests(unittest.TestCase):
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
            self.assertEqual(state, ["pkg/CLAUDE.md"])

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
