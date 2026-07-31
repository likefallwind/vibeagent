import tempfile
import unittest
from pathlib import Path

from vibeagent.agent_approval_preview import approval_preview_summary
from vibeagent.agent_tool_results import build_tool_result_payload
from vibeagent.json_action_executor import execute_json_action
from vibeagent.types import (
    CheckJsonPatchAction,
    CheckJsonSetAction,
    JsonPatchAction,
    JsonPatchOperation,
    JsonSetAction,
)
from vibeagent.workspace import create_run_workspace, write_run_file


class JsonActionExecutorTests(unittest.TestCase):
    def test_json_set_preview_matches_approval_by_value_and_create_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-json-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts":{"test":"npm test"}}\n')

            observation = execute_json_action(
                workspace,
                CheckJsonSetAction(
                    type="check_json_set",
                    path="package.json",
                    pointer="/scripts/dev",
                    value="vite",
                    create_missing=True,
                ),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_json_set")
            self.assertTrue(observation.ok)
            self.assertEqual(observation.value, "vite")
            self.assertTrue(observation.create_missing)
            self.assertEqual(Path(base, "package.json").read_text(encoding="utf-8"), '{"scripts":{"test":"npm test"}}\n')
            matching_preview = approval_preview_summary(
                JsonSetAction(
                    type="json_set",
                    path="package.json",
                    pointer="/scripts/dev",
                    value="vite",
                    create_missing=True,
                ),
                [observation],
            )
            mismatched_value_preview = approval_preview_summary(
                JsonSetAction(
                    type="json_set",
                    path="package.json",
                    pointer="/scripts/dev",
                    value="webpack",
                    create_missing=True,
                ),
                [observation],
            )
            mismatched_create_preview = approval_preview_summary(
                JsonSetAction(
                    type="json_set",
                    path="package.json",
                    pointer="/scripts/dev",
                    value="vite",
                    create_missing=False,
                ),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_value_preview)
            self.assertIsNone(mismatched_create_preview)
            payload = build_tool_result_payload(observation)
            self.assertNotIn("value", payload)
            self.assertNotIn("create_missing", payload)

    def test_json_patch_preview_matches_approval_by_operations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-json-executor-") as base:
            workspace = create_run_workspace(base, "test-run")
            write_run_file(workspace, "package.json", '{"scripts":{"test":"npm test"},"private":false}\n')
            operations = [
                JsonPatchOperation(op="add", path="/scripts/dev", value="vite"),
                JsonPatchOperation(op="replace", path="/private", value=True),
            ]

            observation = execute_json_action(
                workspace,
                CheckJsonPatchAction(type="check_json_patch", path="package.json", operations=operations),
            )

            self.assertIsNotNone(observation)
            self.assertEqual(observation.kind, "check_json_patch")
            self.assertTrue(observation.ok)
            self.assertEqual(observation.operations, operations)
            matching_preview = approval_preview_summary(
                JsonPatchAction(type="json_patch", path="package.json", operations=operations),
                [observation],
            )
            mismatched_preview = approval_preview_summary(
                JsonPatchAction(
                    type="json_patch",
                    path="package.json",
                    operations=[
                        JsonPatchOperation(op="add", path="/scripts/dev", value="webpack"),
                        JsonPatchOperation(op="replace", path="/private", value=True),
                    ],
                ),
                [observation],
            )

            self.assertIn("diffChars=", matching_preview or "")
            self.assertIsNone(mismatched_preview)
            self.assertNotIn("operations", build_tool_result_payload(observation))


if __name__ == "__main__":
    unittest.main()
