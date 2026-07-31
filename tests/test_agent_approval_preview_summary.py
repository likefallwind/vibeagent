from __future__ import annotations

import unittest

import vibeagent.agent_approval_preview_summary as preview_summary
import vibeagent.types as types_module
from vibeagent.types import CheckRunCommandsObservation, CommandCheckObservation


class ApprovalPreviewSummaryTests(unittest.TestCase):
    def test_summarize_preview_observation_fingerprints_diff_content(self) -> None:
        first = preview_summary.summarize_preview_observation(
            types_module.CheckGitStashObservation(
                kind="check_git_stash",
                ok=True,
                message_text="save work",
                include_untracked=False,
                status=" M app.py\n",
                diff="abc",
                message="Can stash 1 path(s).",
            )
        )
        second = preview_summary.summarize_preview_observation(
            types_module.CheckGitStashObservation(
                kind="check_git_stash",
                ok=True,
                message_text="save work",
                include_untracked=False,
                status=" M app.py\n",
                diff="xyz",
                message="Can stash 1 path(s).",
            )
        )

        self.assertIn("diffChars=3", first)
        self.assertIn("diffChars=3", second)
        self.assertIn("diffSha256=", first)
        self.assertIn("diffSha256=", second)
        self.assertNotEqual(first, second)

    def test_summarize_preview_observation_fingerprints_command_checks(self) -> None:
        first = preview_summary.summarize_preview_observation(
            CheckRunCommandsObservation(
                kind="check_run_commands",
                ok=True,
                checks=[
                    CommandCheckObservation(
                        kind="command_check",
                        ok=True,
                        command="python -m unittest",
                        cwd=".",
                        cwd_ok=True,
                        blocked=False,
                        block_reason=None,
                        executable_available=True,
                        missing_tool=None,
                        message="Command can run.",
                    )
                ],
                message="Preflighted 1 command.",
            )
        )
        second = preview_summary.summarize_preview_observation(
            CheckRunCommandsObservation(
                kind="check_run_commands",
                ok=True,
                checks=[
                    CommandCheckObservation(
                        kind="command_check",
                        ok=True,
                        command="npm test",
                        cwd=".",
                        cwd_ok=True,
                        blocked=False,
                        block_reason=None,
                        executable_available=True,
                        missing_tool=None,
                        message="Command can run.",
                    )
                ],
                message="Preflighted 1 command.",
            )
        )

        self.assertIn("commands=1", first)
        self.assertIn("commands=1", second)
        self.assertIn("commandsSha256=", first)
        self.assertIn("commandsSha256=", second)
        self.assertNotEqual(first, second)

    def test_summarize_preview_observation_fingerprints_preview_file_diffs(self) -> None:
        first = preview_summary.summarize_preview_observation(
            types_module.CodeRenamePreviewObservation(
                kind="code_rename_preview",
                symbol="runAgent",
                new_name="executeAgent",
                path=None,
                files=[
                    types_module.CodeRenamePreviewFile(
                        path="src/app.ts",
                        language="typescript",
                        replacements=[],
                        diff="abc",
                        truncated=False,
                    )
                ],
                total_replacements=1,
                total_files=1,
                truncated=False,
                ok=True,
                errors=[],
                message="Found 1 code rename replacement(s) across 1 file(s).",
            )
        )
        second = preview_summary.summarize_preview_observation(
            types_module.CodeRenamePreviewObservation(
                kind="code_rename_preview",
                symbol="runAgent",
                new_name="executeAgent",
                path=None,
                files=[
                    types_module.CodeRenamePreviewFile(
                        path="src/app.ts",
                        language="typescript",
                        replacements=[],
                        diff="xyz",
                        truncated=False,
                    )
                ],
                total_replacements=1,
                total_files=1,
                truncated=False,
                ok=True,
                errors=[],
                message="Found 1 code rename replacement(s) across 1 file(s).",
            )
        )

        self.assertIn("fileDiffs=1", first)
        self.assertIn("fileDiffs=1", second)
        self.assertIn("fileDiffsSha256=", first)
        self.assertIn("fileDiffsSha256=", second)
        self.assertNotEqual(first, second)

    def test_file_diff_fingerprint_payload_normalizes_paths(self) -> None:
        first = preview_summary.file_diff_fingerprint_payload(
            [
                types_module.CodeRenamePreviewFile(
                    path="./src/app.ts",
                    language="typescript",
                    replacements=[],
                    diff="abc",
                    truncated=False,
                )
            ]
        )
        second = preview_summary.file_diff_fingerprint_payload(
            [
                types_module.CodeRenamePreviewFile(
                    path="src/app.ts",
                    language="typescript",
                    replacements=[],
                    diff="abc",
                    truncated=False,
                )
            ]
        )

        self.assertEqual(first, second)
        self.assertIn('"path":"src/app.ts"', first)


if __name__ == "__main__":
    unittest.main()
