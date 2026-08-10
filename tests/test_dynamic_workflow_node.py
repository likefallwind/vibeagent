from __future__ import annotations

from threading import Event, Lock
import time
import unittest

from vibeagent.dynamic_workflow_node import request_to_dict, run_node_workflow
from vibeagent.dynamic_workflow_types import WorkflowAgentRequest


class DynamicWorkflowNodeTests(unittest.TestCase):
    def test_pipeline_runs_agents_concurrently_and_preserves_result_order(self) -> None:
        active = 0
        max_active = 0
        lock = Lock()
        completed: list[tuple[str, bool]] = []

        def execute(request: WorkflowAgentRequest, _cancelled) -> dict[str, object]:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1
            return {"ok": True, "summary": request.task}

        result = run_node_workflow(
            source=(
                "const values = await pipeline(['a', 'b', 'c'], "
                "async (item) => agent(`inspect ${item}`), {concurrency: 3});\n"
                "return values.map((value) => value.summary);"
            ),
            filename="workflow.js",
            execute_agent=execute,
            cancel_event=Event(),
            cached_calls={},
            on_call_completed=lambda request, _result, cached: completed.append((request.call_id, cached)),
        )

        self.assertEqual(result, ["inspect a", "inspect b", "inspect c"])
        self.assertGreaterEqual(max_active, 2)
        self.assertEqual(sorted(completed), [("call-0001", False), ("call-0002", False), ("call-0003", False)])

    def test_resume_replays_matching_cached_calls_without_execution(self) -> None:
        request = WorkflowAgentRequest(call_id="call-0001", task="cached")
        executed: list[str] = []
        completed: list[tuple[str, bool]] = []

        result = run_node_workflow(
            source="const first = await agent('cached'); const second = await agent('new'); return [first, second];",
            filename="workflow.js",
            execute_agent=lambda item, _cancelled: executed.append(item.call_id) or {"summary": item.task},
            cancel_event=Event(),
            cached_calls={
                "call-0001": {
                    "request": request_to_dict(request),
                    "result": {"summary": "cached"},
                }
            },
            on_call_completed=lambda item, _result, cached: completed.append((item.call_id, cached)),
        )

        self.assertEqual(result, [{"summary": "cached"}, {"summary": "new"}])
        self.assertEqual(executed, ["call-0002"])
        self.assertEqual(completed, [("call-0001", True), ("call-0002", False)])

    def test_vm_hides_host_process_and_disables_string_code_generation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Code generation from strings disallowed"):
            run_node_workflow(
                source="return ({}).constructor.constructor('return process')();",
                filename="unsafe.js",
                execute_agent=lambda _request, _cancelled: {},
                cancel_event=Event(),
                cached_calls={},
                on_call_completed=lambda _request, _result, _cached: None,
            )

        result = run_node_workflow(
            source="return [typeof process, typeof require, typeof fetch];",
            filename="globals.js",
            execute_agent=lambda _request, _cancelled: {},
            cancel_event=Event(),
            cached_calls={},
            on_call_completed=lambda _request, _result, _cached: None,
        )
        self.assertEqual(result, ["undefined", "undefined", "undefined"])

        for source in (
            "return agent.constructor('return process')();",
            "const pending = agent('inspect'); return pending.constructor.constructor('return process')();",
        ):
            with self.subTest(source=source), self.assertRaisesRegex(
                RuntimeError, "Code generation from strings disallowed"
            ):
                run_node_workflow(
                    source=source,
                    filename="host-function-escape.js",
                    execute_agent=lambda _request, _cancelled: {"ok": True},
                    cancel_event=Event(),
                    cached_calls={},
                    on_call_completed=lambda _request, _result, _cached: None,
                )

    def test_workflow_can_be_cancelled_while_script_is_busy(self) -> None:
        cancelled = Event()

        def stop_soon() -> None:
            time.sleep(0.1)
            cancelled.set()

        from threading import Thread

        Thread(target=stop_soon, daemon=True).start()
        with self.assertRaises(InterruptedError):
            run_node_workflow(
                source="while (true) {}",
                filename="busy.js",
                execute_agent=lambda _request, _cancelled: {},
                cancel_event=cancelled,
                cached_calls={},
                on_call_completed=lambda _request, _result, _cached: None,
            )

    def test_pipeline_and_total_agent_call_limits_are_enforced(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "concurrency must be an integer between 1 and 16"):
            run_node_workflow(
                source="return pipeline([1], (item) => item, {concurrency: 17});",
                filename="too-wide.js",
                execute_agent=lambda _request, _cancelled: {},
                cancel_event=Event(),
                cached_calls={},
                on_call_completed=lambda _request, _result, _cached: None,
            )

        with self.assertRaisesRegex(RuntimeError, "exceeded 1000 agent calls"):
            run_node_workflow(
                source="return Promise.all(Array.from({length: 1001}, (_, i) => agent(`task ${i}`)));",
                filename="too-many.js",
                execute_agent=lambda _request, _cancelled: {"ok": True},
                cancel_event=Event(),
                cached_calls={},
                on_call_completed=lambda _request, _result, _cached: None,
            )


if __name__ == "__main__":
    unittest.main()
