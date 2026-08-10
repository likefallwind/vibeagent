from __future__ import annotations

from pathlib import Path
from threading import Lock
import tempfile
import time
import unittest

from vibeagent.dynamic_workflow_commands import handle_workflows_command
from vibeagent.dynamic_workflow_runtime import DynamicWorkflowManager
from vibeagent.dynamic_workflow_store import read_workflow_record
from vibeagent.dynamic_workflow_types import WorkflowAgentRequest
from vibeagent.workspace_core import create_run_workspace


class DynamicWorkflowRuntimeTests(unittest.TestCase):
    def wait_for_status(self, manager: DynamicWorkflowManager, workflow_id: str, status: str) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if manager.get(workflow_id).status == status:
                return
            time.sleep(0.02)
        self.fail(f"workflow {workflow_id} did not reach {status}")

    def test_manager_persists_completed_workflow_and_session_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-") as base:
            root = Path(base)
            (root / "flow.js").write_text("return await agent('inspect project');", encoding="utf-8")
            workspace = create_run_workspace(root, run_id="run-1")
            requests: list[WorkflowAgentRequest] = []
            manager = DynamicWorkflowManager(
                workspace,
                lambda request, _cancelled: requests.append(request) or {"ok": True, "summary": "done"},
            )

            summary = manager.start("flow.js")
            self.wait_for_status(manager, summary.id, "completed")
            stored = read_workflow_record(root, summary.id)

            self.assertEqual(stored["total_calls"], 1)
            self.assertEqual(stored["result"], {"ok": True, "summary": "done"})
            self.assertEqual(requests[0].workflow_id, summary.id)
            events = (workspace.session_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"type": "workflow_started"', events)
            self.assertIn('"type": "workflow_finished"', events)

    def test_failed_workflow_resumes_with_completed_call_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-") as base:
            root = Path(base)
            (root / "flow.js").write_text(
                "await agent('first'); await agent('second'); return 'done';",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, run_id="run-1")
            fail_second = True
            executed: list[str] = []

            def execute(request: WorkflowAgentRequest, _cancelled) -> dict[str, object]:
                nonlocal fail_second
                executed.append(request.task)
                if request.task == "second" and fail_second:
                    raise RuntimeError("temporary failure")
                return {"ok": True, "summary": request.task}

            manager = DynamicWorkflowManager(workspace, execute)
            summary = manager.start("flow.js")
            self.wait_for_status(manager, summary.id, "failed")
            fail_second = False
            manager.resume(summary.id)
            self.wait_for_status(manager, summary.id, "completed")
            final = manager.get(summary.id)

            self.assertEqual(executed, ["first", "second", "second"])
            self.assertEqual(final.total_calls, 2)
            self.assertEqual(final.cached_calls, 1)

    def test_shared_code_calls_are_serialized_and_cached_output_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-") as base:
            root = Path(base)
            (root / "flow.js").write_text(
                "return pipeline([1, 2, 3], (item) => agent(`edit ${item}`, {mode: 'code'}), {concurrency: 3});",
                encoding="utf-8",
            )
            workspace = create_run_workspace(root, run_id="run-1")
            lock = Lock()
            active = 0
            max_active = 0

            def execute(_request: WorkflowAgentRequest, _cancelled) -> dict[str, object]:
                nonlocal active, max_active
                with lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.03)
                with lock:
                    active -= 1
                return {"ok": True, "summary": "token=sk-abcdefghijk"}

            manager = DynamicWorkflowManager(workspace, execute)
            summary = manager.start("flow.js")
            self.wait_for_status(manager, summary.id, "completed")
            stored = read_workflow_record(root, summary.id)

            self.assertEqual(max_active, 1)
            self.assertNotIn("sk-abcdefghijk", str(stored))
            self.assertIn("[REDACTED]", str(stored))

    def test_stale_running_record_is_reported_as_interrupted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-") as base:
            root = Path(base)
            (root / "flow.js").write_text("return 'done';", encoding="utf-8")
            workspace = create_run_workspace(root, run_id="run-1")
            manager = DynamicWorkflowManager(workspace, lambda _request, _cancelled: {})
            summary = manager.start("flow.js")
            self.wait_for_status(manager, summary.id, "completed")
            record = read_workflow_record(root, summary.id)
            record["status"] = "running"
            record["owner_pid"] = 999_999_999
            from vibeagent.dynamic_workflow_store import write_workflow_record

            write_workflow_record(root, record)

            refreshed = manager.get(summary.id)
            self.assertEqual(refreshed.status, "interrupted")
            self.assertIn("owner process exited", refreshed.error or "")

    def test_commands_list_show_and_validate_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="vibeagent-workflow-") as base:
            root = Path(base)
            workspace = create_run_workspace(root, run_id="run-1")
            manager = DynamicWorkflowManager(workspace, lambda _request, _cancelled: {})

            self.assertEqual(handle_workflows_command(manager, None), "No workflows found.")
            self.assertIn("Workflow error:", handle_workflows_command(manager, "run ../outside.js"))
            self.assertIn("Usage:", handle_workflows_command(manager, "unknown"))


if __name__ == "__main__":
    unittest.main()
